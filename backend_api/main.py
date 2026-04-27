#!/usr/bin/env python3
"""
api.py — FastAPI backend for the Social Media Analytics Dashboard.

Endpoints:
  GET  /health                        → healthcheck
  POST /api/pipeline/run              → trigger pipeline (returns job_id immediately)
  GET  /api/pipeline/status/{job_id}  → poll job status + streamed logs
  GET  /api/data?keyword=xxx          → return all gold-layer data as JSON
  GET  /api/keywords                  → list previously analysed keywords
  GET  /api/prescribe?keyword=xxx     → Gemini AI strategy recommendations
"""

import os
import sys
import glob
import uuid
import time
import json
import re
import logging
import threading
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def load_env_from_dotenv(dotenv_path=None):
    if dotenv_path is None:
        dotenv_path = Path(__file__).resolve().parent.parent / ".env"
    dotenv_path = Path(dotenv_path)
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value


def get_gemini_api_key() -> str:
    load_env_from_dotenv()
    return os.environ.get("GEMINI_API_KEY", "").strip()

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

GOLD_PATH   = "/app/data/gold"
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_pipeline")
PYTHON      = sys.executable

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Job Store (thread-safe)
# ─────────────────────────────────────────────────────────────────────────────

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()

# Gold data cache: {kw_safe: {"data": {...}, "ts": float}}
_DATA_CACHE: dict[str, dict] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

def _job_create(keyword: str) -> str:
    job_id = str(uuid.uuid4())[:8]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id":  job_id,
            "keyword": keyword,
            "status":  "queued",   # queued | running | done | failed
            "step":    "",
            "logs":    [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "error":   None,
        }
    return job_id

def _job_update(job_id: str, **kwargs):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(kwargs)

def _job_log(job_id: str, line: str):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id]["logs"].append(line)
    log.info(f"[{job_id}] {line}")


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Social Media Analytics API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def kw_safe(keyword: str) -> str:
    return keyword.strip().lower().replace(" ", "_")


def read_parquet(path: str) -> list[dict]:
    """Read a parquet file/directory and return list-of-dicts (JSON-safe)."""
    try:
        if os.path.isdir(path):
            parts = glob.glob(f"{path}/*.parquet")
            if not parts:
                return []
            df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
        else:
            df = pd.read_parquet(path)
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            df[col] = df[col].astype(str)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        log.warning(f"Could not read {path}: {e}")
        return []


