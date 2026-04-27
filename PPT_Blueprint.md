# PPT Blueprint: BigD Analytics Dashboard

## 1. Title Slide
- **Title:** BigD Analytics Dashboard: Scaling Social Media Intelligence
- **Subtitle:** End-to-End Big Data Pipeline for YouTube & Reddit Analytics
- **Members:** 
  - Yugam (2023aib1020) - PySpark Processing & Medallion Pipeline
  - Vaibhav (2023aib1019) - Data Collection API & MongoDB Integration
  - Shashwat (2023aib1015) - Predictive Modeling Backend
  - Nitin (2023aib1012) - React Dashboard Visualization

---

## 2. Project Identity & Scope
- **The Problem:** Analyzing massive, unstructured social media data across multiple platforms to derive actionable content strategies is computationally heavy and complex.
- **Individual Contributions:**
  - *Data Collection API:* Integrated YouTube Data API and Reddit Web Scraping to gather unstructured JSON feeds.
  - *Spark Processing:* Built a PySpark pipeline implementing a Medallion Architecture (Bronze, Silver, Gold).
  - *Predictive Modeling:* Trained a Random Forest model and integrated Gemini AI for prescriptive content recommendations.
- **Learning Objective:** We applied true big data techniques—distributed processing (Spark), NoSQL storage (MongoDB for raw data), and automated ML pipelines—to extract structured insights from real-world noisy datasets.

---

## 3. System Architecture
- **System Flow Diagram:** 
  - **Data Sources:** YouTube API and Reddit Web Scraping Scripts.
  - **Storage Layer (Bronze):** MongoDB acts as the landing zone for unstructured raw JSON.
  - **Processing Core (Silver/Gold):** Apache Spark (PySpark) handles distributed batch processing, feature extraction, and Medallion architecture formatting.
  - **Predictive Engine:** Random Forest Machine Learning Model + Gemini AI.
  - **Frontend Interface:** React.js Data Visualization Dashboard (Recharts).
- **Deployment:** Managed via Docker Compose for seamless scalability and orchestration.

---

## 4. The Big Data Pipeline (40% Weightage)
- **Data Collection (5%):** Used the YouTube API to fetch video metadata and a custom web scraping script to anonymously extract Reddit JSON data, bypassing strict rate limits.
- **Data Storage (15%):** **MongoDB (NoSQL)** was used to land the raw, unstructured JSON data. MongoDB's document-oriented architecture provided flexible, schema-less storage, allowing us to seamlessly accommodate varying data structures from YouTube and Reddit.
- **Data Processing (20%):** We utilized **Apache Spark (PySpark)** to process the data in Hadoop-like distributed nodes. PySpark reads the data, cleans text, computes VADER sentiment scores, normalizes engagement metrics, and transforms the raw records into highly optimized Parquet files across Silver and Gold layers.
- **Pipeline Flow Diagram:**
  ```text
  Input (YouTube/Reddit APIs) 
       ↓ 
  Storage (MongoDB - Raw JSON) 
       ↓ 
  Processing (PySpark Processing & Cleaning) 
       ↓ 
  Output (Gold Layer Parquet -> FastAPI -> React Dashboard)
  ```

---

## 5. Descriptive Analytics (30% Weightage)
- **Analytical Question:** *"What is the current sentiment and engagement trend for our target topic?"*
- **Visualization:** Platform Share Chart, Engagement Timeline Chart, and Sentiment Distribution. 
- **Insight:** The initial analysis maps out exactly how much volume a topic generates, revealing that Reddit often acts as a fast-moving discussion forum while YouTube provides sustained views. Both platforms exhibit distinct sentiment polarities.
- **Example Descriptor:**
  - **Task:** Cross-platform topic analysis.
  - **Picture:** [Insert screenshot of the 'Platform Share' or 'Timeline' dashboard tab here]

---

## 6. Diagnostic Analytics (20% Weightage)
- **Analytical Question:** *"Why are certain posts/videos gaining more traction?"*
- **Visualization:** Heatmap of Upload Days & Hours, and a Feature Importance Bar Chart.
- **Interactivity:** The dashboard allows users to dynamically explore the heatmap via hover tooltips, discovering the specific time slots that historically yield the highest density of engagement. Feature importance helps users see *why* a video succeeds (e.g., view count is highly correlated with specific engagement metrics).

---

## 7. Predictive & Prescriptive Insights (10% Weightage)
- **Predictive (5% - What will happen?):** Our embedded **Random Forest** machine learning model mathematically predicts the expected view range (e.g., 50k - 100k views) for any proposed video idea based on historical dataset trends.
- **Prescriptive (5% - What should be done?):** The system integrates **Gemini AI** to prescribe specific actions. It tells the user "Create this specific video title, with this format, for this target audience" to maximize success.
- **Interactivity Feature:** Users can click the "Generate Strategy" button on the UI, which fetches real-time predictive scorings and actionable steps dynamically.

---

## 8. Dashboard Features & Design Principles
- **Interactive Elements:** Keyword input trigger, dynamic filters via tabs, Recharts-based interactive graphs with hover tooltips, and real-time backend pipeline polling.
- **Design Standards:** Maintained clarity and simplicity through a clean, dark-mode React interface. Used clear, distinct KPI cards at the top of the interface so executives can digest numbers instantly.
- **UX Goal:** Enable users with zero programming knowledge to trigger a massive Spark-based data pipeline and explore deep insights intuitively. 

---

## 9. Methodology & Key Findings
- **Methodology:** An end-to-end data pipeline moving from scalable ingestion (API + Web Scraping) → Flexible Storage (MongoDB) → Distributed Cleaning (PySpark) → Advanced Output (Machine Learning + React Dashboard).
- **Analytics Explanation:** We successfully transitioned from *Descriptive* (what are users talking about?) to *Diagnostic* (when and why is it popular?) and ultimately to *Prescriptive* (what content should we create next to get views?).
- **Key Findings:**
  1. **Upload Timing is Critical:** The heatmap undeniably proves that specific time windows drastically increase the probability of a video's success.
  2. **Sentiment Bias:** The data pipeline revealed strong sentiment differences between YouTube's general audience and Reddit's niche communities.
  3. **Data-Driven Creativity:** Using a Random Forest model on historical Big Data allows us to prescribe highly accurate view estimates for entirely new, AI-generated content concepts.
