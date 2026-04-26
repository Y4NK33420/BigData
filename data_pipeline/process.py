#!/usr/bin/env python3
"""
process.py  —  PySpark Medallion Processing + ML
──────────────────────────────────────────────────
Bronze (raw JSON)  →  Silver (cleaned Parquet)  →  Gold (aggregated Parquet)
                                                  →  Predictions (Random Forest)

Analytics produced:
  Descriptive : sentiment distribution, engagement timeline, top videos, subreddits
  Diagnostic  : engagement spike heatmap, YouTube release vs Reddit discussion peak
  Predictive  : Random Forest view-count predictor + feature importances

Usage:
  python process.py "artificial intelligence"
"""

import os
import sys
import re
import json
from datetime import datetime

keyword  = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "technology"
kw_safe  = keyword.replace(" ", "_").lower()

BRONZE_PATH = "/app/data/bronze"
SILVER_PATH = "/app/data/silver"
GOLD_PATH   = "/app/data/gold"

os.makedirs(SILVER_PATH, exist_ok=True)
os.makedirs(GOLD_PATH,   exist_ok=True)

print("=" * 55)
print(f"  PySpark Medallion Pipeline  |  keyword: '{keyword}'")
print("=" * 55)

# ─────────────────────────────────────────────────────────────────────────────
# Spark Session
# ─────────────────────────────────────────────────────────────────────────────

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, udf, avg, count,
    sum as spark_sum,
    to_date, to_timestamp, hour, dayofweek,
    from_unixtime, concat_ws, when, coalesce,
)
from pyspark.sql.types import StringType, FloatType
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import RandomForestRegressor
from pyspark.ml.evaluation import RegressionEvaluator
import pandas as pd

spark = (
    SparkSession.builder
    .appName(f"SocialMedia_{kw_safe}")
    .master("local[*]")
    .config("spark.driver.memory",          "2g")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.ui.showConsoleProgress", "false")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("ERROR")


# ─────────────────────────────────────────────────────────────────────────────
# Load Bronze Data
# ─────────────────────────────────────────────────────────────────────────────

def latest_json(directory: str, keyword_safe: str):
    """Return path to the newest JSON file matching the keyword."""
    try:
        files = [
            f for f in os.listdir(directory)
            if keyword_safe in f.lower() and f.endswith(".json")
        ]
        if not files:                                    # fallback: any json
            files = [f for f in os.listdir(directory) if f.endswith(".json")]
        if not files:
            return None
        return os.path.join(directory, sorted(files)[-1])
    except FileNotFoundError:
        return None

yt_file     = latest_json(f"{BRONZE_PATH}/youtube", kw_safe)
reddit_file = latest_json(f"{BRONZE_PATH}/reddit",  kw_safe)

if not reddit_file:
    print("[ERROR] Reddit Bronze data missing — run ingest.py first.")
    spark.stop()
    sys.exit(1)

with open(reddit_file) as f: reddit_raw = json.load(f)

# ── Load live YouTube Bronze ───────────────────────────────────────────────
yt_raw = []
if yt_file:
    with open(yt_file) as f: yt_raw = json.load(f)
    print(f"[Bronze] Live YouTube: {len(yt_raw)} rows")
else:
    print("[Bronze] ⚠️  No live YouTube JSON found — will rely on static dataset")

# ── Merge with static YouTube dataset ─────────────────────────────────────
try:
    import importlib.util, pathlib
    _here    = pathlib.Path(__file__).parent
    _spec    = importlib.util.spec_from_file_location("static_loader", _here / "static_loader.py")
    _sl      = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_sl)
    static_rows = _sl.load_static_youtube(keyword=keyword, max_rows=3000)
    if static_rows:
        # Ensure type consistency: coerce numeric fields to int/float before Spark
        _INT_FIELDS   = ["view_count", "like_count", "comment_count", "subscribers", "delta_views"]
        _FLOAT_FIELDS = ["like_to_view_ratio", "comment_to_view_ratio", "engagement_velocity"]
        for r in static_rows:
            for f in _INT_FIELDS:   r[f] = int(r.get(f) or 0)
            for f in _FLOAT_FIELDS: r[f] = float(r.get(f) or 0)
        yt_raw = yt_raw + static_rows
        print(f"[Bronze] Combined YouTube (live + static): {len(yt_raw)} rows")
