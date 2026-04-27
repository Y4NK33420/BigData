#!/usr/bin/env python3
"""
static_loader.py  —  Static YouTube Dataset Integration
─────────────────────────────────────────────────────────
Loads the YouNiverse-style YouTube TSV dataset from the mounted Windows path
(accessible via WSL at /mnt/c/Users/asus/Downloads/youtube_data/).

Files used:
  df_channels_en.tsv   — channel metadata: name, category, subscribers
  df_timeseries_en.tsv — weekly channel stats: views, subs, delta_views

Returns a list of dicts in the same Bronze schema used by ingest.py,
so process.py can union them directly with the live-ingested videos.

Usage:
  rows = load_static_youtube(keyword="football", max_rows=2000)
"""

import os
import re
import math
import pandas as pd

def _resolve_static_base() -> str:
    """Resolve static YouTube dataset root for Docker and local dev."""
    candidates = [
        os.environ.get("YOUTUBE_STATIC_PATH", "").strip(),
        "/mnt/youtube_static",
        "/mnt/c/Users/asus/Downloads/youtube_data",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    # Keep default Docker path for stable log messages.
    return "/mnt/youtube_static"


STATIC_BASE = _resolve_static_base()
CHANNELS_FILE   = os.path.join(STATIC_BASE, "df_channels_en.tsv")
TIMESERIES_FILE = os.path.join(STATIC_BASE, "df_timeseries_en.tsv")


# Keyword → YouTube category mapping for better static dataset matching
# Keys are lowercase keywords; values are category substrings to match (case-insensitive)
_KW_TO_CATEGORY: dict[str, list[str]] = {
    # Sports
    "football": ["sport"],
    "soccer":   ["sport"],
    "fifa":     ["sport"],
    "nfl":      ["sport"],
    "basketball":["sport"],
    "nba":      ["sport"],
    "cricket":  ["sport"],
    "tennis":   ["sport"],
    "golf":     ["sport"],
    "f1":       ["sport"],
    "formula":  ["sport"],
    "rugby":    ["sport"],
    "hockey":   ["sport"],
    "boxing":   ["sport"],
    # Gaming
    "gaming":   ["gaming"],
    "game":     ["gaming"],
    "minecraft":["gaming"],
    "fortnite": ["gaming"],
    "valorant": ["gaming"],
    "esports":  ["gaming"],
    "twitch":   ["gaming"],
    # Music
    "music":    ["music"],
    "rap":      ["music"],
    "pop":      ["music"],
    "hip hop":  ["music"],
    # Education / Tech
    "ai":       ["education", "science", "tech"],
    "machine learning": ["education", "science"],
    "python":   ["education", "science", "tech"],
    "coding":   ["education", "science", "tech"],
    "tech":     ["science", "tech"],
    # Entertainment
    "comedy":   ["comedy", "entertainment"],
    "memes":    ["comedy", "entertainment"],
    "reaction": ["entertainment"],
    "vlog":     ["people", "entertainment"],
    # Food / lifestyle
    "cooking":  ["howto", "food"],
    "recipe":   ["howto", "food"],
    "fitness":  ["howto", "people"],
    "workout":  ["howto", "people"],
    "beauty":   ["howto", "people"],
}

def _get_category_filters(keyword: str) -> list[str]:
    """Return category substrings to match for this keyword. Falls back to keyword itself."""
    kw = keyword.lower().strip()
    # Direct lookup
    if kw in _KW_TO_CATEGORY:
        return _KW_TO_CATEGORY[kw]
    # Partial match — a word in the keyword matches a mapping key
    for key, cats in _KW_TO_CATEGORY.items():
        if key in kw or kw in key:
            return cats
    # Fallback: search by keyword word in channel name
    return []

def _keyword_matches_category(category: str, channel_name: str, keyword: str, cat_filters: list[str]) -> bool:
    """True if the channel's category matches one of our filters, or keyword is in channel name."""
    cat_lower  = (category or "").lower()
    name_lower = (channel_name or "").lower()
    kw_lower   = keyword.lower()
    if cat_filters:
        return any(f in cat_lower for f in cat_filters)
    # Fallback: keyword word in channel name
    return any(w in name_lower for w in kw_lower.split() if len(w) > 3)


def load_static_youtube(keyword: str, max_rows: int = 3000) -> list[dict]:
    """
    Filter the static dataset by keyword and return Bronze-compatible rows.
    Strategy:
      1. Read channels file → filter by keyword in category or channel name
      2. Read timeseries file → join on channel IDs; aggregate per channel
      3. Return synthetic "video" rows with enriched channel-level stats
    """
    if not os.path.exists(CHANNELS_FILE):
        print(f"[StaticLoader] ⚠️  Dataset not found at {CHANNELS_FILE}. Skipping.")
        return []
    if not os.path.exists(TIMESERIES_FILE):
        print(f"[StaticLoader] ⚠️  Timeseries file not found at {TIMESERIES_FILE}. Skipping.")
        return []

    print(f"[StaticLoader] 📂 Loading channels metadata…")
    try:
        # Read channels — channel is the ID column, name_cc is the display name
        ch_cols = ["channel", "category_cc", "name_cc", "subscribers_cc", "videos_cc", "join_date"]
        channels = pd.read_csv(
            CHANNELS_FILE, sep="\t", usecols=ch_cols,
            dtype=str, on_bad_lines="skip",
        )
        channels.columns = ["channel_id", "category", "channel_name", "subscribers", "video_count", "join_date"]
        channels["subscribers"] = pd.to_numeric(channels["subscribers"], errors="coerce").fillna(0)
        channels["video_count"]  = pd.to_numeric(channels["video_count"],  errors="coerce").fillna(0)

        # Resolve category filters for this keyword
        cat_filters = _get_category_filters(keyword)
        print(f"[StaticLoader] 🔎 Category filters for '{keyword}': {cat_filters or ['name-based fallback']}")

        # Filter channels by category or name
        mask = channels.apply(
            lambda r: _keyword_matches_category(r["category"], r["channel_name"], keyword, cat_filters),
            axis=1
        )
        matched = channels[mask].copy()

        if matched.empty:
            print(f"[StaticLoader] ⚠️  No category match for '{keyword}' — using top 1000 channels by subscribers.")
            matched = channels.nlargest(1000, "subscribers")

        print(f"[StaticLoader] ✅ {len(matched)} channels matched keyword '{keyword}'")

        # Now read timeseries for those channel IDs
        matched_ids = set(matched["channel_id"].tolist())
        print(f"[StaticLoader] ⏳ Streaming timeseries file (large — may take a moment)…")

        # Read in chunks to avoid loading all 21M rows
        chunk_size = 200_000
        agg_rows = []
        seen = set()

        for chunk in pd.read_csv(
            TIMESERIES_FILE, sep="\t",
            usecols=["channel", "category", "datetime", "views", "delta_views"],
            dtype={"channel": str, "category": str, "datetime": str, "views": str, "delta_views": str},
            on_bad_lines="skip",
            chunksize=chunk_size,
        ):
            chunk = chunk[chunk["channel"].isin(matched_ids)]
            if chunk.empty:
                continue
            chunk["views"]       = pd.to_numeric(chunk["views"],       errors="coerce").fillna(0)
            chunk["delta_views"] = pd.to_numeric(chunk["delta_views"], errors="coerce").fillna(0)

            # Aggregate per channel: max views, sum delta (= new views over period), latest date
            grouped = (
                chunk.groupby("channel")
                .agg(
                    total_views=("views",       "max"),
                    delta_views =("delta_views", "sum"),
                    last_date   =("datetime",    "max"),
                    category    =("category",    "first"),
                )
                .reset_index()
            )
            agg_rows.append(grouped)
            seen.update(chunk["channel"].tolist())
            if len(seen) >= max_rows:
                break

        if not agg_rows:
            print(f"[StaticLoader] ⚠️  No timeseries rows matched the filtered channels.")
            # Fall back to channels-only data
            agg_df = matched.rename(columns={"subscribers": "total_views"}).assign(
                delta_views=0, last_date="2024-01-01", category=matched["category"]
            ).head(max_rows)
        else:
            agg_df = pd.concat(agg_rows, ignore_index=True)
            agg_df = agg_df.groupby("channel").agg(
                total_views=("total_views", "max"),
                delta_views=("delta_views", "sum"),
                last_date  =("last_date",   "max"),
                category   =("category",    "first"),
            ).reset_index()

        # Merge with channel metadata for names/subscribers
        agg_df = agg_df.merge(
            matched[["channel_id", "channel_name", "subscribers", "video_count"]],
            left_on="channel", right_on="channel_id", how="left"
        )

        print(f"[StaticLoader] 🔢 Building {min(len(agg_df), max_rows)} synthetic Bronze rows…")

        # Build bronze-schema rows
        rows = []
        for _, row in agg_df.head(max_rows).iterrows():
            view_count   = int(row["total_views"] or 0)
            delta        = int(row["delta_views"] or 0)
            subscribers  = int(row["subscribers"] or 0)
            video_count  = int(row["video_count"] or 0)
            # Estimate like_count as ~4% of views (YouTube average)
            like_count   = int(view_count * 0.04)
            comment_count = int(view_count * 0.005)
            lv_ratio     = round(like_count / view_count, 6) if view_count > 0 else 0.0
            cv_ratio     = round(comment_count / view_count, 6) if view_count > 0 else 0.0
            ev           = round((like_count + comment_count) / math.sqrt(view_count), 4) if view_count > 0 else 0.0

            last_date = str(row.get("last_date") or "2024-01-01")[:10]

            rows.append({
                "video_id":              row["channel"],
                "title":                 f"[{keyword.title()}] Channel: {row.get('channel_name', row['channel'])}",
                "description":           f"Category: {row.get('category', '')}. Subscribers: {subscribers:,}. Videos: {video_count}.",
                "channel":               str(row.get("channel_name") or row["channel"]),
                "published_at":          f"{last_date}T00:00:00Z",
                "view_count":            view_count,
                "like_count":            like_count,
                "comment_count":         comment_count,
                "like_to_view_ratio":    lv_ratio,
                "comment_to_view_ratio": cv_ratio,
                "engagement_velocity":   ev,
                "comments":              [],
                "tags":                  [keyword, str(row.get("category", ""))],
                "source":                "youtube_static",
                "ingested_at":           "2024-01-01T00:00:00Z",
                # Extra static-dataset fields for richer ML
                "subscribers":           subscribers,
                "delta_views":           delta,
            })

        print(f"[StaticLoader] ✅ {len(rows)} static YouTube rows loaded for '{keyword}'")
        return rows

    except Exception as e:
        print(f"[StaticLoader] ❌ Error loading static dataset: {e}")
        return []
