# BigD Analytics Dashboard

BigD Analytics is a full-stack big data analytics project for comparing YouTube and Reddit activity around a search keyword. It ingests social data, processes it through a PySpark medallion pipeline, computes sentiment and predictive metrics, exposes the results through a FastAPI backend, and visualizes them in a React dashboard.

The application is designed to run with Docker Compose:

- React dashboard: `http://localhost:3000`
- FastAPI backend: `http://localhost:5000`
- Swagger API docs: `http://localhost:5000/docs`

## What This Project Does

For a keyword such as `artificial intelligence`, the project can:

1. Collect recent YouTube video metadata and Reddit posts.
2. Store the raw data in the Bronze layer.
3. Clean and normalize the raw records with PySpark.
4. Create Silver layer parquet datasets.
5. Generate Gold layer analytics tables.
6. Run sentiment analysis with VADER.
7. Train and save a Random Forest model for YouTube view prediction.
8. Serve processed metrics through a REST API.
9. Generate video idea recommendations and predict expected views for each idea.
10. Display charts, KPIs, tables, predictions, and recommendations in the frontend.

## Architecture

```text
React Dashboard
localhost:3000
      |
      | /api/*
      v
FastAPI Backend
localhost:5000
      |
      | runs ingestion and processing scripts
      v
Data Pipeline
ingest.py -> process.py
      |
      v
Medallion Storage
data/bronze -> data/silver -> data/gold
```

The frontend is served by nginx in production-style Docker mode. nginx also proxies `/api/*` requests to the backend service inside the Docker network.

## Main Components

### Frontend

Path: `frontend/`

The frontend is a React + Vite application. It provides the user interface for entering a keyword, starting the analysis pipeline, polling pipeline status, and visualizing processed data.

Important files:

- `frontend/src/App.jsx`: top-level app state, API calls, pipeline polling.
- `frontend/src/components/Sidebar.jsx`: keyword input and analysis controls.
- `frontend/src/components/Dashboard.jsx`: KPI layout, chart tabs, recommendation panel.
- `frontend/src/components/charts/`: chart components built with Recharts.
- `frontend/vite.config.js`: local dev server and API proxy configuration.

### Backend API

Path: `backend_api/main.py`

The backend is a FastAPI app. It exposes endpoints for health checks, running the pipeline, checking job status, listing analyzed keywords, loading analytics data, and generating strategy recommendations.

Key responsibilities:

- Accept keyword requests from the frontend.
- Start ingestion and processing jobs in the background.
- Track job status and logs in memory.
- Read Gold layer parquet outputs.
- Return JSON payloads for the dashboard.

### Data Pipeline

Path: `data_pipeline/`

The pipeline has two major stages:

- `ingest.py`: pulls raw data from YouTube and Reddit.
- `process.py`: uses PySpark to clean, transform, aggregate, and model the data.

Supporting files:

- `reddit_scrap.py`: Reddit public JSON scraping helper.
- `static_loader.py`: optional static YouTube dataset loader.
- `recommender.py`: recommendation-related scoring helpers.

### Data Directory

Path: `data/`

This directory stores the medallion pipeline outputs:

- `data/bronze/`: raw JSON data from ingestion.
- `data/silver/`: cleaned parquet datasets.
- `data/gold/`: analytics parquet tables used by the API and dashboard.

The Docker backend mounts this folder into the container at `/app/data`.

## Medallion Pipeline

### Bronze Layer

The Bronze layer stores raw data with minimal changes.

YouTube data is saved under:

```text
data/bronze/youtube/
```

Reddit data is saved under:

```text
data/bronze/reddit/
```

Each run creates keyword-specific JSON files.

### Silver Layer

The Silver layer contains cleaned and normalized parquet outputs. This stage:

- Parses timestamps.
- Cleans text fields.
- Computes sentiment scores.
- Normalizes numeric engagement fields.
- Creates structured Spark DataFrames.

### Gold Layer

The Gold layer contains dashboard-ready analytics tables, including:

- Sentiment distribution by platform.
- YouTube engagement timeline.
- Reddit activity timeline.
- Top videos by view count.
- Top subreddits discussing the topic.
- Upload-hour/day heatmap data.
- Prediction results.
- Feature importance.
- Model metrics.
- Topic viability and content gap outputs.

The API reads these parquet outputs and converts them into JSON for the frontend.

## API Endpoints

### `GET /health`

Returns backend health and active job count.

Example:

```json
{
  "status": "ok",
  "service": "analytics-api",
  "version": "3.0.0",
  "active_jobs": 0
}
```

### `POST /api/pipeline/run`

Starts the ingestion and processing pipeline for a keyword.

Request:

```json
{
  "keyword": "artificial intelligence"
}
```

Response includes a `job_id` and a polling URL.

### `GET /api/pipeline/status/{job_id}`

Returns the current pipeline status, step, logs, and error message if the job failed.

### `GET /api/data?keyword=...`

Loads all Gold layer analytics for a keyword.

### `GET /api/keywords`

Lists keywords with existing Gold layer output.

### `GET /api/prescribe?keyword=...`

Generates three video idea recommendations using Gemini and then scores each idea with the keyword-specific Random Forest model saved by the pipeline.

Each returned idea includes:

- Video title.
- Format.
- Target audience.
- Rationale.
- Distribution strategy.
- Risk warning.
- Predicted views.
- Predicted view range.

