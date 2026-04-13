#!/usr/bin/env python3
"""
reddit_scrap.py  —  Reddit Web Scraper (no OAuth / PRAW required)
──────────────────────────────────────────────────────────────────
Uses Reddit's public JSON endpoints (*.reddit.com/r/<sub>/<sort>.json)
which are accessible without an API key as long as a valid User-Agent
is supplied and rate limits are respected.

Reddit's unauthenticated rate limit:
  • ~1 request per second sustained
  • Burst up to ~5–10 req/s before 429s start appearing
  • _safe_request() handles 429 / 5xx with exponential backoff

Public usage:
  get_reddit_finance_data_json()   — finance/ticker subreddits
  search_reddit_keyword()          — generic keyword → r/all search
"""

import time
import random
import requests
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Rate-limit config
# ---------------------------------------------------------------------------
# Seconds to sleep between every individual HTTP request (per session).
# With max_workers=2 this keeps the global rate at ≤ 2 req/s sustained.
_PER_REQUEST_DELAY: float = 1.2          # polite floor between requests
_COMMENT_DELAY:     float = 1.5          # slightly longer for comment pages
_BETWEEN_SUBS:      float = 1.0          # sleep between sureddit tasks

# ---------------------------
# Helpers
# ---------------------------
def _safe_request(
    session: requests.Session,
    url: str,
    params: dict = None,
    headers: dict = None,
    max_retries: int = 6,
    backoff_factor: float = 2.0,
    timeout: int = 15,
) -> Optional[requests.Response]:
    """
    GET with exponential backoff on transient errors (429, 502, 503, 504).

    Back-off schedule (backoff_factor=2):
      attempt 1 → 2s, 2 → 4s, 3 → 8s, 4 → 16s, 5 → 32s, 6 → 64s
    A small random jitter (±20 %) is added to avoid thundering-herd.
    """
    for attempt in range(1, max_retries + 1):
        try:
            r = session.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 502, 503, 504):
                base  = backoff_factor * (2 ** (attempt - 1))
                jitter = base * random.uniform(-0.2, 0.2)
                wait  = base + jitter
                print(
                    f"  → HTTP {r.status_code} from {url}. "
                    f"Backoff {wait:.1f}s (attempt {attempt}/{max_retries})"
                )
                time.sleep(wait)
                continue
            # Non-transient error — log and return as-is
            print(f"  → HTTP {r.status_code} from {url}: {r.text[:200]}")
            return r
        except requests.RequestException as e:
            base  = backoff_factor * (2 ** (attempt - 1))
            jitter = base * random.uniform(-0.2, 0.2)
            wait  = base + jitter
            print(f"  → RequestException: {e}. Backoff {wait:.1f}s (attempt {attempt}/{max_retries})")
            time.sleep(wait)

    print(f"  ✗ Failed to GET {url} after {max_retries} attempts.")
    return None


# ---------------------------------------------------------------------------
# Low-level fetch helpers
# ---------------------------------------------------------------------------

