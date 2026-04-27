# BigD Analytics Dashboard

<div align="center">

![BigD Analytics](https://img.shields.io/badge/BigD-Analytics-6366f1?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi0yaDJ2MnptMC00aC0yVjdoMnY2eiIvPjwvc3ZnPg==)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PySpark](https://img.shields.io/badge/PySpark-3.x-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**A full-stack Big Data analytics platform that ingests YouTube + Reddit data, processes it through a PySpark Medallion architecture, performs sentiment analysis & predictive modelling, and serves results through a modern React dashboard.**

</div>

---

## 📸 Features

- 🎬 **YouTube API ingestion** — videos, stats, engagement metrics
- 💬 **Reddit web scraping** — no API key required, polite rate-limiting
- 🥉🥈🥇 **Medallion Architecture** — Bronze → Silver → Gold via PySpark
- 🧠 **VADER Sentiment Analysis** — per-video and per-post sentiment scoring
- 🤖 **Random Forest ML** — view count predictions with feature importance
- ⚡ **FastAPI backend** — REST endpoints with Swagger docs
- 🎨 **React + Recharts frontend** — 7 interactive charts, KPI cards, dark theme
- 🐳 **Docker Compose** — one-command deployment

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND  (port 3000)               │
│         Recharts · KPI Cards · 3-tab Dashboard              │
└─────────────────────────┬────────────────────────────────────┘
                          │ nginx reverse proxy /api/*
┌─────────────────────────▼────────────────────────────────────┐
│                   FASTAPI BACKEND  (port 5000)               │
│        /api/pipeline/run  ·  /api/data  ·  /api/keywords    │
│                    Swagger UI at /docs                       │
└──────┬───────────────────────────────────────────────────────┘
       │ subprocess
       ▼
┌──────────────────────────────────────────────────────────────┐
│               PYSPARK MEDALLION PIPELINE                     │
│                                                              │
│  ingest.py ──► Bronze (raw JSON)                            │
│      │                                                       │
│  process.py ──► Silver (cleaned Parquet)                    │
│                 └──► Gold (analytics Parquet tables)        │
│                       └──► Random Forest predictions        │
└──────────────────────────────────────────────────────────────┘
       ▲              ▲
  YouTube API    Reddit Scraper
  (API key)     (public JSON endpoints,
                 no auth required)
```

### Data Sources

| Source | Method | Auth |
|---|---|---|
| YouTube | Google API v3 | API key |
| Reddit | Public JSON (`/r/<sub>.json`) | None |

### Gold Layer Tables

| Table | Contents |
|---|---|
| `sentiment_{kw}` | Sentiment distribution per platform |
| `yt_timeline_{kw}` | YouTube views/likes over time |
| `reddit_timeline_{kw}` | Reddit score/post count over time |
| `yt_spikes_{kw}` | Avg views by upload hour × day of week |
| `top_videos_{kw}` | Top 20 videos by view count |
| `subreddits_{kw}` | Top subreddits discussing the keyword |
| `predictions_{kw}.parquet` | Random Forest view count predictions |
| `feature_importance_{kw}.parquet` | RF feature importances |
| `model_metrics_{kw}.parquet` | RMSE, R², training sample count |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose v2
- A YouTube Data API v3 key ([get one here](https://console.cloud.google.com/))

### 1. Clone the repository

```bash
git clone https://github.com/Y4NK33420/BigData.git
cd BigData
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your YouTube API key:
#   YOUTUBE_API_KEY=AIza...
```

### 3. Build & run

```bash
docker compose build
docker compose up -d
```

### 4. Open the dashboard

| Service | URL |
|---|---|
| 🎨 React Dashboard | http://localhost:3000 |
| ⚡ FastAPI Swagger | http://localhost:5000/docs |
| 🔌 Health Check | http://localhost:5000/health |

Enter a keyword (e.g. `artificial intelligence`) in the sidebar and click **Run Analysis**.

---

## 📁 Project Structure

```
BigData/
├── api.py                    # FastAPI backend (pipeline trigger + data endpoints)
├── ingest.py                 # Data ingestion (YouTube API + Reddit scraper)
├── process.py                # PySpark Medallion pipeline + Random Forest ML
├── reddit_scrap.py           # Custom Reddit web scraper (no auth needed)
│
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx           # Root component (state, API calls)
│   │   ├── index.css         # Global dark theme styles
│   │   ├── components/
│   │   │   ├── Sidebar.jsx   # Keyword input, run button, history
│   │   │   ├── Dashboard.jsx # KPI cards + tab layout
│   │   │   ├── Welcome.jsx   # Empty state
│   │   │   └── charts/
│   │   │       ├── SentimentChart.jsx    # Donut + grouped bar
│   │   │       ├── TimelineChart.jsx     # Dual-series area + line
│   │   │       ├── TopVideosTable.jsx    # Ranked video table
│   │   │       ├── HeatmapChart.jsx      # Upload hour × day heatmap
│   │   │       ├── YTvsReddit.jsx        # Bar + line combo (dual axis)
│   │   │       ├── SubredditsChart.jsx   # Horizontal sentiment bars
│   │   │       ├── PredictionChart.jsx   # Actual vs predicted scatter
│   │   │       ├── FeatureImport.jsx     # RF feature importance bars
│   │   │       └── SentimentScatter.jsx  # Sentiment vs views bubbles
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── data/                     # Medallion data (git-ignored, created at runtime)
│   ├── bronze/               # Raw JSON from ingestion
│   │   ├── youtube/
│   │   └── reddit/
│   ├── silver/               # Cleaned Parquet (PySpark output)
│   └── gold/                 # Analytics tables + ML results
│
├── Dockerfile.spark          # FastAPI + PySpark container
├── Dockerfile.frontend       # Node build → nginx serve (multi-stage)
├── nginx.conf                # SPA routing + /api/ reverse proxy
├── docker-compose.yml        # Orchestrates spark + frontend services
├── .env.example              # Environment variable template
└── README.md
```

---

## 🔌 API Reference

### `POST /api/pipeline/run`

Trigger the full ingestion + processing pipeline.

```json
// Request body
{ "keyword": "artificial intelligence" }

// Response
{ "status": "success", "keyword": "artificial intelligence", "message": "..." }
```

### `GET /api/data?keyword=artificial+intelligence`

Fetch all gold-layer analytics data for a keyword.

Returns: `sentiment`, `yt_timeline`, `rd_timeline`, `spikes`, `top_videos`, `subreddits`, `predictions`, `feat_import`, `model_metrics`

### `GET /api/keywords`

List all keywords with existing gold-layer data.

### `GET /health`

Docker healthcheck endpoint.

> Full interactive docs available at **http://localhost:5000/docs** (Swagger UI)

---

## 🛠️ Development

### Running locally without Docker

**Backend (FastAPI):**
```bash
pip install fastapi uvicorn pyarrow pandas vaderSentiment google-api-python-client requests
cp .env.example .env  # add your API key
python api.py
```

**Frontend (React):**
```bash
cd frontend
npm install
VITE_API_URL=http://localhost:5000 npm run dev
```

### Rebuilding after code changes

| Change | Required action |
|---|---|
| `api.py`, `ingest.py`, `process.py`, `reddit_scrap.py` | Auto-reloaded via volume mount (no restart) |
| `frontend/src/**` | Requires `docker compose build frontend && docker compose up -d frontend` |
| `Dockerfile.spark` or `Dockerfile.frontend` | Requires full `docker compose build --no-cache` |

---

## 📊 Dashboard Tabs

### 📊 Descriptive
- **Sentiment Distribution** — Donut chart (overall) + grouped bar (by platform)
- **Engagement Over Time** — Dual-series area + line (YouTube views vs Reddit score)
- **Top Videos by View Count** — Ranked table with sentiment badges

### 🔬 Diagnostic
- **Engagement Spike Heatmap** — Grid heatmap of avg views by upload hour × day of week
- **YouTube Releases vs Reddit Discussions** — Bar + line combo with dual Y axes
- **Top Subreddits** — Horizontal bars colored by average sentiment

### 🤖 Predictive
- **Model Metrics** — Algorithm, RMSE, R², training samples
- **Actual vs Predicted Views** — Scatter chart (color = sentiment)
- **Feature Importance** — Random Forest feature importance ranking
- **Sentiment vs View Count** — Bubble chart (size = likes)

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