def _run_subprocess(script_name: str, keyword: str, timeout: int) -> tuple[bool, str]:
    """Run a pipeline script, streaming stdout/stderr as it goes."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    try:
        result = subprocess.run(
            [PYTHON, script_path, keyword],
            capture_output=True, text=True,
            timeout=timeout, env=os.environ.copy(),
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            return False, output[-1200:]
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, f"Script {script_name} timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def _run_pipeline_background(job_id: str, keyword: str):
    """Runs ingest + process in a background thread. Updates job store throughout."""
    _job_update(job_id, status="running", step="ingest")
    _job_log(job_id, f"▶ Pipeline started for keyword: '{keyword}'")

    # Step 1: Ingest
    _job_log(job_id, "📡 [1/2] Fetching live data (YouTube API + Reddit)…")
    ok, msg = _run_subprocess("ingest.py", keyword, timeout=300)
    if not ok:
        _job_update(job_id, status="failed", step="ingest",
                    error=f"Ingestion failed: {msg[-600:]}",
                    finished_at=datetime.now(timezone.utc).isoformat())
        _job_log(job_id, f"❌ Ingest failed: {msg[-300:]}")
        return
    _job_log(job_id, "✅ Ingest complete. Bronze data saved.")

    # Step 2: PySpark
    _job_update(job_id, step="process")
    _job_log(job_id, "⚡ [2/2] Running PySpark Medallion pipeline (Bronze→Silver→Gold+ML)…")
    ok, msg = _run_subprocess("process.py", keyword, timeout=420)
    if not ok:
        _job_update(job_id, status="failed", step="process",
                    error=f"Processing failed: {msg[-600:]}",
                    finished_at=datetime.now(timezone.utc).isoformat())
        _job_log(job_id, f"❌ Processing failed: {msg[-300:]}")
        return

    # Bust data cache for this keyword
    kw = kw_safe(keyword)
    with _JOBS_LOCK:
        _DATA_CACHE.pop(kw, None)

    _job_update(job_id, status="done", step="complete",
                finished_at=datetime.now(timezone.utc).isoformat())
    _job_log(job_id, "🎉 Pipeline complete! Gold data is ready.")


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    keyword: str


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics-api", "version": "3.0.0",
            "active_jobs": sum(1 for j in _JOBS.values() if j["status"] == "running")}


@app.post("/api/pipeline/run")
def run_pipeline(body: PipelineRequest, background_tasks: BackgroundTasks):
    """
    Trigger ingestion + PySpark processing pipeline asynchronously.
    Returns a job_id immediately — poll /api/pipeline/status/{job_id} for updates.
    """
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    # Prevent duplicate concurrent runs for the same keyword
    with _JOBS_LOCK:
        for j in _JOBS.values():
            if j["keyword"] == keyword and j["status"] in ("queued", "running"):
                return {
                    "job_id":  j["job_id"],
                    "status":  j["status"],
                    "message": "Pipeline already running for this keyword",
                }

    job_id = _job_create(keyword)
    log.info(f"=== Pipeline queued: '{keyword}' (job_id={job_id}) ===")

    background_tasks.add_task(_run_pipeline_background, job_id, keyword)

    return {
        "job_id":   job_id,
        "keyword":  keyword,
        "status":   "queued",
        "message":  "Pipeline started in background. Poll /api/pipeline/status/{job_id}",
        "poll_url": f"/api/pipeline/status/{job_id}",
    }


@app.get("/api/pipeline/status/{job_id}")
def pipeline_status(job_id: str):
    """Return current status, step, log lines, and errors for a pipeline job."""
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job


@app.get("/api/pipeline/history")
def pipeline_history():
    """Return all jobs from the session, newest first."""
    with _JOBS_LOCK:
        jobs = sorted(_JOBS.values(), key=lambda j: j["started_at"], reverse=True)
    return {"jobs": jobs}


@app.get("/api/data")
def get_data(keyword: str = Query(..., description="Analysis keyword")):
    """Return all gold-layer analytical data for the given keyword."""
    kw = kw_safe(keyword)
    g  = GOLD_PATH

    # Check cache
    cached = _DATA_CACHE.get(kw)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL_SECONDS:
        log.info(f"[cache hit] Returning cached data for '{keyword}'")
        return cached["data"]

    # Parquet directories (Spark writes partitioned dirs)
    sentiment   = read_parquet(f"{g}/sentiment_{kw}")
    yt_timeline = read_parquet(f"{g}/yt_timeline_{kw}")
    rd_timeline = read_parquet(f"{g}/reddit_timeline_{kw}")
    spikes      = read_parquet(f"{g}/yt_spikes_{kw}")
    top_videos  = read_parquet(f"{g}/top_videos_{kw}")
    subreddits  = read_parquet(f"{g}/subreddits_{kw}")

    # Single parquet files (pandas writes)
    predictions   = read_parquet(f"{g}/predictions_{kw}.parquet")
    feat_import   = read_parquet(f"{g}/feature_importance_{kw}.parquet")
    model_metrics = read_parquet(f"{g}/model_metrics_{kw}.parquet")
    topic_recs    = read_parquet(f"{g}/topic_recommendations_{kw}.parquet")
    content_gaps  = read_parquet(f"{g}/content_gaps_{kw}.parquet")

    # Sort timelines
    yt_timeline.sort(key=lambda r: str(r.get("published_date", "")))
    rd_timeline.sort(key=lambda r: str(r.get("created_date", "")))

    viability_score = next(
        (r.get("raw_score") for r in topic_recs if r.get("metric") == "TOTAL_VIABILITY"),
        None
    )

    payload = {
        "keyword":         keyword,
        "sentiment":       sentiment,
        "yt_timeline":     yt_timeline,
        "rd_timeline":     rd_timeline,
        "spikes":          spikes,
        "top_videos":      top_videos,
        "subreddits":      subreddits,
        "predictions":     predictions,
        "feat_import":     feat_import,
        "model_metrics":   model_metrics,
        "topic_recs":      topic_recs,
        "viability_score": viability_score,
        "content_gaps":    content_gaps,
    }

    # Store in cache
    _DATA_CACHE[kw] = {"data": payload, "ts": time.time()}
    return payload


@app.get("/api/keywords")
def list_keywords():
    """Return list of keywords that have been analysed (from Gold layer)."""
    gold = Path(GOLD_PATH)
    if not gold.exists():
        return {"keywords": []}
    seen = set()
    for p in gold.iterdir():
        name = p.name
        for prefix in ["sentiment_", "top_videos_", "predictions_"]:
            if name.startswith(prefix):
                kw = name[len(prefix):].replace(".parquet", "").replace("_", " ")
                seen.add(kw)
    return {"keywords": sorted(seen)}


def _avg(rows: list[dict], key: str, default: float = 0.0) -> float:
    vals = [float(r.get(key) or 0) for r in rows if r.get(key) is not None]
    return sum(vals) / len(vals) if vals else default


def _extract_json_array(text: str) -> list[dict]:
    """Parse Gemini JSON, tolerating fenced output or brief surrounding prose."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", cleaned)
        if not match:
            return []
        parsed = json.loads(match.group(0))
    if isinstance(parsed, dict):
        parsed = parsed.get("ideas", [])
    return parsed if isinstance(parsed, list) else []


