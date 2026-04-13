#!/usr/bin/env python3
"""
api.py — FastAPI backend for the Social Media Analytics Dashboard.

Endpoints:
  GET  /health                  → healthcheck
  POST /api/pipeline/run        → trigger ingest + process pipeline
  GET  /api/data?keyword=xxx    → return all gold-layer data as JSON
"""

import os
import sys
import glob
import logging
import subprocess
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
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
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON      = sys.executable

app = FastAPI(title="Social Media Analytics API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # React dev server + prod
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
        # Convert timestamps/dates to strings for JSON serialisation
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            df[col] = df[col].astype(str)
        return df.fillna(0).to_dict(orient="records")
    except Exception as e:
        log.warning(f"Could not read {path}: {e}")
        return []


def run_script(script_name: str, keyword: str, timeout: int) -> tuple[bool, str]:
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    log.info(f"Running: {script_name} '{keyword}'")
    result = subprocess.run(
        [PYTHON, script_path, keyword],
        capture_output=True, text=True,
        timeout=timeout, env=os.environ.copy(),
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        log.error(f"{script_name} failed:\n{output[-1000:]}")
        return False, output[-800:]
    log.info(f"{script_name} succeeded")
    return True, result.stdout


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
    return {"status": "ok", "service": "analytics-api"}


@app.post("/api/pipeline/run")
def run_pipeline(body: PipelineRequest):
    """Trigger ingestion + PySpark processing pipeline."""
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    log.info(f"=== Pipeline started: '{keyword}' ===")

    # Step 1: Ingest
    try:
        ok, msg = run_script("ingest.py", keyword, timeout=120)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Ingestion timed out (120s)")
    if not ok:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {msg}")

    # Step 2: Process
    try:
        ok, msg = run_script("process.py", keyword, timeout=360)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Spark processing timed out (360s)")
    if not ok:
        raise HTTPException(status_code=500, detail=f"Spark processing failed: {msg}")

    log.info(f"=== Pipeline complete: '{keyword}' ===")
    return {
        "status":  "success",
        "keyword": keyword,
        "message": "Ingest → Bronze → Silver → Gold pipeline complete",
    }


@app.get("/api/data")
def get_data(keyword: str = Query(..., description="Analysis keyword")):
    """Return all gold-layer analytical data for the given keyword."""
    kw = kw_safe(keyword)
    g  = GOLD_PATH

    # Parquet directories (Spark writes partitioned dirs)
    sentiment     = read_parquet(f"{g}/sentiment_{kw}")
    yt_timeline   = read_parquet(f"{g}/yt_timeline_{kw}")
    rd_timeline   = read_parquet(f"{g}/reddit_timeline_{kw}")
    spikes        = read_parquet(f"{g}/yt_spikes_{kw}")
    top_videos    = read_parquet(f"{g}/top_videos_{kw}")
    subreddits    = read_parquet(f"{g}/subreddits_{kw}")

    # Single parquet files (pandas writes)
    predictions   = read_parquet(f"{g}/predictions_{kw}.parquet")
    feat_import   = read_parquet(f"{g}/feature_importance_{kw}.parquet")
    model_metrics = read_parquet(f"{g}/model_metrics_{kw}.parquet")

    # Sort timelines
    yt_timeline.sort(key=lambda r: str(r.get("published_date", "")))
    rd_timeline.sort(key=lambda r: str(r.get("created_date", "")))

    return {
        "keyword":       keyword,
        "sentiment":     sentiment,
        "yt_timeline":   yt_timeline,
        "rd_timeline":   rd_timeline,
        "spikes":        spikes,
        "top_videos":    top_videos,
        "subreddits":    subreddits,
        "predictions":   predictions,
        "feat_import":   feat_import,
        "model_metrics": model_metrics,
    }


@app.get("/api/keywords")
def list_keywords():
    """Return list of keywords that have been analysed."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=False, log_level="info")