except Exception as _sl_err:
    print(f"[Bronze] ⚠️  Static loader failed (non-fatal): {_sl_err}")

if not yt_raw:
    print("[ERROR] No YouTube data available (live or static).")
    spark.stop()
    sys.exit(1)

if not reddit_raw:
    print("[ERROR] Reddit Bronze files are empty.")
    spark.stop()
    sys.exit(1)

# Drop extra fields not in Spark schema to prevent StructType mismatch
_YT_SCHEMA_FIELDS = {
    "video_id", "title", "description", "channel", "published_at",
    "view_count", "like_count", "comment_count", "like_to_view_ratio",
    "comment_to_view_ratio", "engagement_velocity", "comments", "tags",
    "source", "ingested_at",
}
yt_raw_clean = [{k: v for k, v in r.items() if k in _YT_SCHEMA_FIELDS} for r in yt_raw]

yt_df     = spark.createDataFrame(yt_raw_clean)
reddit_df = spark.createDataFrame(reddit_raw)

print(f"[Bronze] YouTube: {yt_df.count()} rows | Reddit: {reddit_df.count()} rows")


# ─────────────────────────────────────────────────────────────────────────────
# UDFs
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text):
    """Remove URLs, emojis, special chars; lowercase."""
    if not text:
        return ""
    text = re.sub(r"http[s]?://\S+", "", text)          # URLs
    text = re.sub(r"[^\x00-\x7F]+", " ", text)          # emojis / unicode
    text = re.sub(r"[^\w\s]", " ", text)                 # punctuation
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text

def vader_sentiment(text):
    """VADER compound score [-1, 1]. Initialised per call (local[*] mode)."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    if not text or len(text.strip()) < 3:
        return 0.0
    try:
        return float(SentimentIntensityAnalyzer().polarity_scores(str(text))["compound"])
    except Exception:
        return 0.0

def sentiment_label(score):
    if score is None: return "neutral"
    if score >=  0.05: return "positive"
    if score <= -0.05: return "negative"
    return "neutral"

def compute_comment_sentiment(comments):
    """VADER compound score averaged across scraped comments list."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    if not comments:
        return 0.0
    sia = SentimentIntensityAnalyzer()
    scores = [sia.polarity_scores(str(c))["compound"] for c in comments if c and str(c).strip()]
    return float(sum(scores) / len(scores)) if scores else 0.0

clean_udf          = udf(clean_text,             StringType())
sent_udf           = udf(vader_sentiment,        FloatType())
label_udf          = udf(sentiment_label,        StringType())
comment_sent_udf   = udf(compute_comment_sentiment, FloatType())


# ─────────────────────────────────────────────────────────────────────────────
# Bronze → Silver
# ─────────────────────────────────────────────────────────────────────────────

# YouTube Silver
yt_silver = (
    yt_df
    .withColumn("published_ts",         to_timestamp(col("published_at")))
    .withColumn("published_date",        to_date(col("published_ts")))
    .withColumn("upload_hour",           hour(col("published_ts")))
    .withColumn("day_of_week",           dayofweek(col("published_ts")))
    .withColumn("clean_title",           clean_udf(col("title")))
    .withColumn("clean_desc",            clean_udf(col("description")))
    .withColumn("combined_text",         concat_ws(" ", col("clean_title"), col("clean_desc")))
    .withColumn("sentiment_score",       sent_udf(col("combined_text")))
    .withColumn("sentiment_label",       label_udf(col("sentiment_score")))
    .withColumn("comment_sentiment",     comment_sent_udf(col("comments")))
    .withColumn("view_count",            col("view_count").cast("long"))
    .withColumn("like_count",            col("like_count").cast("long"))
    .withColumn("comment_count",         col("comment_count").cast("long"))
    .withColumn("like_to_view_ratio",    coalesce(col("like_to_view_ratio").cast("double"),   lit(0.0)))
    .withColumn("comment_to_view_ratio", coalesce(col("comment_to_view_ratio").cast("double"), lit(0.0)))
    .withColumn("engagement_velocity",   coalesce(col("engagement_velocity").cast("double"),   lit(0.0)))
    .withColumn("engagement_rate",
        when(col("view_count") > 0,
             (col("like_count") + col("comment_count")).cast("double")
             / col("view_count") * 100
        ).otherwise(lit(0.0))
    )
)

