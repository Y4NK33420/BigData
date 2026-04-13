#!/usr/bin/env python3
"""
ingest.py  —  Bronze Layer Ingestion
─────────────────────────────────────
Pulls data from YouTube Data API v3 and Reddit (web scraper — no API key needed).
Saves raw JSON to:
  /app/data/bronze/youtube/<keyword>_<timestamp>.json
  /app/data/bronze/reddit/<keyword>_<timestamp>.json

Usage:
  python ingest.py "artificial intelligence"
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

# ── Credentials from environment ──────────────────────────────────────────────
YOUTUBE_API_KEY   = os.environ.get("YOUTUBE_API_KEY", "")
REDDIT_USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT",
    "BigDataDashboard/1.0 (educational project)",
)

BRONZE_PATH = "/app/data/bronze"


# ─────────────────────────────────────────────────────────────────────────────
# YouTube Ingestion
# ─────────────────────────────────────────────────────────────────────────────

def ingest_youtube(keyword: str) -> list:
    """
    Fetch up to 25 videos from YouTube Data API v3.
    Quota cost: 100 (search) + ~1 (videos.list) = ~101 units per call.
    Daily free quota: 10,000 units → ~99 searches per day.
    """
    if not YOUTUBE_API_KEY:
        print("[YouTube] ❌ YOUTUBE_API_KEY not set in .env — skipping.")
        return []

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    print(f"[YouTube] 🔍 Searching: '{keyword}'")

    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

        # Search call (100 quota units)
        search_resp = youtube.search().list(
            q=keyword,
            part="id,snippet",
            type="video",
            maxResults=25,
            order="relevance",
            relevanceLanguage="en",
        ).execute()

        video_ids = [
            item["id"]["videoId"]
            for item in search_resp.get("items", [])
            if item["id"].get("kind") == "youtube#video"
        ]

        if not video_ids:
            print("[YouTube] ⚠️  No videos found.")
            return []

        # Stats call (1 quota unit total — all IDs in 1 request)
        stats_resp = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        ).execute()

        videos = []
        for item in stats_resp.get("items", []):
            stats   = item.get("statistics", {})
            snippet = item.get("snippet", {})
            videos.append({
                "video_id":     item["id"],
                "title":        snippet.get("title", ""),
                "description":  (snippet.get("description", "") or "")[:500],
                "channel":      snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count":   int(stats.get("viewCount",   0)),
                "like_count":   int(stats.get("likeCount",   0)),
                "comment_count":int(stats.get("commentCount",0)),
                "source":       "youtube",
                "ingested_at":  datetime.now(timezone.utc).isoformat(),
            })

        # Save to Bronze
        os.makedirs(f"{BRONZE_PATH}/youtube", exist_ok=True)
        ts      = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        kw_safe = keyword.replace(" ", "_").lower()
        outfile = f"{BRONZE_PATH}/youtube/{kw_safe}_{ts}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)

        print(f"[YouTube] ✅ {len(videos)} videos → {outfile}")
        return videos

    except HttpError as e:
        print(f"[YouTube] ❌ API error: {e}")
        return []
    except Exception as e:
        print(f"[YouTube] ❌ Unexpected error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Reddit Ingestion  (scraper — no API key / PRAW required)
# ─────────────────────────────────────────────────────────────────────────────

def ingest_reddit(keyword: str) -> list:
    """
    Search Reddit across r/all using reddit_scrap.search_reddit_keyword().
    Uses Reddit's public JSON endpoints — no OAuth credentials needed.

    Fetches up to 30 posts × 3 sort orders (relevance, hot, new) with
    built-in rate-limiting (≥1.2 s between requests, exponential backoff
    on 429/5xx).
    """
    # Import from the co-located scraper module
    import importlib.util, pathlib
    _here = pathlib.Path(__file__).parent
    spec  = importlib.util.spec_from_file_location(
        "reddit_scrap", _here / "reddit_scrap.py"
    )
    reddit_scrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reddit_scrap)

    print(f"[Reddit] 🔍 Scraping: '{keyword}'")

    try:
        raw_posts = reddit_scrap.search_reddit_keyword(
            keyword,
            limit=30,
            sort_orders=["relevance", "hot", "new"],
            time_filter="month",
            user_agent=REDDIT_USER_AGENT,
        )

        # Normalise to process.py schema
        posts = []
        for p in raw_posts:
            posts.append({
                "post_id":      p.get("post_id", ""),
                "title":        p.get("title", ""),
                "text":         (p.get("text", "") or "")[:1000],
                "subreddit":    p.get("subreddit", ""),
                "author":       p.get("author", "[deleted]"),
                "score":        p.get("score", 0) or 0,
                "upvote_ratio": p.get("upvote_ratio", 0.0) or 0.0,
                "num_comments": p.get("num_comments", 0) or 0,
                "created_utc":  p.get("created_utc"),
                "url":          p.get("url", ""),
                "source":       "reddit",
                "ingested_at":  datetime.now(timezone.utc).isoformat(),
            })

        # Save to Bronze
        os.makedirs(f"{BRONZE_PATH}/reddit", exist_ok=True)
        ts      = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        kw_safe = keyword.replace(" ", "_").lower()
        outfile = f"{BRONZE_PATH}/reddit/{kw_safe}_{ts}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)

        print(f"[Reddit] ✅ {len(posts)} posts → {outfile}")
        return posts

    except Exception as e:
        print(f"[Reddit] ❌ Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "technology"

    print("=" * 55)
    print(f"  Bronze Ingestion Pipeline  |  keyword: '{keyword}'")
    print("=" * 55)

    yt_data     = ingest_youtube(keyword)
    reddit_data = ingest_reddit(keyword)

    print("\n" + "=" * 55)
    print(f"  ✅ Ingestion complete!")
    print(f"     YouTube : {len(yt_data)} videos")
    print(f"     Reddit  : {len(reddit_data)} posts")
    print(f"     Saved to: {BRONZE_PATH}")
    print("=" * 55)
