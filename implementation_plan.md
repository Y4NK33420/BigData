# Trend Intelligence Platform - Implementation Plan

## Goal Description
Enhance our existing cross-platform analytics app to function as a predictive video topic generator. The core upgrades will focus on capturing advanced YouTube metrics, computing cross-platform viability scores, and generating actionable topic recommendations on the frontend.

> [!NOTE]
> **YouTube Quality Metric:** Instead of using the undocumented dislike count, video quality will be assessed using the **Like-to-View ratio** and **Comment Sentiment Ratio** (derived from fetching top comments for each video).

## Proposed Changes

### 1. Data Ingestion Layer (data_pipeline/)

We need to enhance our data collectors to capture deeper metrics for our recommendation algorithm.

#### [MODIFY] `data_pipeline/ingest.py`
- Update the YouTube fetching logic to include calls to the `commentThreads` endpoint to extract top comments for each video.
- Calculate `like_to_view_ratio`, `comment_to_view_ratio`, and `engagement_velocity` before saving to the Bronze layer.
- Ensure metadata like video tags are thoroughly collected for topic context.

#### [MODIFY] `data_pipeline/reddit_scrap.py`
- Extract overarching subreddit themes for keyword searches.
- Increase comment fetching depth to accurately gauge community sentiment on a topic.

---

### 2. Processing & Algorithm Layer (data_pipeline/)

Here we will engineer the core **Recommendation Engine** combining data from both platforms.

#### [NEW] `data_pipeline/recommender.py`
- Develop an algorithm that grades a topic (e.g., from 0-100) based on:
  - **YouTube Metric:** Growth velocity vs. average views of competing videos.
  - **Engagement Quality:** The YouTube Like-to-View ratio.
  - **YouTube Sentiment:** Sentiment polarity of the scraped YouTube comments.
  - **Reddit Sentiment:** Positive conversation momentum over the last N days.
  - **Saturation Penalty:** A penalty for topics already flooded with too many high-view videos.

#### [MODIFY] `data_pipeline/process.py` (or orchestrator)
- Incorporate the new `recommender.py` logic into the transform flow.
- Output a new Gold dataset: `topic_recommendations_{keyword}.parquet` containing the scores and human-readable "Action Recommendations".

---

### 3. API & Serving Layer (backend_api/)

#### [MODIFY] `backend_api/main.py`
- Update the `GET /api/data` endpoint to read the new `topic_recommendations` Gold datasets.
- **Gemini API Integration:** Add logic to feed aggregated Gold metrics (top videos, sentiment, predictions) into a Gemini Prompt to dynamically generate text for the Prescriptive Action Cards.
- Ensure the JSON returned includes the advanced YouTube analytics metrics (dislike estimations, comment rates) and recommendation signals.

---

### 4. Frontend Layer (frontend/src/)

The dashboard will be mapped directly to the four stages of analytics maturity, featuring heavily expanded visual modules to demonstrate deep analytical capability.

#### 1. Descriptive Analytics Layer *(What is happening?)*
- **Cross-Platform Volume Timeline:** A dual-axis line chart comparing YouTube video uploads against Reddit post frequency over the last 30/60 days.
- **KPI Summary Cards:** Big-number metric cards displaying Total Views, Aggregate Like Count, Reddit Score Volume, and Average Sentiment Polarity.
- **Platform Share Donut Chart:** Visualizing the percentage distribution of discussion (Is this a Reddit-heavy trend or YouTube-heavy trend?).
- **Top Subreddits & Channel Distribution:** Horizontal bar charts highlighting the top 5 arenas where the largest volume of discussion is happening.
- **Topic Density Word Cloud:** A visual cloud clustering the most frequently used terms across video titles, descriptions, and top Reddit posts.
- **Current Sentiment Distribution:** A pie chart showing the Positive/Neutral/Negative split across the aggregated platforms.

#### 2. Diagnostic Analytics Layer *(Why is it happening?)*
- **Engagement Heatmap:** A visual density grid showing when (Day of Week vs. Hour) content historically gets the highest engagement.
- **Quality vs. Reach Scatter Plot:** Plotting YouTube *Like/View Ratio* against *View Count*. This graph identifies "clickbait" (high views, low quality) vs. "hidden gems" (low views, high quality).
- **Sentiment vs. Upload Time Correlation:** A line chart tracking how audience reaction shifts dynamically over the lifecycle of a topic.
- **Video Length vs. Engagement Box Plot:** Diagnosing whether longer video runtimes correlate with higher Like/View ratios for this specific keyword.
- **Comment Sentiment Breakdown:** Visualizing the sentiment of scraped YouTube comments to see if viewers resonated with the video content.
- **Negative Driver Bar Chart:** A breakdown of the top keywords that specifically drive negative sentiment and backlash.

#### 3. Predictive Analytics Layer *(What will happen?)*
- **Engagement Forecast Line Chart:** Combining historical engagement data with Random Forest regression predictions to plot future trajectory (with confidence intervals).
- **Feature Importance Bar Chart:** Visualizing which characteristics (number of likes, reddit buzz, comment count) mathematically drive future algorithmic reach.
- **Sentiment Decay Curve:** A downward-trending line chart predicting roughly when a viral trend will die off based on historical sentiment exhaustion.
- **Anomaly Detection Bubble Chart:** Flagging specific videos/posts that are statistically anomalies and predicting their peak lifespan.
- **Risk vs. Reward Matrix:** A scatter plot predicting the probability of algorithmic suppression (Risk) vs viral growth potential (Reward) based on sentiment thresholds.
- **View-to-Comment Conversion Gauge:** Predicting the future probability that viewers will actively engage rather than passively consume.

#### 4. Prescriptive Analytics Layer *(What should we do?)*
- **Topic Viability Radar Chart:** A multi-axis radar graph evaluating user-inputted topics across "Growth Velocity," "Competition," and "Sentiment."
- **Optimal Target Parameters Plot:** A Parallel Coordinates Plot outputting the mathematically perfect video parameters (e.g. Length + Upload Time + Tag Density).
- **Competitor Void Treemap:** A hierarchical map showing sub-topics that have incredibly high Reddit interest but zero YouTube video tutorials (identifying market gaps).
- **Content Strategy Output Timeline:** A Gantt chart visually prescribing exactly what sub-topics the user should post and exactly when over the next 14 days.
- **Title Optimization Simulator Result:** Horizontal bar charts showing theoretical performance of user-generated titles based on historical keyword click-through data.
- **LLM-Powered Action Cards (Gemini API Integration):** The dashboard will utilize the Gemini API, feeding it the Gold metrics to output natural-language recommendations:
  - *"What to Publish Next:"* (e.g. "Create a tutorial on Topic X; competing videos have high views but terrible comment sentiment.")
  - *"Audiences to Target:"* (e.g. "Cross-post tutorials to r/MachineLearning as Reddit activity correlates tightly with upload spikes.")

## Verification Plan

### Automated Tests
1. Verify the `recommender.py` scoring outputs consistently format numbers correctly and never exceed maximum bounds (0-100).

### Manual Verification
1. Input three known topics into the frontend.
2. Process the pipeline end-to-end to verify that the generated recommendations rationally align with the provided data metrics.
3. Validate that Like/View ratios and comment sentiment scores are visually rendering on the UI without breaking React component state.