def _fallback_ideas(keyword: str, content_gaps: list[dict], top_videos: list[dict]) -> list[dict]:
    gaps = content_gaps[:3]
    if not gaps:
        gaps = [{"gap_phrase": keyword, "opportunity_score": 1}] * 3
    ideas = []
    for idx, gap in enumerate(gaps, start=1):
        phrase = gap.get("gap_phrase") or keyword
        ideas.append({
            "title": f"{phrase.title()}: What People Are Missing",
            "format": "Explainer with data-backed examples" if idx == 1 else "Comparison breakdown" if idx == 2 else "Practical tutorial",
            "target_audience": f"Viewers researching {keyword}",
            "rationale": f"Reddit demand signal found for '{phrase}', with limited matching YouTube coverage.",
        })
    return ideas


def _predict_video_ideas(keyword: str, ideas: list[dict], top_videos: list[dict]) -> list[dict]:
    """
    Score generated ideas with the persisted Spark Random Forest model.
    The model was trained on: like_count, comment_count, sentiment_score, engagement_rate.
    For an unmade idea, we estimate those pre-publish signals from topic averages plus
    the idea title/rationale sentiment, then let the RF model predict view_count.
    """
    kw = kw_safe(keyword)
    model_path = f"{GOLD_PATH}/rf_model_{kw}"
    if not ideas or not os.path.isdir(model_path):
        global_model_path = f"{GOLD_PATH}/rf_model_global"
        if not ideas or not os.path.isdir(global_model_path):
            return ideas
        model_path = global_model_path
        model_label = "global pretrained Spark Random Forest model"
    else:
        model_label = "keyword-adapted Spark Random Forest model"

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        from pyspark.sql import SparkSession
        from pyspark.ml.feature import VectorAssembler
        from pyspark.ml.regression import RandomForestRegressionModel

        sia = SentimentIntensityAnalyzer()
        base_like = _avg(top_videos, "like_count", 100.0)
        base_comments = _avg(top_videos, "comment_count", 10.0)
        base_engagement = _avg(top_videos, "engagement_rate", 1.0)
        avg_views = _avg(top_videos, "view_count", 0.0)

        feature_rows = []
        enriched = []
        for idx, idea in enumerate(ideas[:3], start=1):
            text = " ".join(str(idea.get(k, "")) for k in ("title", "format", "target_audience", "rationale"))
            sentiment = float(sia.polarity_scores(text)["compound"])
            sentiment_boost = 1 + max(sentiment, 0) * 0.25
            rank_boost = max(1.0, 1.18 - (idx - 1) * 0.08)
            est_like = max(base_like * sentiment_boost * rank_boost, 1.0)
            est_comments = max(base_comments * (1 + abs(sentiment) * 0.15) * rank_boost, 1.0)
            est_engagement = max(base_engagement * sentiment_boost, 0.01)

            enriched.append({
                **idea,
                "idea_rank": idx,
                "estimated_features": {
                    "like_count": round(est_like, 2),
                    "comment_count": round(est_comments, 2),
                    "sentiment_score": round(sentiment, 4),
                    "engagement_rate": round(est_engagement, 4),
                },
            })
            feature_rows.append({
                "idea_rank": idx,
                "like_count": float(est_like),
                "comment_count": float(est_comments),
                "sentiment_score": float(sentiment),
                "engagement_rate": float(est_engagement),
            })

        spark = (
            SparkSession.builder
            .appName(f"IdeaPrediction_{kw}")
            .master("local[*]")
            .config("spark.driver.memory", "1g")
            .config("spark.sql.shuffle.partitions", "1")
            .config("spark.ui.showConsoleProgress", "false")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("ERROR")

        df = spark.createDataFrame(feature_rows)
        assembled = VectorAssembler(
            inputCols=["like_count", "comment_count", "sentiment_score", "engagement_rate"],
            outputCol="features",
        ).transform(df)
        model = RandomForestRegressionModel.load(model_path)
        scored = model.transform(assembled).select("idea_rank", "prediction").toPandas().to_dict("records")
        spark.stop()

        by_rank = {int(row["idea_rank"]): max(float(row["prediction"]), 0.0) for row in scored}
        for idea in enriched:
            pred = by_rank.get(int(idea["idea_rank"]), 0.0)
            rmse_floor = max(avg_views * 0.15, pred * 0.2, 1000.0)
            idea["predicted_views"] = round(pred)
            idea["predicted_view_range"] = {
                "low": round(max(pred - rmse_floor, 0)),
                "high": round(pred + rmse_floor),
            }
            idea["prediction_method"] = model_label
        return enriched
    except Exception as e:
        log.warning(f"Idea prediction failed for '{keyword}': {e}")
        return ideas


@app.get("/api/prescribe")
def prescribe(keyword: str = Query(..., description="Analysis keyword")):
    """
    Generate video ideas with Gemini, then score those ideas with the
    keyword-specific Random Forest model saved by the pipeline.
    """
    gemini_key = get_gemini_api_key()
    if not gemini_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    kw = kw_safe(keyword)
    g  = GOLD_PATH

    top_videos    = read_parquet(f"{g}/top_videos_{kw}")
    sentiment     = read_parquet(f"{g}/sentiment_{kw}")
    subreddits    = read_parquet(f"{g}/subreddits_{kw}")
    topic_recs    = read_parquet(f"{g}/topic_recommendations_{kw}.parquet")
    model_metrics = read_parquet(f"{g}/model_metrics_{kw}.parquet")
    rd_timeline   = read_parquet(f"{g}/reddit_timeline_{kw}")
    content_gaps  = read_parquet(f"{g}/content_gaps_{kw}.parquet")

    top5_titles   = "\n  - ".join(v.get("title", "") for v in top_videos[:5])
    avg_lv_ratio  = sum(v.get("like_to_view_ratio", 0) for v in top_videos) / max(len(top_videos), 1)
    top3_subs     = ", ".join(s.get("subreddit", "") for s in subreddits[:3])
    top_sub_sizes = ", ".join(f"{s.get('subreddit','')}({int(s.get('post_count',0))} posts)" for s in subreddits[:3])
    gap_summary   = ", ".join(g.get("gap_phrase", "") for g in content_gaps[:5]) or "no explicit content gaps found"
    rec_summary   = next((r.get("note", "") for r in topic_recs if r.get("metric") == "TOTAL_VIABILITY"), "")
    viability     = next((r.get("raw_score") for r in topic_recs if r.get("metric") == "TOTAL_VIABILITY"), "N/A")
    r2_score      = model_metrics[0].get("r2", "N/A") if model_metrics else "N/A"
    growth_note   = next((r.get("note", "") for r in topic_recs if r.get("metric") == "growth_velocity"), "")
    sat_note      = next((r.get("note", "") for r in topic_recs if r.get("metric") == "saturation_penalty"), "")
    reddit_trend  = f"{len(rd_timeline)} active posting days in last 30 days" if rd_timeline else "no Reddit trend data"

    prompt = f"""You are a specialist content-strategy AI advisor. A YouTube creator is evaluating the keyword: '{keyword}'.

You have access to the following real analytics data — use it precisely in your recommendations.

📊 DATA SNAPSHOT:
- Top 5 performing videos on this topic:
  - {top5_titles}
- Average Like/View ratio: {avg_lv_ratio:.4f} ({avg_lv_ratio*100:.2f}%)
- Top Reddit communities discussing this topic: {top_sub_sizes}
- Reddit posting activity: {reddit_trend}
- Content gap phrases from Reddit demand: {gap_summary}
- Topic Viability Score: {viability}/100
- Overall viability assessment: {rec_summary}
- YouTube growth velocity note: {growth_note}
- Competition saturation note: {sat_note}
- Random Forest model R2: {r2_score}

Based ONLY on this data, generate exactly 3 video ideas that can later be scored by a predictive model.

Return ONLY valid JSON as an array. Do not wrap it in markdown.
Each item must have these exact keys:
- title
- format
- target_audience
- rationale
- distribution_strategy
- risk_warning

Make the ideas concrete and title-like. Reference content gaps and subreddit demand when useful."""

    try:
        import urllib.request, json as _json
        url     = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        req     = urllib.request.Request(
            url, data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result  = _json.loads(resp.read())
            ai_text = result["candidates"][0]["content"]["parts"][0]["text"]

        ideas = _extract_json_array(ai_text)
        if not ideas:
            ideas = _fallback_ideas(keyword, content_gaps, top_videos)
        predicted_ideas = _predict_video_ideas(keyword, ideas, top_videos)

        recommendation_text = "\n\n".join(
            (
                f"{i}. {idea.get('title', 'Untitled idea')}\n"
                f"Format: {idea.get('format', '')}\n"
                f"Predicted views: {int(idea.get('predicted_views', 0)):,}"
                if idea.get("predicted_views") is not None else
                f"{i}. {idea.get('title', 'Untitled idea')}\nFormat: {idea.get('format', '')}"
            )
            for i, idea in enumerate(predicted_ideas, start=1)
        )

        return {
            "keyword":         keyword,
            "viability_score": viability,
            "recommendations": recommendation_text,
            "video_ideas":     predicted_ideas,
            "prompt_context":  {
                "avg_like_view_ratio": avg_lv_ratio,
                "top_subreddits":      top3_subs,
                "assessment":          rec_summary,
                "model_r2":            r2_score,
            }
        }
    except Exception as e:
        log.error(f"Gemini API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=False, log_level="info")
