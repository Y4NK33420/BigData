# Mid-Term Project Presentation Document

## Project Title
Cross-Platform Trend Intelligence Platform (YouTube + Reddit)

## One-Line Pitch
A Big Data analytics platform that ingests YouTube and Reddit data, processes it through a Medallion architecture, and delivers descriptive, diagnostic, and predictive insights for trend detection and sentiment-aware decision making.

---

## 1. Presentation Objective
This document is designed for your mid-term submission presentation. It combines:
1. The detailed app idea and long-term direction.
2. The current implementation progress already available in this repository.
3. A clear demo narrative for faculty evaluation.

---

## 2. Problem Statement
Organizations and creators often struggle to answer the following in real time:
1. Which topics are rising across platforms (not just one platform)?
2. Is audience sentiment becoming positive or negative over time?
3. Are engagement spikes driven by content release timing or community amplification?
4. Can we predict future engagement trends from early signals?

Existing tools usually provide siloed analytics. This project addresses that by combining YouTube content dynamics with Reddit discussion behavior.

---

## 3. Proposed Solution (App Idea)
We are building a Cross-Platform Trend Intelligence app that:
1. Collects public data from YouTube and Reddit based on user keywords.
2. Converts raw data to analytics-ready datasets using a Medallion pipeline.
3. Computes sentiment, engagement trends, spike diagnostics, and predictive modeling outputs.
4. Serves these outputs via REST APIs to an interactive dashboard.

### Core User Value
1. Unified view of content trends across video and community platforms.
2. Sentiment-aware understanding of topic quality, not just volume.
3. Time-based diagnostics (when spikes happen and where).
4. ML-based predictive layer for engagement estimation.

---

## 4. High-Level Product Vision (Target)
The final app vision is an insight engine with:
1. Trend Radar: detect rising topics early.
2. Narrative Shift Tracking: identify how discussion framing changes.
3. Influence Mapping: connect creators, channels, and subreddits.
4. Alerting: notify users of spike, risk, and opportunity events.
5. Action Recommendations: suggest what to publish, monitor, or investigate.

For mid-term, we already have a strong working pipeline foundation and dashboard analytics module.

---

## 5. Current Repo Progress (Implemented)

## 5.1 Data Ingestion Layer (Bronze)
Implemented in `ingest.py` and `reddit_scrap.py`.

What is done:
1. YouTube ingestion through YouTube Data API v3.
2. Reddit ingestion via public JSON scraping (no OAuth requirement).
3. Keyword-based collection for both platforms.
4. Standardized raw JSON output files in Bronze folders:
5. `/app/data/bronze/youtube/`
6. `/app/data/bronze/reddit/`

Technical highlights:
1. YouTube metadata + statistics capture (views, likes, comments, publish time).
2. Reddit search across sort orders with deduplication.
3. Retry/backoff behavior for transient Reddit HTTP failures.
4. Timestamped raw snapshots for reproducibility.

---

## 5.2 Processing Layer (Silver + Gold)
Implemented in `process.py` using PySpark.

### Bronze -> Silver completed
1. Text cleaning (URL/punctuation/noise normalization).
2. VADER sentiment scoring.
3. Sentiment labeling (positive/neutral/negative).
4. Time feature engineering:
5. YouTube publish date/hour/day-of-week.
6. Reddit created date conversion.
7. Derived metric: engagement rate.
8. Silver Parquet persistence.

### Silver -> Gold completed
Six analytics datasets are generated:
1. Sentiment distribution.
2. YouTube engagement timeline.
3. Reddit engagement timeline.
4. Upload hour vs day spike heatmap source.
5. Top videos table.
6. Top subreddits summary.

Stored under `/app/data/gold/` in keyword-specific tables/files.

---

## 5.3 Predictive Analytics Layer
Also implemented in `process.py`.

What is done:
1. Random Forest regression model on YouTube engagement features.
2. Feature vector includes:
3. like_count
4. comment_count
5. sentiment_score
6. engagement_rate
7. Model metrics generated (RMSE, R2, training sample count).
8. Prediction outputs saved to Gold.
9. Feature importances saved to Gold.

This already provides the project with a valid predictive analytics component beyond descriptive charts.

---