This requires `GEMINI_API_KEY` in `.env`. Predicted views require a completed pipeline run for the keyword because the model is saved during `process.py`.

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
YOUTUBE_API_KEY=
GEMINI_API_KEY=
REDDIT_USER_AGENT=BigDataDashboard/1.0 (educational project)
```

`YOUTUBE_API_KEY` is needed for live YouTube ingestion. Without it, YouTube ingestion is skipped. Reddit scraping does not require an API key.

`GEMINI_API_KEY` is optional and only required for the recommendation endpoint.

## Running With Docker Compose

From the project root:

```bash
docker compose up -d --build
```

Then open:

- Dashboard: `http://localhost:3000`
- Backend health: `http://localhost:5000/health`
- Swagger docs: `http://localhost:5000/docs`

Check running services:

```bash
docker compose ps
```

Stop the project:

```bash
docker compose down
```

## Pretraining The Prediction Model

The project supports a global pretrained Random Forest baseline built from 100 famous keywords. This is useful because a single keyword run can produce a small dataset, while the global model learns broader YouTube engagement patterns from many topics.

Run the full pretraining job inside the backend container:

```bash
docker compose exec spark python /app/data_pipeline/pretrain_keywords.py
```

For a smaller test run:

```bash
docker compose exec spark python /app/data_pipeline/pretrain_keywords.py --limit 10
```

To resume without rerunning keywords that already wrote training rows:

```bash
docker compose exec spark python /app/data_pipeline/pretrain_keywords.py --skip-existing
```

Pretraining writes:

- `data/gold/global_training_rows/`: feature rows collected across keywords.
- `data/gold/rf_model_global/`: the global pretrained Random Forest model.

During a normal keyword analysis, `process.py` updates the global training store and trains a keyword-adapted model by combining the pretrained global rows with the current keyword rows repeated at higher weight. This is the Random Forest equivalent of fine-tuning; Spark Random Forest does not support incremental gradient-style fine-tuning of an existing model.

The final video idea recommendations use:

- `rf_model_<keyword>` when the keyword has been analyzed.
- `rf_model_global` as a fallback when a keyword-specific model does not exist yet.

## Running Locally Without Docker

Docker Compose is the recommended path because the backend needs Java and PySpark. If running manually, install the required Python and Node dependencies first.

Backend:

```bash
pip install fastapi uvicorn pyspark pyarrow pandas vaderSentiment google-api-python-client requests
python backend_api/main.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## How a User Analysis Run Works

1. The user enters a keyword in the dashboard.
2. React sends `POST /api/pipeline/run`.
3. FastAPI creates a background job.
4. The backend runs `data_pipeline/ingest.py`.
5. Ingestion writes raw JSON files to `data/bronze`.
6. The backend runs `data_pipeline/process.py`.
7. PySpark reads Bronze files and creates Silver and Gold parquet outputs.
8. React polls `GET /api/pipeline/status/{job_id}`.
9. When the job is done, React calls `GET /api/data`.
10. The Random Forest model is saved under the Gold layer as `rf_model_<keyword>`.
11. The dashboard renders charts and KPI cards from the returned JSON.
12. When recommendations are generated, Gemini creates video ideas and the saved Random Forest model predicts expected views for each idea.

## Docker Notes

This project builds two images:

- `bigdata-spark`: FastAPI, PySpark, Java, and Python dependencies.
- `bigdata-frontend`: React build served by nginx.

The containers are:

- `spark_analytics`: backend on port `5000`.
- `react_dashboard`: frontend on port `3000`.

On Windows with WSL, Docker may use `wslrelay.exe` to forward localhost ports. If ports remain busy after stopping containers, run:

```powershell
wsl --shutdown
```

Then verify:

```powershell
netstat -ano | findstr ":3000 :5000"
```

## Troubleshooting

### Port 3000 or 5000 is already in use

Stop the project:

```bash
docker compose down
```

On Windows/WSL, also try:

```powershell
wsl --shutdown
```

### Dashboard loads but charts are empty

The keyword may not have Gold layer data yet. Run an analysis from the sidebar, then wait for the pipeline to finish.

### YouTube data is missing

Check that `YOUTUBE_API_KEY` is configured in `.env`. Without it, the YouTube ingestion step is skipped.

### Recommendation endpoint fails

Set `GEMINI_API_KEY` in `.env`. The main dashboard can still run without this key.

### Docker reuses an old image

Force a clean rebuild:

```bash
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d
```

## Project Structure

```text
BigData/
├── backend_api/
│   └── main.py
├── data/
│   ├── bronze/
│   ├── silver/
│   └── gold/
├── data_pipeline/
│   ├── ingest.py
│   ├── process.py
│   ├── reddit_scrap.py
│   ├── recommender.py
│   └── static_loader.py
├── docker/
│   ├── Dockerfile.frontend
│   ├── Dockerfile.spark
│   └── nginx.conf
├── frontend/
│   ├── src/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── implementation_plan.md
└── README.md
```

## Current Limitations

- Job state is stored in memory, so job history resets when the backend container restarts.
- YouTube ingestion depends on an external API key and quota.
- Reddit scraping uses public JSON endpoints and may be rate-limited.
- The optional static YouTube dataset is only used if mounted at the expected path.
- Gold layer data must exist before `/api/data` can return meaningful chart data.

## License

MIT
