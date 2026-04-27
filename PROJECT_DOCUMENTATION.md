# Trend Intelligence Platform & BigData Analytics Dashboard

## 1. Project Overview

The BigD Analytics Dashboard is a comprehensive, full-stack big data analytics platform designed to ingest, monitor, and extract multifaceted market intelligence from YouTube and Reddit activity surrounding user-specified keywords. Far more than a simple metric aggregator, this application functions as a predictive video topic generator and trend diagnosis tool. 

The primary business value is guiding content creators and strategists. By analyzing cross-platform momentum, audience sentiment, and predictive algorithmic reach, the platform offers "Action Cards" and mathematically sound strategies on optimal metadata (like video length or upload time) to maximize visibility based on current network thresholds.

## 2. Core System Architecture & Technology Stack

The platform's architecture leverages specialized Big Data solutions engineered to handle semi-structured data pipelines efficiently. It is built on a robust **Medallion Architecture** model (Bronze, Silver, Gold layers) ensuring clean lineage mapping.

### A. Data Streaming & Ingestion
*   **Apache Kafka**: Serves as the high-throughput, low-latency streaming bus for all raw data. As social data API responses (videos, user replies, nested Reddit comments) are ingested, the data loaders broadcast JSON payloads via Kafka topics. Kafka's fault-tolerant event processing is responsible for standardizing the data flow between varying API latencies before laying out the data to the bronze persistent layer.

### B. Scalable Data Processing 
*   **Apache Spark (PySpark)**: Spark acts as the solitary processing engine deployed for high-volume transformations. Our pipeline completely side-steps legacy map-reduce architectures; **Hadoop is not used anywhere in the tech stack**. By relying explicitly on PySpark’s distributed and resilient in-memory DataFrames processing framework, it cleans, aggregates, and transforms the raw payloads from Kafka into normalized datasets, scaling seamlessly across local or orchestrated container fleets.

### C. Persistent Storage Layer
*   **MongoDB**: Since the outputs of Reddit nested dictionaries and YouTube complex statistics vary heavily depending on the endpoints accessed, a NoSQL database provides the most frictionless storage. **MongoDB** is tightly integrated into the final layer of our pipeline. Once Spark outputs the aggregate logic and machine learning predictions, these highly nested JSON-ready profiles (the Gold Layer results) are serialized and persisted into MongoDB clusters holding user queries, aggregated KPIs, and historical analyses for low-latency querying by the backend.

### D. Server Infrastructure & Orchestration
*   **Backend Application**: Powered by **FastAPI** (Python). The stateless REST API is extremely fast and integrates flawlessly with Spark orchestration scripts, handling user queueing, streaming MongoDB data to the clients, and triggering new streaming sessions.
*   **Frontend Dashboard**: A Reactive client interface built with **React** and **Vite** configured with **Recharts** for beautiful, responsive D3-style component charts. 
*   **Containerization**: **Docker** and **Docker Compose** isolate the varying runtimes (Node, Python SDKs, JVM dependencies for Spark), exposing distinct container clusters ensuring environment parity from development to production.

### E. AI, NLP & ML Stack
*   **Sentiment Engine**: Integration with the **VADER NLP engine** tailored specifically for assessing social media slang and emojis, providing accurate sentiment polarity analysis across YouTube comments and Reddit threads.
*   **Spark MLlib Model**: **Random Forest** regression models are dynamically trained and fine-tuned per user topic, learning the mathematical relationship between historical features (like-to-view ratios, comment velocity) to accurately output predicted total-view projections.
*   **Google Gemini LLM**: Serves as the cognitive analyst. Gemini is fed API-derived statistical summaries, competitor gaps, and risk computations. In turn, it writes natural language "Prescriptive Action Cards" matching actionable strategy directly to raw data patterns.

---

## 3. End-to-End Orchestration Workflow

### Phase 1: Trigger & Edge Ingestion
1.  **Initiation**: The user submits a research keyword (e.g., "M1 Mac Review", "Docker Swarm tutorial") to the React frontend.
2.  **API Routing**: FastAPI acknowledges the request and commits an asynchronous task to trace the request.
3.  **Cross-Platform Fetching**: 
    *   *YouTube Data*: Data scrapers interact with YouTube Data v3 APIs to extract broad search aggregations and iteratively drill-down, acquiring individual video metrics, tags, and crucially, thousands of *top comments* via `commentThreads`.
    *   *Reddit Data*: Concurrently scraping overlapping top matching submissions and iterating over the nested comment trees to sample current community sentiment trends over the specified temporal window.
