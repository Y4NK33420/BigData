#!/usr/bin/env python3
"""
recommender.py  —  Topic Viability Scoring Engine
──────────────────────────────────────────────────
Computes a 0-100 topic viability score for a keyword based on:
  1. YouTube Growth Velocity    — engagement_velocity vs. avg
  2. YouTube Engagement Quality — like_to_view_ratio vs. avg
  3. YouTube Comment Sentiment  — VADER polarity of scraped comments
  4. Reddit Community Momentum  — avg sentiment + score of Reddit posts
  5. Saturation Penalty         — deductions for a flooded niche (too many high-view videos)

Outputs a Gold parquet: topic_recommendations_{kw}.parquet
  Columns: metric, value, score_component, recommendation

Called from process.py after Silver transformation.
"""

import math
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# ─────────────────────────────────────────────────────────────────────────────
# Weights  (must sum to 100)
# ─────────────────────────────────────────────────────────────────────────────

WEIGHTS = {
    "growth_velocity":   25,   # YouTube algorithmic momentum
    "engagement_quality":20,   # Like/View ratio quality signal
    "yt_comment_sentiment": 15, # YouTube comment tone
    "reddit_sentiment":  20,   # Reddit community warmth
    "saturation_penalty": 20,  # inverse of market saturation
}

_VADER = SentimentIntensityAnalyzer()


def _sentiment_to_score(compound: float) -> float:
    """Map VADER compound [-1, 1] → [0, 100]."""
    return round((compound + 1) / 2 * 100, 2)


def _growth_velocity_score(yt_rows: list[dict]) -> tuple[float, str]:
    """
    Compare each video's engagement_velocity to the topic mean.
    Score = % of videos above the mean, scaled 0-100.
    """
    velocities = [r.get("engagement_velocity", 0) or 0 for r in yt_rows]
    if not velocities:
        return 0.0, "No YouTube velocity data."
    mean_v = sum(velocities) / len(velocities)
    above  = sum(1 for v in velocities if v > mean_v)
    score  = round(above / len(velocities) * 100, 2)
    note   = (
        f"{above}/{len(velocities)} videos outperform the topic avg velocity "
        f"(mean={mean_v:.2f}). "
        + ("Strong momentum!" if score >= 60 else "Moderate growth signal.")
    )
    return score, note


def _engagement_quality_score(yt_rows: list[dict]) -> tuple[float, str]:
    """
    Average like_to_view_ratio, normalised against a 5% baseline.
    Ratios over 5% = full score; below 0.5% = zero.
    """
    ratios = [r.get("like_to_view_ratio", 0) or 0 for r in yt_rows]
    if not ratios:
        return 0.0, "No like/view data."
    avg_ratio = sum(ratios) / len(ratios)
    # Clamp to [0.005, 0.05] then scale to 0-100
    score = round(min(max(avg_ratio - 0.005, 0) / (0.05 - 0.005), 1) * 100, 2)
    note  = (
        f"Avg Like/View ratio: {avg_ratio:.4f}. "
        + (
            "Excellent audience approval." if score >= 70
            else "Average quality signal." if score >= 40
            else "Low quality signal — consider niche twist."
        )
    )
    return score, note


def _yt_comment_sentiment_score(yt_rows: list[dict]) -> tuple[float, str]:
    """
    VADER-score all scraped YouTube comments and average them.
    """
    compounds = []
    for row in yt_rows:
        for comment in (row.get("comments") or []):
            if comment and len(comment.strip()) > 5:
                score = _VADER.polarity_scores(str(comment))["compound"]
                compounds.append(score)
    if not compounds:
        return 50.0, "No comments fetched — defaulting to neutral."
    avg_compound = sum(compounds) / len(compounds)
    score = _sentiment_to_score(avg_compound)
    note  = (
        f"YouTube comments analyzed: {len(compounds)}. "
        f"Avg sentiment: {avg_compound:+.3f}. "
        + (
            "Positive viewer reception." if avg_compound >= 0.05
            else "Negative viewer reception — potential controversy." if avg_compound <= -0.05
            else "Neutral viewer reception."
        )
    )
    return score, note