# Reddit Silver
reddit_silver = (
    reddit_df
    .withColumn("created_ts",    from_unixtime(col("created_utc")))
    .withColumn("created_date",  to_date(col("created_ts")))
    .withColumn("clean_title",   clean_udf(col("title")))
    .withColumn("clean_text",    clean_udf(col("text")))
    .withColumn("combined_text", concat_ws(" ", col("clean_title"), col("clean_text")))
    .withColumn("sentiment_score", sent_udf(col("combined_text")))
    .withColumn("sentiment_label", label_udf(col("sentiment_score")))
    .withColumn("score",         col("score").cast("long"))
    .withColumn("num_comments",  col("num_comments").cast("long"))
)

# Persist Silver
yt_silver.write.mode("overwrite").parquet(f"{SILVER_PATH}/youtube_{kw_safe}")
reddit_silver.write.mode("overwrite").parquet(f"{SILVER_PATH}/reddit_{kw_safe}")

yt_n     = yt_silver.count()
reddit_n = reddit_silver.count()
print(f"[Silver] YouTube: {yt_n} rows | Reddit: {reddit_n} rows")


# ─────────────────────────────────────────────────────────────────────────────
# Silver → Gold  (6 analytical tables)
# ─────────────────────────────────────────────────────────────────────────────

# Gold 1 — Sentiment Distribution (Descriptive)
yt_sent = (
    yt_silver.groupBy("sentiment_label")
    .agg(count("*").alias("count"), avg("sentiment_score").alias("avg_score"))
    .withColumn("source", lit("YouTube"))
)
reddit_sent = (
    reddit_silver.groupBy("sentiment_label")
    .agg(count("*").alias("count"), avg("sentiment_score").alias("avg_score"))
    .withColumn("source", lit("Reddit"))
)
yt_sent.union(reddit_sent).write.mode("overwrite").parquet(
    f"{GOLD_PATH}/sentiment_{kw_safe}"
)

# Gold 2 — YouTube Timeline (Descriptive)
(
    yt_silver.groupBy("published_date")
    .agg(
        spark_sum("view_count").alias("total_views"),
        spark_sum("like_count").alias("total_likes"),
        avg("sentiment_score").alias("avg_sentiment"),
        count("*").alias("video_count"),
    )
    .dropna(subset=["published_date"])
    .orderBy("published_date")
    .write.mode("overwrite").parquet(f"{GOLD_PATH}/yt_timeline_{kw_safe}")
)

# Gold 3 — Reddit Timeline (Descriptive / Diagnostic)
(
    reddit_silver.groupBy("created_date")
    .agg(
        spark_sum("score").alias("total_score"),
        spark_sum("num_comments").alias("total_comments"),
        avg("sentiment_score").alias("avg_sentiment"),
        count("*").alias("post_count"),
    )
    .dropna(subset=["created_date"])
    .orderBy("created_date")
    .write.mode("overwrite").parquet(f"{GOLD_PATH}/reddit_timeline_{kw_safe}")
)

# Gold 4 — Engagement Spike Heatmap (Diagnostic)
(
    yt_silver
    .groupBy("upload_hour", "day_of_week")
    .agg(avg("view_count").alias("avg_views"), count("*").alias("video_count"))
    .dropna(subset=["upload_hour", "day_of_week"])
    .write.mode("overwrite").parquet(f"{GOLD_PATH}/yt_spikes_{kw_safe}")
)

# Gold 5 — Top Videos (Descriptive)
(
    yt_silver
    .select("title", "channel", "view_count", "like_count", "comment_count",
            "like_to_view_ratio", "comment_to_view_ratio", "engagement_velocity",
            "sentiment_score", "sentiment_label", "comment_sentiment",
            "published_date", "engagement_rate")
    .orderBy(col("view_count").desc())
    .limit(20)
    .write.mode("overwrite").parquet(f"{GOLD_PATH}/top_videos_{kw_safe}")
)

# Gold 6 — Top Subreddits (Descriptive / Diagnostic)
(
    reddit_silver.groupBy("subreddit")
    .agg(
        count("*").alias("post_count"),
        avg("score").alias("avg_score"),
        avg("sentiment_score").alias("avg_sentiment"),
        spark_sum("num_comments").alias("total_comments"),
    )
    .orderBy(col("post_count").desc())
    .limit(20)
    .write.mode("overwrite").parquet(f"{GOLD_PATH}/subreddits_{kw_safe}")
)

