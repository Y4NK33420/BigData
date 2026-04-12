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
    from_unixtime, concat_ws, when,
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

if not yt_file or not reddit_file:
    print("[ERROR] Bronze data missing — run ingest.py first.")
    spark.stop()
    sys.exit(1)

with open(yt_file)     as f: yt_raw     = json.load(f)
with open(reddit_file) as f: reddit_raw = json.load(f)

if not yt_raw or not reddit_raw:
    print("[ERROR] Bronze files are empty.")
    spark.stop()
    sys.exit(1)

yt_df     = spark.createDataFrame(yt_raw)
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

clean_udf = udf(clean_text,       StringType())
sent_udf  = udf(vader_sentiment,  FloatType())
label_udf = udf(sentiment_label,  StringType())


# ─────────────────────────────────────────────────────────────────────────────
# Bronze → Silver
# ─────────────────────────────────────────────────────────────────────────────

# YouTube Silver
yt_silver = (
    yt_df
    .withColumn("published_ts",   to_timestamp(col("published_at")))
    .withColumn("published_date", to_date(col("published_ts")))
    .withColumn("upload_hour",    hour(col("published_ts")))
    .withColumn("day_of_week",    dayofweek(col("published_ts")))
    .withColumn("clean_title",    clean_udf(col("title")))
    .withColumn("clean_desc",     clean_udf(col("description")))
    .withColumn("combined_text",  concat_ws(" ", col("clean_title"), col("clean_desc")))
    .withColumn("sentiment_score", sent_udf(col("combined_text")))
    .withColumn("sentiment_label", label_udf(col("sentiment_score")))
    .withColumn("view_count",     col("view_count").cast("long"))
    .withColumn("like_count",     col("like_count").cast("long"))
    .withColumn("comment_count",  col("comment_count").cast("long"))
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
    .select("title", "view_count", "like_count", "comment_count",
            "sentiment_score", "sentiment_label", "published_date",
            "channel", "engagement_rate")
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