def _reddit_sentiment_score(reddit_rows: list[dict]) -> tuple[float, str]:
    """
    Score based on avg compound sentiment of Reddit post titles + top_comments.
    """
    compounds = []
    for row in reddit_rows:
        text = " ".join(filter(None, [
            row.get("title", ""),
            row.get("text", ""),
        ]))
        for comment in (row.get("top_comments") or []):
            text += " " + str(comment)
        if text.strip():
            score = _VADER.polarity_scores(text)["compound"]
            compounds.append(score)
    if not compounds:
        return 50.0, "No Reddit data — defaulting to neutral."
    avg_compound = sum(compounds) / len(compounds)
    score = _sentiment_to_score(avg_compound)
    note  = (
        f"Reddit posts analyzed: {len(compounds)}. "
        f"Avg sentiment: {avg_compound:+.3f}. "
        + (
            "Community is excited about this topic." if avg_compound >= 0.05
            else "Community has negative associations with this topic." if avg_compound <= -0.05
            else "Community is neutral — room to define the narrative."
        )
    )
    return score, note


def _saturation_score(yt_rows: list[dict]) -> tuple[float, str]:
    """
    Penalise heavily saturated niches.
    Saturation = % of videos with > 100k views (lots of large players).
    Score = inverse of saturation (low saturation = high opportunity).
    """
    if not yt_rows:
        return 50.0, "No YouTube saturation data."
    high_view = sum(1 for r in yt_rows if (r.get("view_count") or 0) > 100_000)
    saturation_pct = high_view / len(yt_rows)
    # Invert: low saturation → high score
    score = round((1 - saturation_pct) * 100, 2)
    note  = (
        f"{high_view}/{len(yt_rows)} videos exceed 100k views. "
        + (
            "Low competition — great opportunity!" if score >= 70
            else "Moderate competition." if score >= 40
            else "Highly saturated — differentiate your angle."
        )
    )
    return score, note


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry-Point
# ─────────────────────────────────────────────────────────────────────────────

