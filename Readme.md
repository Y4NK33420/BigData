# AI Tooling Trend & Sentiment Analyzer

![Status: In Development](https://img.shields.io/badge/Status-In%20Development-blue)
![Purpose: Academic Project](https://img.shields.io/badge/Purpose-Academic%20Project-success)

## 📌 Project Overview
This repository contains the data ingestion, processing, and analytics pipeline for an academic Big Data course project. The primary objective is to analyze the propagation, developer adoption trends, and community sentiment surrounding emerging Artificial Intelligence frameworks (specifically Large Language Models and Autonomous Agents).

By aggregating public discussions across developer-focused communities on Reddit and tutorial ecosystems on YouTube, this project aims to bridge the gap between technical hype and real-world implementation realities.

### Key Objectives
* **Descriptive Analytics:** Identify the most discussed AI architectures, agent frameworks, and memory management techniques over time.
* **Prescriptive Analytics:** Analyze developer sentiment to highlight common implementation bottlenecks, ultimately recommending the most reliable deployment pipelines based on community consensus.

---

## 🏗️ System Architecture

The project relies on a decoupled, batch-processing architecture designed for offline analysis.

1.  **Data Extraction (Ingestion Layer):** * Automated, read-only scripts query the Reddit API (via PRAW) and YouTube Data API v3. 
    * Targets specific technical subreddits (e.g., `r/LocalLLaMA`, `r/dataengineering`) and developer channels.
    * Extracts post text, comment trees, timestamps, and engagement metrics.
2.  **Routing & Storage (Backend Layer):** * Incoming JSON payloads are routed through a **FastAPI** backend for sanitization.
    * Data is stored securely in a **Supabase** (PostgreSQL) database, allowing for robust query capabilities and data relational mapping.
3.  **NLP & Processing (Analytics Layer):** * Offline batch processing of text data for entity extraction and sentiment analysis. 
    * The inference pipeline is optimized to run locally on resource-constrained environments (supporting hardware down to 4GB VRAM GPUs) using quantized models to ensure efficient offline compute.
4.  **Visualization (Presentation Layer):**
    * A **Next.js / React** dashboard surfaces the aggregated insights, rendering time-series graphs of framework popularity and sentiment heatmaps.

---

## ⚙️ Tech Stack

* **Ingestion:** Python 3.10+, PRAW, YouTube Data API
* **Backend Application:** FastAPI
* **Database:** Supabase (PostgreSQL)
* **Frontend Dashboard:** Next.js, React
* **Data Science & NLP:** Pandas, HuggingFace Transformers, PyTorch

---

## 🔒 Data Policy & API Compliance
This application is strictly built for non-commercial, educational research. 
* **Read-Only:** The scripts do not interact with users, post content, or automate user actions.
* **Rate Limiting:** All API calls strictly adhere to platform rate limits to ensure stable, low-impact data retrieval.
* **Privacy:** No personally identifiable information (PII) is stored or analyzed outside of public usernames directly tied to technical inquiries. 

---

## 🚀 Setup & Installation (Local Development)

### Prerequisites
* Python 3.10 or higher
* Node.js and npm (for the frontend dashboard)
* Approved Reddit API Credentials (Client ID & Secret)
* YouTube Data API Key
* Supabase project credentials

### Environment Variables
Create a `.env` file in the root directory and configure the following:
```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=project_name:v1.0 (by /u/yourusername)
YOUTUBE_API_KEY=your_youtube_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
Running the Pipeline
(Detailed execution commands will be updated as the pipeline is finalized).

Bash
# 1. Clone the repository
git clone [https://github.com/yourusername/ai-trend-analyzer.git](https://github.com/yourusername/ai-trend-analyzer.git)

# 2. Install backend dependencies
pip install -r requirements.txt

# 3. Start the FastAPI routing server
uvicorn main:app --reload

# 4. Execute the batch ingestion script
python ingestion/reddit_scraper.py