4.  **Kafka Streaming**: As payloads resolve, events are continuously published to active Kafka topics, providing buffering against source rate-limits and allowing non-blocking ingestion routing downward to the Bronze storage.

### Phase 2: PySpark Medallion Transformations
5.  **Bronze Layer**: Raw, unfiltered Kafka JSON event logs are persisted incrementally.
6.  **Silver Layer Processing**: PySpark ingests the new Bronze logs.
    *   Missing timestamps are inferred, timezone normalized.
    *   Text inputs are scrubbed of markdown, HTML strings, and stop-words.
    *   PySpark UDFs invoke VADER to quantify numeric sentiment factors across tens of thousands of scraped comments.
    *   Custom algorithms assess *quality metrics*: standardizing ratios such as `like-to-view_ratio` and formatting arrays grouping engagements by the hour.
7.  **Gold Layer & ML Training**: PySpark compresses the Silver arrays into strict analytical data frames optimized for dashboards. Simultaneously, the framework feeds this context into a keyword-specific Random Forest model. Through historical feature cross-referencing aligned with baseline pretraining arrays, to output future predictions.

### Phase 3: Export & Actionable Serving
8.  **MongoDB Aggregation**: The final analytics arrays, timeline plots, forecasting metadata, and topic dictionaries are stored immutably inside MongoDB collections explicitly tied to the initial Keyword job.
9.  **Frontend Dashboarding**: Following the data propagation, the frontend continuously polls endpoints. Data sourced instantaneously from MongoDB populates charts mapping network densities to platform distributions.
10. **Gemini Prescriptive Step**: Upon finalizing all statistical bounds, the FastAPI layer issues a formatted context window prompt enclosing statistical anomalies and baseline norms explicitly to the Gemini REST API. Gemini replies with robust, format-specific "Idea Generations", which the Random Forest model simultaneously simulates to predict views—closing out the workflow visually to the end user.

---

## 4. The 4-Tier Analytics Dashboard Layers

The core of the React Dashboard interface operates over four progressive pillars of business intelligence, translating complex aggregations smoothly to the user:

### I. Descriptive Analytics *(What is happening?)*
Outlines basic statistical landscape and volume indicators:
*   **Cross-Platform Volume Timeline**: Dual-axis line charts tracking YouTube video publications matched chronologically against Reddit post frequency.
*   **KPI Summary Arrays**: Displaying key indicators like raw accumulated view counts, global like figures, aggregate comment numbers, and average VADER semantic polarity.
*   **Topic Density Maps & Core Subreddits**: Identifies visually the most commonly associated tag terms in a word-cloud array alongside Top-5 Reddit communities most actively debating the specified keyword context.

### II. Diagnostic Analytics *(Why is it happening?)*
Investigative charting aiming to explain metric anomalies:
*   **Time-Series Heatmaps**: Displays complex engagement densities plotted against "Day of the Week" intersecting with "Hour of the Day", surfacing organic traffic patterns.
*   **Quality vs. Reach Coordinates**: Scatters the YouTube *Like/View Ratio* against total lifetime *View Count* helping creators separate low-retention "clickbait" from highly praised localized trends.
*   **Sentiment Lifecycles**: Evaluates overall topic health by correlating positive word combinations directly against the time since video upload.

### III. Predictive Analytics *(What will happen next?)*
Extends current trajectory maps into ML-based outcomes:
*   **Engagement Forecasting**: MLlib generated predictions overlaying potential growth curves (with confidence bounds) spanning the immediate forward weeks.
*   **Feature Importance Drivers**: PySpark outputs explicitly weighting the absolute highest correlation patterns driving algorithmic pickup. (e.g., Does high Reddit sentiment override a low comment volume ratio on YouTube?).

### IV. Prescriptive Analytics *(What action should we take?)*
Directly prescribes strategy to exploit market gaps highlighted by preceding layers:
*   **Competitor Void Treemaps**: An overlay exposing heavy Reddit user interest aligning against shockingly low volume of corresponding YouTube instructional coverage on sub-topics.
*   **Topic Viability Radar Chart**: Scores an idea overall on multiple axes (Velocity, Saturation/Competition, Positive Engagement).
*   **LLM "Next Action" Cards**: Generated specifically via Google Gemini assessing data patterns to recommend clear concepts. *Example Output*: "Launch an exploratory video heavily optimized toward long-form tutorials, capturing traffic routed largely from r/learnpython due to elevated 'how-to' search velocities detected over previous weekends." Each card is paired with an exact estimated View Output from the local regression model.