def compute_topic_recommendation(
    keyword: str,
    yt_rows: list[dict],
    reddit_rows: list[dict],
    gold_path: str,
) -> pd.DataFrame:
    """
    Run all scoring components, compute weighted total, and persist to Gold.

    Returns a DataFrame with one row per metric component + a summary row.
    """
    kw_safe = keyword.strip().lower().replace(" ", "_")

    # Evaluate each component
    gv_score,   gv_note   = _growth_velocity_score(yt_rows)
    eq_score,   eq_note   = _engagement_quality_score(yt_rows)
    yt_s_score, yt_s_note = _yt_comment_sentiment_score(yt_rows)
    rd_score,   rd_note   = _reddit_sentiment_score(reddit_rows)
    sat_score,  sat_note  = _saturation_score(yt_rows)

    components = [
        ("growth_velocity",      gv_score,   gv_note),
        ("engagement_quality",   eq_score,   eq_note),
        ("yt_comment_sentiment", yt_s_score, yt_s_note),
        ("reddit_sentiment",     rd_score,   rd_note),
        ("saturation_penalty",   sat_score,  sat_note),
    ]

    # Weighted total
    total = sum(
        WEIGHTS[name] * score / 100
        for name, score, _ in components
    )
    total = round(min(max(total, 0), 100), 2)

    # Build recommendation string
    if total >= 75:
        action = "🚀 High Opportunity: Strong signals across velocity, sentiment, and low competition. Publish now."
    elif total >= 50:
        action = "📈 Moderate Opportunity: Decent signals. Focus on differentiation — improving sentiment angle or targeting underserved sub-topics."
    elif total >= 30:
        action = "⚠️ Proceed Cautiously: Mixed signals. Research competitor gaps before committing significant resources."
    else:
        action = "🛑 Low Opportunity: Saturated or declining interest. Consider pivoting to a related niche."

    rows = []
    for name, score, note in components:
        rows.append({
            "keyword":         keyword,
            "metric":          name,
            "raw_score":       score,
            "weight":          WEIGHTS[name],
            "weighted_contribution": round(WEIGHTS[name] * score / 100, 2),
            "note":            note,
        })

    # Summary row
    rows.append({
        "keyword":               keyword,
        "metric":                "TOTAL_VIABILITY",
        "raw_score":             total,
        "weight":                100,
        "weighted_contribution": total,
        "note":                  action,
    })

    df = pd.DataFrame(rows)
    out = f"{gold_path}/topic_recommendations_{kw_safe}.parquet"
    df.to_parquet(out, index=False)
    print(f"[Recommender] ✅ Topic viability score: {total}/100 → {out}")
    print(f"[Recommender] 💡 {action}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Content Gap Analysis
# ─────────────────────────────────────────────────────────────────────────────

import re as _re
import collections

# Common question signals that indicate demand / unsatisfied curiosity
_QUESTION_WORDS = {"how", "why", "what", "when", "where", "who", "which", "best", "vs", "versus", "compare", "difference"}

def _extract_question_topics(posts: list[dict]) -> list[str]:
    """
    Extract distinctive multi-word phrases from Reddit post titles that
    look like questions or comparisons — these signal content demand.
    """
    phrases = []
    for p in posts:
        title = (p.get("title", "") or "").lower()
        words = _re.findall(r"[a-z]{3,}", title)
        if not _QUESTION_WORDS.isdisjoint(set(words)):
            # Extract 2–3 word bigrams/trigrams from the interesting part
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if not any(stop in bigram for stop in ["the ", " the ", " is ", " are ", " of "]):
                    phrases.append(bigram)
            for i in range(len(words) - 2):
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                phrases.append(trigram)
    return phrases


def _has_youtube_coverage(phrase: str, yt_rows: list[dict]) -> bool:
    """Check whether any YouTube video title/description already covers this phrase."""
    phrase_words = set(phrase.lower().split())
    for v in yt_rows:
        yt_text = (
            (v.get("title", "") or "") + " " +
            (v.get("description", "") or "")
        ).lower()
        yt_words = set(_re.findall(r"[a-z]{3,}", yt_text))
        if phrase_words.issubset(yt_words):
            return True
    return False


def compute_content_gaps(
    keyword: str,
    yt_rows: list[dict],
    reddit_rows: list[dict],
    gold_path: str,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Find sub-topics people are asking about on Reddit that don't yet have
    strong YouTube video coverage. These are genuine content opportunities.
    """
    kw_safe = keyword.strip().lower().replace(" ", "_")

    # Extract demand-signals from Reddit
    phrases = _extract_question_topics(reddit_rows)
    freq = collections.Counter(phrases)

    rows = []
    for phrase, demand_count in freq.most_common(50):
        covered = _has_youtube_coverage(phrase, yt_rows)
        if not covered:
            compound = _VADER.polarity_scores(phrase)["compound"]
            rows.append({
                "keyword":      keyword,
                "gap_phrase":   phrase,
                "demand_count": demand_count,
                "covered_on_yt": False,
                "phrase_sentiment": round(compound, 3),
                "opportunity_score": round(demand_count * (1 - abs(compound) * 0.3), 2),
            })

    # Sort by opportunity score
    df = pd.DataFrame(rows).sort_values("opportunity_score", ascending=False).head(top_n)
    if df.empty:
        print("[ContentGap] ⚠️ No clear gaps found for this keyword.")
        return df

    out = f"{gold_path}/content_gaps_{kw_safe}.parquet"
    df.to_parquet(out, index=False)
    print(f"[ContentGap] ✅ {len(df)} content gaps found → {out}")
    return df