def get_subreddit_metadata(
    session: requests.Session,
    subreddit: str,
    headers: dict = None,
) -> Dict[str, Any]:
    """Fetch about.json metadata for a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/about.json"
    time.sleep(_PER_REQUEST_DELAY)
    r = _safe_request(session, url, headers=headers)
    if not r or r.status_code != 200:
        return {
            "subreddit": subreddit,
            "error": f"status_{getattr(r, 'status_code', 'no_response')}",
        }
    data = r.json().get("data", {})
    return {
        "subreddit":          subreddit,
        "title":              data.get("title"),
        "public_description": data.get("public_description"),
        "subscribers":        data.get("subscribers"),
        "active_user_count":  data.get("active_user_count"),
        "icon_img":           data.get("icon_img"),
        "header_img":         data.get("header_img"),
        "created_utc": (
            datetime.utcfromtimestamp(data["created_utc"]).isoformat()
            if data.get("created_utc") else None
        ),
    }


def fetch_posts(
    session: requests.Session,
    subreddit: str,
    limit: int = 50,
    sort: str = "hot",
    timeframe: str = "day",
    headers: dict = None,
) -> List[Dict[str, Any]]:
    """
    Fetch posts from a subreddit listing endpoint.
    sort: hot | new | top
    """
    sort = sort.lower()
    if sort not in ("hot", "new", "top"):
        sort = "hot"

    params = {"limit": min(limit, 100)}   # Reddit hard-caps at 100
    if sort == "top":
        params["t"] = timeframe

    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    time.sleep(_PER_REQUEST_DELAY)
    r = _safe_request(session, url, params=params, headers=headers)
    if not r or r.status_code != 200:
        return []

    posts = []
    for post in r.json().get("data", {}).get("children", []):
        d = post.get("data", {})
        posts.append({
            "id":                  d.get("id"),
            "name":                d.get("name"),
            "subreddit":           subreddit,
            "title":               d.get("title"),
            "selftext":            d.get("selftext") or None,
            "url":                 d.get("url"),
            "permalink": (
                f"https://www.reddit.com{d['permalink']}"
                if d.get("permalink") else None
            ),
            "upvotes":             d.get("score"),
            "score":               d.get("score"),
            "upvote_ratio":        d.get("upvote_ratio"),
            "num_comments":        d.get("num_comments"),
            "created_utc": (
                datetime.utcfromtimestamp(d["created_utc"]).isoformat()
                if d.get("created_utc") else None
            ),
            "author":              d.get("author"),
            "is_video":            d.get("is_video"),
            "thumbnail": (
                d.get("thumbnail")
                if d.get("thumbnail") and d.get("thumbnail") != "self"
                else None
            ),
            # Metadata fields
            "link_flair_text":     d.get("link_flair_text"),
            "author_flair_text":   d.get("author_flair_text"),
            "domain":              d.get("domain"),
            "edited":              d.get("edited"),
            "is_original_content": d.get("is_original_content"),
            "num_crossposts":      d.get("num_crossposts"),
            "over_18":             d.get("over_18"),
            "spoiler":             d.get("spoiler"),
            "locked":              d.get("locked"),
            "stickied":            d.get("stickied"),
        })
    return posts


def fetch_search_posts(
    session: requests.Session,
    query: str,
    subreddit: str = "all",
    limit: int = 25,
    sort: str = "relevance",
    time_filter: str = "month",
    headers: dict = None,
) -> List[Dict[str, Any]]:
    """
    Search Reddit posts via the public search JSON endpoint.
    Equivalent of PRAW's subreddit.search().

    Endpoint:  https://www.reddit.com/r/<sub>/search.json?q=<query>&...
    """
    sort = sort.lower()
    if sort not in ("relevance", "hot", "new", "top", "comments"):
        sort = "relevance"

    params = {
        "q":           query,
        "restrict_sr": "0" if subreddit == "all" else "1",
        "sort":        sort,
        "t":           time_filter,
        "limit":       min(limit, 100),
        "type":        "link",
    }
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    time.sleep(_PER_REQUEST_DELAY)
    r = _safe_request(session, url, params=params, headers=headers)
    if not r or r.status_code != 200:
        return []

    posts = []
    for post in r.json().get("data", {}).get("children", []):
        d = post.get("data", {})
        posts.append({
            "post_id":       d.get("id"),
            "title":         d.get("title") or "",
            "text":          (d.get("selftext") or "")[:1000],
            "subreddit":     d.get("subreddit"),
            "author":        d.get("author") or "[deleted]",
            "score":         d.get("score"),
            "upvote_ratio":  d.get("upvote_ratio"),
            "num_comments":  d.get("num_comments"),
            "created_utc":   d.get("created_utc"),
            "url":           d.get("url"),
            "permalink": (
                f"https://www.reddit.com{d['permalink']}"
                if d.get("permalink") else None
            ),
            "source":        "reddit",
        })
    return posts


def fetch_top_comments(
    session: requests.Session,
    post_id_or_permalink: str,
    top_n: int = 3,
    headers: dict = None,
) -> List[Dict[str, Any]]:
    """Fetch top-level comments for a Reddit post."""
    if post_id_or_permalink.startswith("t3_"):
        url = f"https://www.reddit.com/comments/{post_id_or_permalink.replace('t3_', '')}.json"
    elif post_id_or_permalink.startswith("/r/") or post_id_or_permalink.startswith("https://"):
        url = post_id_or_permalink
        if not url.endswith(".json"):
            url = url + ".json"
    else:
        url = f"https://www.reddit.com/comments/{post_id_or_permalink}.json"

    time.sleep(_COMMENT_DELAY)
    r = _safe_request(session, url, headers=headers)
    if not r or r.status_code != 200:
        return []

    try:
        data = r.json()
        if not isinstance(data, list) or len(data) < 2:
            return []
        comments = data[1].get("data", {}).get("children", [])
        results  = []
        for c in comments:
            if c.get("kind") != "t1":
                continue
            cd = c.get("data", {})
            results.append({
                "comment_id": cd.get("id"),
                "author":     cd.get("author"),
                "body":       cd.get("body"),
                "upvotes":    cd.get("score"),
                "score":      cd.get("score"),
                "created_utc": (
                    datetime.utcfromtimestamp(cd["created_utc"]).isoformat()
                    if cd.get("created_utc") else None
                ),
            })
            if len(results) >= top_n:
                break
        return results
    except Exception as e:
        print(f"  → Error parsing comments: {e}")
        return []


# ---------------------------
# Main Functions
# ---------------------------

def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen: set = set()
    deduped: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _collect_subreddit_payload(
    subreddit: str,
    *,
    limit_per_subreddit: int,
    sort: str,
    timeframe: str,
    top_comments: int,
    user_agent: str,
) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]], List[str]]:
    """Fetch metadata + posts (+ optional comments) for one subreddit."""
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    logs: List[str] = []

    metadata = get_subreddit_metadata(session, subreddit)
    posts    = fetch_posts(
        session, subreddit,
        limit=limit_per_subreddit,
        sort=sort,
        timeframe=timeframe,
    )

    logs.append(f"📥 /r/{subreddit} — {len(posts)} posts fetched.")

    if top_comments > 0 and posts:
        for post in posts:
            target = post.get("id") or post.get("permalink")
            post["top_comments"] = (
                fetch_top_comments(session, target, top_n=top_comments)
                if target else []
            )
    else:
        for post in posts:
            post["top_comments"] = []

    return subreddit, metadata, posts, logs


def get_reddit_finance_data_json(
    ticker: str = "AAPL",
    subreddits: Optional[List[str]] = None,
    limit_per_subreddit: int = 25,
    sort: str = "hot",
    timeframe: str = "day",
    top_comments: int = 2,
    user_agent: str = "finance-data-fetcher:v1.0 (educational project)",
) -> Dict[str, Any]:
    """
    Fetch subreddit metadata, posts, and top comments for finance tickers.
    Returns a dict and also prints JSON to stdout.

    Rate limiting:
      • max_workers is capped to 2 (≤2 concurrent sessions)
      • Each session sleeps _PER_REQUEST_DELAY between requests
      • _safe_request backs off on 429 / 5xx
    """
    if subreddits is None:
        subreddits = ["stocks", "investing", "wallstreetbets", "finance"]
    subreddits = list(subreddits)
    if ticker:
        subreddits.append(ticker)
    subreddits = _dedupe_preserve_order([s.strip() for s in subreddits if s])

    result: Dict[str, Any] = {
        "fetched_at": datetime.utcnow().isoformat(),
        "subreddits": {},
        "posts": [],
    }

    print("ℹ️ Fetching data from Reddit (scraper)…\n")

    # Cap workers to 2 to stay within polite rate limits
    max_workers = min(len(subreddits), 2)
    logs: List[str] = []
    payloads: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _collect_subreddit_payload,
                sub,
                limit_per_subreddit=limit_per_subreddit,
                sort=sort,
                timeframe=timeframe,
                top_comments=top_comments,
                user_agent=user_agent,
            ): sub
            for sub in subreddits
        }

        for future in as_completed(futures):
            subreddit, metadata, posts, sub_logs = future.result()
            payloads[subreddit] = (metadata, posts, sub_logs)

    for subreddit in subreddits:
        metadata, posts, sub_logs = payloads.get(
            subreddit, ({"subreddit": subreddit, "error": "missing"}, [], [])
        )
        result["subreddits"][subreddit] = metadata
        result["posts"].extend(posts)
        logs.extend(sub_logs)

    for line in logs:
        print(line)

    print("\n── Final JSON Output:\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


# ---------------------------------------------------------------------------
# Generic keyword search  (used by ingest.py as PRAW replacement)
# ---------------------------------------------------------------------------

def search_reddit_keyword(
    keyword: str,
    limit: int = 30,
    sort_orders: Optional[List[str]] = None,
    time_filter: str = "month",
    user_agent: str = "bigd-analytics-scraper:v1.0 (educational project)",
) -> List[Dict[str, Any]]:
    """
    Search Reddit for a keyword across r/all using multiple sort orders.
    This is the drop-in replacement for PRAW's subreddit.search().

    Parameters
    ----------
    keyword     : search query
    limit       : posts per sort order (max 100)
    sort_orders : list of sort modes to try; default ['relevance', 'hot', 'new']
    time_filter : 'hour'|'day'|'week'|'month'|'year'|'all'
    user_agent  : User-Agent header string

    Returns
    -------
    Deduplicated list of post dicts compatible with process.py schema:
      post_id, title, text, subreddit, author, score,
      upvote_ratio, num_comments, created_utc, url, source
    """
    if sort_orders is None:
        sort_orders = ["relevance", "hot", "new"]

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    posts:    List[Dict[str, Any]] = []
    seen_ids: set                  = set()

    for sort_order in sort_orders:
        print(f"  [Reddit Scraper] Searching '{keyword}' sort={sort_order} …")
        batch = fetch_search_posts(
            session,
            query=keyword,
            subreddit="all",
            limit=limit,
            sort=sort_order,
            time_filter=time_filter,
        )
        new_count = 0
        for post in batch:
            pid = post.get("post_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                posts.append(post)
                new_count += 1

        print(f"  [Reddit Scraper] → {new_count} new posts (total {len(posts)})")

        # Polite delay between sort-order requests (same session)
        time.sleep(_BETWEEN_SUBS)

    print(f"  [Reddit Scraper] ✅ {len(posts)} unique posts for '{keyword}'")
    return posts


# ---------------------------
# CLI Run Example
# ---------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        # python reddit_scrap.py search "artificial intelligence"
        kw = " ".join(sys.argv[2:]) or "technology"
        results = search_reddit_keyword(kw, limit=20)
        print(json.dumps(results[:3], indent=2, ensure_ascii=False))
    else:
        get_reddit_finance_data_json(
            ticker="TSLA",
            limit_per_subreddit=10,
            sort="hot",
            top_comments=2,
        )