#!/usr/bin/env python3
"""
pretrain_keywords.py

Build the global Random Forest baseline before normal dashboard usage.

This script runs the existing ingestion + processing pipeline across a curated
set of 100 high-volume keywords. Each process.py run writes that keyword's
training rows to /app/data/gold/global_training_rows and refreshes the global
model at /app/data/gold/rf_model_global.

Usage:
  python data_pipeline/pretrain_keywords.py
  python data_pipeline/pretrain_keywords.py --limit 10
  python data_pipeline/pretrain_keywords.py --skip-existing
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


FAMOUS_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "chatgpt",
    "python programming",
    "web development",
    "data science",
    "cybersecurity",
    "blockchain",
    "cryptocurrency",
    "stock market",
    "personal finance",
    "real estate",
    "startup business",
    "digital marketing",
    "social media marketing",
    "content creation",
    "youtube growth",
    "video editing",
    "photography",
    "graphic design",
    "gaming",
    "minecraft",
    "fortnite",
    "valorant",
    "gta 6",
    "call of duty",
    "esports",
    "fitness",
    "weight loss",
    "muscle building",
    "home workout",
    "nutrition",
    "healthy recipes",
    "cooking",
    "street food",
    "travel vlog",
    "budget travel",
    "luxury travel",
    "cars",
    "electric vehicles",
    "tesla",
    "motorcycles",
    "football",
    "soccer",
    "cricket",
    "basketball",
    "nba",
    "ufc",
    "formula 1",
    "movies",
    "netflix",
    "anime",
    "marvel",
    "music production",
    "guitar",
    "piano",
    "fashion",
    "beauty",
    "skincare",
    "makeup",
    "productivity",
    "self improvement",
    "motivation",
    "study tips",
    "college life",
    "career advice",
    "job interview",
    "remote work",
    "freelancing",
    "side hustle",
    "ecommerce",
    "dropshipping",
    "amazon fba",
    "podcasting",
    "mental health",
    "meditation",
    "relationships",
    "parenting",
    "pets",
    "dogs",
    "cats",
    "gardening",
    "home decor",
    "interior design",
    "diy projects",
    "science",
    "space",
    "nasa",
    "climate change",
    "history",
    "geography",
    "politics",
    "news analysis",
    "education",
    "math",
    "language learning",
    "english speaking",
    "medical advice",
    "public speaking",
    "book summaries",
]


def kw_safe(keyword: str) -> str:
    return keyword.strip().lower().replace(" ", "_")


def has_keyword_training(gold: Path, keyword: str) -> bool:
    safe = kw_safe(keyword)
    marker = gold / "global_training_rows" / "_markers" / f"{safe}.done"
    legacy_dir = gold / "global_training_rows" / safe
    if marker.exists() or legacy_dir.exists():
        return True
    runs_root = gold / "global_training_rows"
    if not runs_root.exists():
        return False
    return any(p.is_dir() and p.name.startswith(f"{safe}__") for p in runs_root.iterdir())


def run_step(script: Path, keyword: str) -> int:
    print(f"\n=== {script.name}: {keyword} ===", flush=True)
    proc = subprocess.run([sys.executable, str(script), keyword], env=os.environ.copy())
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N keywords.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip keywords already present in global_training_rows.")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    ingest = here / "ingest.py"
    process = here / "process.py"
    gold = Path("/app/data/gold")
    keywords = FAMOUS_KEYWORDS[: args.limit] if args.limit else FAMOUS_KEYWORDS

    failures: list[tuple[str, str]] = []
    for idx, keyword in enumerate(keywords, start=1):
        if args.skip_existing and has_keyword_training(gold, keyword):
            print(f"[{idx}/{len(keywords)}] Skipping existing keyword: {keyword}")
            continue

        print(f"[{idx}/{len(keywords)}] Pretraining keyword: {keyword}")
        if run_step(ingest, keyword) != 0:
            failures.append((keyword, "ingest"))
            continue
        if run_step(process, keyword) != 0:
            failures.append((keyword, "process"))
            continue

    if failures:
        print("\nCompleted with failures:")
        for keyword, step in failures:
            print(f"- {keyword}: {step}")
        return 1

    print("\nGlobal pretraining complete.")
    print("Model path: /app/data/gold/rf_model_global")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