## 5.4 API Layer
Implemented in `api.py` with FastAPI.

Available endpoints:
1. `GET /health`
2. `POST /api/pipeline/run`
3. `GET /api/data?keyword=...`
4. `GET /api/keywords`

What is done:
1. End-to-end pipeline trigger through API.
2. Error/timeout handling for ingestion and Spark processing.
3. Unified analytics payload delivery for frontend.
4. Timeline sorting and parquet-to-JSON transformation.

---

## 5.5 Frontend Layer
Implemented in `frontend/` (React + Vite + Recharts).

What is done:
1. Keyword input and pipeline trigger UI.
2. Pipeline status messages and run history.
3. Dashboard with KPI cards and tabbed analytics.
4. Three analytics sections:
5. Descriptive
6. Diagnostic
7. Predictive

Visual modules implemented:
1. Sentiment distribution chart.
2. Timeline comparison (YouTube vs Reddit).
3. Top videos table.
4. Engagement heatmap.
5. YouTube vs Reddit activity chart.
6. Top subreddits chart.
7. Prediction scatter chart.
8. Feature importance chart.
9. Sentiment vs view-count scatter.

---

## 5.6 Containerization and Deployment
Implemented with Docker.

What is done:
1. `docker-compose.yml` orchestrates backend + frontend services.
2. `Dockerfile.spark` runs FastAPI + PySpark processing service.
3. `Dockerfile.frontend` builds and serves React app via nginx.
4. `nginx.conf` handles SPA routing and API reverse proxy.
5. Shared `data/` volume supports persistent pipeline outputs.

Note for presentation clarity:
1. Streamlit files also exist in repo from earlier iteration (`app.py`, `spark_server.py`, `Dockerfile.streamlit`).
2. Current active deploy path is React + FastAPI + PySpark.

---

## 6. End-to-End Workflow (Current Working Flow)
1. User enters keyword in dashboard sidebar.
2. Frontend calls `POST /api/pipeline/run`.
3. Backend executes:
4. `ingest.py` (collect from YouTube and Reddit to Bronze).
5. `process.py` (Bronze -> Silver -> Gold + ML artifacts).
6. Frontend requests `GET /api/data` for that keyword.
7. Dashboard renders all analytics tabs from Gold outputs.

This demonstrates a complete multi-layer big data application pipeline.

---

## 7. Medallion Data Strategy

### Bronze
Raw JSON snapshots from each source, close to original structure.

### Silver
Cleaned, typed, sentiment-enriched, feature-ready Parquet datasets.

### Gold
Business-facing analytical datasets and ML outputs for fast consumption by APIs and dashboard.

Why this matters academically:
1. Clear separation of concerns.
2. Reproducibility and maintainability.
3. Scalable pattern used in enterprise lakehouse systems.

---

## 8. Mid-Term Deliverables Mapping

### Required Big Data elements already shown
1. Multi-source ingestion: Yes.
2. Data engineering pipeline: Yes.
3. Transformation and feature engineering: Yes.
4. Analytical querying and aggregation: Yes.
5. Visualization dashboard: Yes.
6. Predictive modeling: Yes.
7. Containerized reproducible deployment: Yes.

### Practical completion status
1. Pipeline architecture: Implemented.
2. API integration: Implemented.
3. UI analytics rendering: Implemented.
4. Predictive component baseline: Implemented.
5. Production hardening and advanced intelligence: In progress/future scope.

---

## 9. What To Demo Live (Suggested)
1. Start app via Docker compose.
2. Open dashboard UI.
3. Enter keyword (example: "artificial intelligence").
4. Trigger pipeline run.
5. Show status progression.
6. Show generated analytics:
7. Sentiment distribution.
8. Timeline behavior.
9. Heatmap and subreddit diagnostics.
10. Random Forest predictions and feature importance.
11. Explain Gold artifacts created for the keyword.

If live API limits are a risk, keep at least one precomputed keyword ready for fallback.

---

## 10. Technical Strengths To Highlight During Viva
1. Full-stack integration from ingestion to dashboard.
2. Keyword-based dynamic pipeline execution.
3. Spark-based scalable processing pattern.
4. Structured Medallion design with persisted layers.
5. Combined descriptive + diagnostic + predictive analytics.
6. Clean API boundary between compute and presentation.
7. Containerized setup for reproducibility.

