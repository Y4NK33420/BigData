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
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")

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


@app.get("/api/prescribe")
def prescribe(keyword: str = Query(..., description="Analysis keyword")):
    """
    Calls Gemini API with the aggregated Gold metrics to generate
    hyper-specific prescriptive action cards.
    Requires GEMINI_API_KEY to be set in .env
    """
    if not GEMINI_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")

    kw = kw_safe(keyword)
    g  = GOLD_PATH

    top_videos    = read_parquet(f"{g}/top_videos_{kw}")
    sentiment     = read_parquet(f"{g}/sentiment_{kw}")
    subreddits    = read_parquet(f"{g}/subreddits_{kw}")
    topic_recs    = read_parquet(f"{g}/topic_recommendations_{kw}.parquet")
    model_metrics = read_parquet(f"{g}/model_metrics_{kw}.parquet")
    rd_timeline   = read_parquet(f"{g}/reddit_timeline_{kw}")

    top5_titles   = "\n  - ".join(v.get("title", "") for v in top_videos[:5])
    avg_lv_ratio  = sum(v.get("like_to_view_ratio", 0) for v in top_videos) / max(len(top_videos), 1)
    top3_subs     = ", ".join(s.get("subreddit", "") for s in subreddits[:3])
    top_sub_sizes = ", ".join(f"{s.get('subreddit','')}({int(s.get('post_count',0))} posts)" for s in subreddits[:3])
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
- Topic Viability Score: {viability}/100
- Overall viability assessment: {rec_summary}
- YouTube growth velocity note: {growth_note}
- Competition saturation note: {sat_note}

Based ONLY on this data, give exactly 3 tightly specific, data-driven recommendations:
1. **Video Concept**: Suggest a precise video title + format + target audience angle that directly fills a gap visible from the data above.
2. **Distribution Strategy**: Which exact subreddits to target and what framing works for each community (based on their post counts and sentiment levels).
3. **Content Risk Warning**: One specific thing to avoid (angle, framing, or claim) based on the saturation and sentiment signals.

Be concrete. Reference the actual data. No generic advice."""

    try:
        import urllib.request, json as _json
        url     = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        req     = urllib.request.Request(
            url, data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result  = _json.loads(resp.read())
            ai_text = result["candidates"][0]["content"]["parts"][0]["text"]

        return {
            "keyword":         keyword,
            "viability_score": viability,
            "recommendations": ai_text,
            "prompt_context":  {
                "avg_like_view_ratio": avg_lv_ratio,
                "top_subreddits":      top3_subs,
                "assessment":          rec_summary,
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
