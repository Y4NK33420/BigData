#!/usr/bin/env python3
"""
spark_server.py
───────────────
Flask REST API running inside the Spark container.
Acts as the bridge between the Streamlit UI and the PySpark pipeline.

Endpoints:
  GET  /health           → healthcheck for docker-compose
  POST /pipeline?keyword → runs ingest.py then process.py synchronously
"""

import os
import sys
import logging
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def run_script(script_name: str, keyword: str, timeout: int) -> tuple[bool, str]:
    """Run a Python script with the given keyword argument."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    log.info(f"Running: {script_name} '{keyword}'")

    result = subprocess.run(
        [PYTHON, script_path, keyword],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=os.environ.copy(),
    )

    output = result.stdout + result.stderr
    if result.returncode != 0:
        log.error(f"{script_name} failed:\n{output[-1000:]}")
        return False, output[-800:]

    log.info(f"{script_name} succeeded:\n{result.stdout[-400:]}")
    return True, result.stdout


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Docker healthcheck endpoint."""
    return jsonify({"status": "ok", "service": "spark-analytics-server"})


@app.route("/pipeline", methods=["POST"])
def pipeline():
    """
    Trigger the full analytics pipeline for a keyword.
    Runs synchronously — Streamlit will block with a spinner.
    """
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "keyword query parameter is required"}), 400

    log.info(f"=== Pipeline started for keyword: '{keyword}' ===")

    # ── Step 1: Ingest ────────────────────────────────────────────
    try:
        ok, msg = run_script("ingest.py", keyword, timeout=120)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Ingestion timed out after 120s"}), 504
    except Exception as e:
        return jsonify({"error": f"Ingestion error: {str(e)}"}), 500

    if not ok:
        return jsonify({"error": f"Ingestion failed: {msg}"}), 500

    # ── Step 2: Process (PySpark Medallion + ML) ──────────────────
    try:
        ok, msg = run_script("process.py", keyword, timeout=360)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Spark processing timed out after 360s"}), 504
    except Exception as e:
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

    if not ok:
        return jsonify({"error": f"Spark processing failed: {msg}"}), 500

    log.info(f"=== Pipeline complete for keyword: '{keyword}' ===")
    return jsonify({
        "status":  "success",
        "keyword": keyword,
        "message": "Ingest → Bronze → Silver → Gold pipeline complete",
    })


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting Spark Analytics Server on port 5000 …")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