---

## 11. Known Limitations (Honest Assessment)
1. Current ingestion volume is modest and tuned for educational/demo usage.
2. Reddit source uses public scraping (policy and reliability considerations at scale).
3. Advanced entity linking/topic modeling is not yet included.
4. Alerting and near-real-time streaming are not yet implemented.
5. MLOps lifecycle (versioning/retraining automation) is basic at current stage.

Presenting these clearly improves credibility.

---

## 12. Next Milestones (Post Mid-Term)
1. Add scheduler/queue-based asynchronous pipeline execution.
2. Improve topic intelligence (topic clusters and narrative shift detection).
3. Implement alert engine (spike, sentiment risk, breakout opportunity).
4. Add entity resolution (aliases/brand normalization).
5. Add stronger model comparison and drift monitoring.
6. Add role-based multi-user workspace support.

---

## 13. Evaluation Metrics (For Final Assessment)

### Engineering metrics
1. Pipeline success rate.
2. End-to-end runtime per keyword.
3. Data freshness.
4. API response latency.

### Analytics quality metrics
1. Sentiment consistency checks.
2. Forecast RMSE and R2 trends.
3. Topic signal precision (manual validation sample).

### Product utility metrics
1. Time to insight.
2. Dashboard task completion (compare/analyze/extract).
3. User feedback from test reviewers.

---

## 14. 7-10 Minute Presentation Script (Ready to Use)

1. Introduction (45 sec)
"Our project builds a cross-platform big data intelligence system that combines YouTube and Reddit signals for trend and sentiment analytics."

2. Problem and Motivation (60 sec)
"Single-platform analytics misses context. We need a unified system to see what is trending, how people feel, and whether engagement is likely to rise or fall."

3. Architecture (90 sec)
"We use a Medallion pipeline: Bronze raw ingestion, Silver cleaned/enriched data, Gold analytical datasets. FastAPI serves outputs; React dashboard visualizes insights."

4. Current Implementation (120 sec)
"In this repository, we already implemented ingestion scripts, Spark processing, sentiment analysis, six Gold analytics tables, Random Forest predictions, API endpoints, and a multi-tab dashboard."

5. Demo Walkthrough (120 sec)
"I trigger analysis for a keyword, run pipeline, and show descriptive, diagnostic, and predictive charts generated from processed data."

6. Limitations and Improvements (60 sec)
"Current version is a robust prototype. Next steps include advanced topic modeling, alerting, and higher-scale orchestration."

7. Conclusion (30 sec)
"This project demonstrates an end-to-end big data product workflow with practical engineering and analytics depth."

---

## 15. Suggested Slide Deck Structure
1. Title and objective.
2. Problem statement.
3. Proposed app idea and user value.
4. Architecture diagram (YouTube + Reddit -> Bronze/Silver/Gold -> API -> Dashboard).
5. Current implementation in repo (feature checklist).
6. Live/demo screenshots or run flow.
7. Predictive analytics section.
8. Limitations and future roadmap.
9. Conclusion and Q/A.

---

## 16. Appendix: Key Repo Files to Mention
1. `ingest.py` - ingestion entry point.
2. `reddit_scrap.py` - Reddit scraping utilities.
3. `process.py` - Spark transformation + Gold + ML.
4. `api.py` - FastAPI orchestration and data serving.
5. `docker-compose.yml` - service orchestration.
6. `Dockerfile.spark` - backend container.
7. `Dockerfile.frontend` - frontend container.
8. `nginx.conf` - reverse proxy and SPA routing.
9. `frontend/src/App.jsx` - frontend API flow.
10. `frontend/src/components/Dashboard.jsx` - chart orchestration.

---

## Final Summary
This mid-term project already demonstrates a complete and technically meaningful big data system:
1. Data ingestion from two distinct social platforms.
2. Structured Medallion processing pipeline.
3. Sentiment and trend analytics.
4. Predictive modeling outputs.
5. API-driven interactive dashboard.
6. Dockerized reproducible deployment.

The current build is a strong prototype foundation for an advanced final-phase intelligence platform.