print("[Gold] ✅ All 6 analytical tables saved!")


# ─────────────────────────────────────────────────────────────────────────────
# Predictive Analytics — Random Forest (MLlib)
# ─────────────────────────────────────────────────────────────────────────────

print("[Predictive] Training Random Forest …")

FEATURE_COLS = ["like_count", "comment_count", "sentiment_score", "engagement_rate"]

feature_df = (
    yt_silver
    .select("view_count", *FEATURE_COLS)
    .dropna()
    .withColumn("view_count",      col("view_count").cast("double"))
    .withColumn("like_count",      col("like_count").cast("double"))
    .withColumn("comment_count",   col("comment_count").cast("double"))
    .withColumn("sentiment_score", col("sentiment_score").cast("double"))
    .withColumn("engagement_rate", col("engagement_rate").cast("double"))
)

n_rows = feature_df.count()
print(f"[Predictive] Training samples: {n_rows}")

if n_rows >= 5:
    assembled = VectorAssembler(
        inputCols=FEATURE_COLS, outputCol="features"
    ).transform(feature_df)

    if n_rows >= 10:
        train, test = assembled.randomSplit([0.8, 0.2], seed=42)
    else:
        train = test = assembled   # use all when data is sparse

    rf_model = RandomForestRegressor(
        featuresCol="features",
        labelCol="view_count",
        numTrees=50,
        maxDepth=5,
        seed=42,
    ).fit(train)

    predictions = rf_model.transform(test)

    rmse = RegressionEvaluator(
        labelCol="view_count", predictionCol="prediction", metricName="rmse"
    ).evaluate(predictions)

    r2 = RegressionEvaluator(
        labelCol="view_count", predictionCol="prediction", metricName="r2"
    ).evaluate(predictions)

    print(f"[Predictive] RMSE: {rmse:,.0f}  |  R²: {r2:.4f}")

    # Save predictions
    (
        predictions
        .select("view_count", "prediction", "sentiment_score",
                "like_count", "comment_count")
        .limit(200)
        .toPandas()
        .to_parquet(f"{GOLD_PATH}/predictions_{kw_safe}.parquet")
    )

    # Save feature importances
    pd.DataFrame({
        "feature":    FEATURE_COLS,
        "importance": rf_model.featureImportances.toArray(),
    }).sort_values("importance", ascending=False).to_parquet(
        f"{GOLD_PATH}/feature_importance_{kw_safe}.parquet"
    )

    # Save model metrics
    pd.DataFrame([{
        "keyword":          keyword,
        "rmse":             rmse,
        "r2":               r2,
        "training_samples": n_rows,
        "timestamp":        datetime.utcnow().isoformat(),
    }]).to_parquet(f"{GOLD_PATH}/model_metrics_{kw_safe}.parquet")

    print("[Predictive] ✅ Predictions & feature importance saved!")
else:
    print(f"[Predictive] ⚠️  Only {n_rows} samples — need ≥5. Skipping RF.")

spark.stop()
print(f"\n✅ Medallion pipeline complete!  Gold tables → {GOLD_PATH}")

# ─────────────────────────────────────────────────────────────────────────────
# Prescriptive — Topic Viability Scoring (Recommender)
# ─────────────────────────────────────────────────────────────────────────────

print("[Recommender] Computing topic viability score …")
try:
    import importlib.util, pathlib
    _here = pathlib.Path(__file__).parent
    spec  = importlib.util.spec_from_file_location("recommender", _here / "recommender.py")
    recommender = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recommender)

    recommender.compute_topic_recommendation(
        keyword=keyword,
        yt_rows=yt_raw,
        reddit_rows=reddit_raw,
        gold_path=GOLD_PATH,
    )

    # Content Gap Analysis
    recommender.compute_content_gaps(
        keyword=keyword,
        yt_rows=yt_raw,
        reddit_rows=reddit_raw,
        gold_path=GOLD_PATH,
        top_n=10,
    )
except Exception as _rec_err:
    print(f"[Recommender] ⚠️  Scoring failed (non-fatal): {_rec_err}")
