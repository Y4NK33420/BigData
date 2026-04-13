#!/usr/bin/env python3
"""
app.py  —  Social Media Analytics Dashboard
─────────────────────────────────────────────
Streamlit UI that:
  1. Accepts a keyword search
  2. Triggers the PySpark pipeline via the Spark container REST API
  3. Reads Gold-layer Parquet files and renders 5 interactive visualisations

Analytics tabs:
  📊 Descriptive  — Sentiment distribution | Engagement timeline | Top videos
  🔍 Diagnostic   — Engagement heatmap     | YouTube release vs Reddit peak
  🔮 Predictive   — Actual vs predicted views | Feature importance | Trend scatter
"""

import os
import time
import requests
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page Config  (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Social Media Analytics | BigD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — Dark Premium Theme
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Base ── */
*, *::before, *::after { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

.stApp {
    background: radial-gradient(ellipse at 0% 0%, #0f0c29 0%, #302b63 50%, #0a0a1a 100%);
    min-height: 100vh;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(5, 5, 20, 0.85) !important;
    border-right: 1px solid rgba(255,255,255,0.07) !important;
    backdrop-filter: blur(20px);
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }

/* ── Text inputs ── */
.stTextInput input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(99,102,241,0.4) !important;
    border-radius: 10px !important;
    color: white !important;
    font-size: 1rem !important;
}
.stTextInput input:focus {
    border-color: rgba(99,102,241,0.9) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
}

/* ── Sliders ── */
[data-testid="stSlider"] * { color: rgba(255,255,255,0.8) !important; }
.stSlider [data-baseweb="slider"] { padding: 0 !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    width: 100% !important;
    transition: all 0.25s ease !important;
    letter-spacing: 0.3px;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 30px rgba(99,102,241,0.45) !important;
}
.stButton > button:active { transform: translateY(0px) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 14px !important;
    padding: 5px !important;
    gap: 4px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    color: rgba(255,255,255,0.5) !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    font-weight: 600 !important;
}

/* ── DataFrames ── */
.stDataFrame { border-radius: 12px !important; overflow: hidden; }
[data-testid="stDataFrame"] { background: rgba(255,255,255,0.03) !important; }

/* ── Headings / text ── */
h1, h2, h3, h4, h5 { color: white !important; }
p, li, label, span   { color: rgba(255,255,255,0.8) !important; }
.stMarkdown p        { color: rgba(255,255,255,0.75) !important; }

/* ── Status widgets ── */
[data-testid="stStatusWidget"] { background: rgba(255,255,255,0.05) !important; border-radius: 12px !important; }

/* ── Metric card (custom HTML) ── */
.metric-card {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 22px 18px;
    text-align: center;
    transition: border-color 0.3s, box-shadow 0.3s;
    height: 130px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.metric-card:hover {
    border-color: rgba(99,102,241,0.5);
    box-shadow: 0 0 28px rgba(99,102,241,0.18);
}
.metric-icon  { font-size: 1.6rem; line-height: 1; }
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    background: linear-gradient(135deg, #a78bfa, #6366f1);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
}
.metric-label {
    font-size: 0.72rem;
    color: rgba(255,255,255,0.45) !important;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* ── Section headers ── */
.section-hdr {
    font-size: 1.05rem;
    font-weight: 600;
    color: white !important;
    margin: 22px 0 10px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid rgba(99,102,241,0.3);
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── Pipeline card ── */
.pipeline-card {
    background: rgba(99,102,241,0.08);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 14px;
    margin-top: 16px;
    font-size: 0.8rem;
    color: rgba(255,255,255,0.6) !important;
    line-height: 1.8;
}

/* ── Welcome screen ── */
.welcome-wrap {
    text-align: center;
    padding: 60px 20px;
}
.welcome-pipeline {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 40px;
}
.pipeline-node {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 18px 22px;
    min-width: 130px;
    text-align: center;
    transition: border-color 0.3s;
}
.pipeline-node:hover { border-color: rgba(99,102,241,0.4); }
.pipeline-arrow { font-size: 1.3rem; color: rgba(99,102,241,0.7); }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Config & Paths
# ─────────────────────────────────────────────────────────────────────────────

SPARK_URL  = os.environ.get("SPARK_SERVER_URL", "http://spark:5000")
GOLD_PATH  = "/app/data"     # charts read from /app/data/gold/...
GOLD_DIR   = "/app/data/gold"


# ── Plotly theme ──────────────────────────────────────────────────────────────
_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.025)",
    font=dict(color="rgba(255,255,255,0.8)", family="Inter"),
    title_font=dict(color="white", size=15, family="Inter"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.08)"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor="rgba(255,255,255,0.08)", zeroline=False),
    margin=dict(t=50, b=30, l=30, r=30),
)
DAY_MAP = {1:"Sun",2:"Mon",3:"Tue",4:"Wed",5:"Thu",6:"Fri",7:"Sat"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def gold_paths(kw: str) -> dict:
    k = kw.replace(" ", "_").lower()
    return {
        "sentiment":         f"{GOLD_DIR}/sentiment_{k}",
        "yt_timeline":       f"{GOLD_DIR}/yt_timeline_{k}",
        "reddit_timeline":   f"{GOLD_DIR}/reddit_timeline_{k}",
        "yt_spikes":         f"{GOLD_DIR}/yt_spikes_{k}",
        "top_videos":        f"{GOLD_DIR}/top_videos_{k}",
        "subreddits":        f"{GOLD_DIR}/subreddits_{k}",
        "predictions":       f"{GOLD_DIR}/predictions_{k}.parquet",
        "feat_importance":   f"{GOLD_DIR}/feature_importance_{k}.parquet",
        "model_metrics":     f"{GOLD_DIR}/model_metrics_{k}.parquet",
    }


def pq(path: str) -> pd.DataFrame | None:
    """Safely load a Parquet file or directory."""
    try:
        if os.path.isdir(path):
            return pd.read_parquet(path)
        if os.path.isfile(path):
            return pd.read_parquet(path)
    except Exception:
        pass
    return None


def data_ready(kw: str) -> bool:
    paths = gold_paths(kw)
    return (
        os.path.exists(paths["top_videos"])
        or os.path.exists(paths["sentiment"])
    )


def fmt_num(n) -> str:
    try:
        n = float(n)
        if n >= 1_000_000: return f"{n/1e6:.1f}M"
        if n >= 1_000:     return f"{n/1e3:.1f}K"
        return f"{n:.0f}"
    except Exception:
        return str(n)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:24px 0 8px;'>
        <div style='font-size:2.8rem;'>📊</div>
        <div style='font-size:1.15rem; font-weight:700; color:white; margin-top:6px;'>BigD Analytics</div>
        <div style='font-size:0.75rem; color:rgba(255,255,255,0.4); margin-top:2px;'>Social Media Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    keyword = st.text_input(
        "🔍 Keyword",
        value="technology",
        placeholder="e.g. AI, Bitcoin, Climate …",
        key="kw",
    )

    st.markdown("**⚙️ Filters**")
    min_likes  = st.slider("Min YouTube Likes",  0, 20_000, 0, 500)
    min_reddit = st.slider("Min Reddit Score",   0, 5_000,  0, 50)

    st.divider()
    analyze_btn = st.button("🚀 Run Analysis", key="analyze_btn", use_container_width=True)

    st.markdown("""
    <div class='pipeline-card'>
        <b style='color:#a78bfa;'>Medallion Architecture</b><br>
        🥉 <b>Bronze</b> — Raw JSON (YouTube + Reddit)<br>
        🥈 <b>Silver</b> — Cleaned Parquet + VADER<br>
        🥇 <b>Gold</b>   — Analytics + RF Predictions
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Hero Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='text-align:center; padding:36px 0 20px;'>
    <h1 style='
        font-size: clamp(2rem, 5vw, 3.2rem);
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0; line-height: 1.15;
    '>Social Media Analytics</h1>
    <p style='color:rgba(255,255,255,0.45); font-size:1rem; margin-top:8px;'>
        YouTube × Reddit Intelligence  ·  Powered by PySpark
    </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Trigger
# ─────────────────────────────────────────────────────────────────────────────

if analyze_btn and keyword.strip():
    st.markdown("---")
    c1, c2, c3 = st.columns(3)

    with c1:
        with st.status("📥 Ingesting Data …", expanded=True) as s1:
            st.write("🎬 Querying YouTube API …")
            st.write("💬 Querying Reddit API …")
            try:
                resp = requests.post(
                    f"{SPARK_URL}/pipeline",
                    params={"keyword": keyword.strip()},
                    timeout=400,
                )
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot reach the Spark container. Is `docker compose up` running?")
                st.stop()
            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. Try a more specific keyword.")
                st.stop()

            if resp.status_code != 200:
                err = resp.json().get("error", resp.text)
                st.error(f"❌ Pipeline error: {err}")
                s1.update(label="📥 Ingestion Failed ✗", state="error")
                st.stop()
            else:
                s1.update(label="📥 Data Ingested ✓", state="complete")

    with c2:
        with st.status("⚙️ Spark Processing …", expanded=True) as s2:
            st.write("🥉 Bronze → reading raw JSON …")
            st.write("🥈 Silver → cleaning + VADER …")
            st.write("🥇 Gold  → aggregating tables …")
            time.sleep(0.5)
            s2.update(label="⚙️ Processing Complete ✓", state="complete")

    with c3:
        with st.status("📊 Building Dashboard …", expanded=True) as s3:
            st.write("🤖 Random Forest model …")
            st.write("📈 Rendering charts …")
            time.sleep(0.5)
            s3.update(label="📊 Dashboard Ready ✓", state="complete")

    st.success("✅ Analysis complete! See charts below.")
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Main Dashboard
# ─────────────────────────────────────────────────────────────────────────────

if data_ready(keyword.strip()):
    paths  = gold_paths(keyword.strip())

    # Load all Gold tables
    sent_df   = pq(paths["sentiment"])
    yt_tl     = pq(paths["yt_timeline"])
    rd_tl     = pq(paths["reddit_timeline"])
    spikes_df = pq(paths["yt_spikes"])
    top_df    = pq(paths["top_videos"])
    subs_df   = pq(paths["subreddits"])
    pred_df   = pq(paths["predictions"])
    feat_df   = pq(paths["feat_importance"])
    metrics   = pq(paths["model_metrics"])

    # Apply sidebar filters
    if top_df  is not None and min_likes  > 0:
        top_df  = top_df[top_df["like_count"]  >= min_likes]
    if subs_df is not None and min_reddit > 0:
        subs_df = subs_df[subs_df["avg_score"] >= min_reddit]

    # ── KPI Metrics ──────────────────────────────────────────────────────────
    st.markdown("---")

    total_videos = len(top_df)    if top_df  is not None else 0
    total_posts  = int(subs_df["post_count"].sum()) if subs_df is not None and len(subs_df) else 0
    avg_sent     = float(sent_df["avg_score"].mean()) if sent_df is not None else 0.0
    top_sub      = subs_df.iloc[0]["subreddit"] if subs_df is not None and len(subs_df) else "N/A"
    total_views  = fmt_num(top_df["view_count"].sum()) if top_df is not None and len(top_df) else "0"
    r2_score     = f"{metrics.iloc[0]['r2']:.3f}" if metrics is not None and len(metrics) else "N/A"

    kpi_html = ""
    for icon, value, label in [
        ("🎬", str(total_videos), "Videos Analysed"),
        ("💬", fmt_num(total_posts), "Reddit Posts"),
        ("🧠", f"{avg_sent:+.3f}", "Avg Sentiment"),
        ("🏆", f"r/{top_sub}", "Top Subreddit"),
        ("👁️", total_views, "Total Views"),
        ("🤖", r2_score, "RF Model R²"),
    ]:
        kpi_html += f"""
        <div class='metric-card'>
            <div class='metric-icon'>{icon}</div>
            <div class='metric-value'>{value}</div>
            <div class='metric-label'>{label}</div>
        </div>"""

    st.markdown(
        f"<div style='display:grid; grid-template-columns:repeat(6,1fr); gap:12px;'>{kpi_html}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Keyword badge ─────────────────────────────────────────────────────────
    st.markdown(
        f"<p style='text-align:center; color:rgba(255,255,255,0.4); font-size:0.85rem;'>"
        f"Showing results for &nbsp;"
        f"<span style='background:rgba(99,102,241,0.2); border:1px solid rgba(99,102,241,0.4); "
        f"padding:3px 12px; border-radius:20px; color:#a78bfa; font-weight:600;'>"
        f"🔍 {keyword}</span></p>",
        unsafe_allow_html=True,
    )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📊  Descriptive Analytics",
        "🔍  Diagnostic Analytics",
        "🔮  Predictive Analytics",
    ])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1 — DESCRIPTIVE
    # ═════════════════════════════════════════════════════════════════════════
    with tab1:

        # ── Chart 1a: Sentiment Distribution ─────────────────────────────────
        st.markdown("<div class='section-hdr'>💡 Sentiment Distribution</div>", unsafe_allow_html=True)
        try:
            if sent_df is not None and len(sent_df):
                col_a, col_b = st.columns(2)
                SENT_COLORS = {
                    "positive": "#22c55e",
                    "negative": "#ef4444",
                    "neutral":  "#fbbf24",
                }

                with col_a:
                    # Donut by source (combined)
                    combined = (
                        sent_df.groupby("sentiment_label", as_index=False)
                        .agg(count=("count", "sum"), avg_score=("avg_score", "mean"))
                    )
                    fig = px.pie(
                        combined,
                        names="sentiment_label",
                        values="count",
                        color="sentiment_label",
                        color_discrete_map=SENT_COLORS,
                        hole=0.62,
                        title="Overall Sentiment (YouTube + Reddit)",
                    )
                    fig.update_traces(textposition="outside", textinfo="percent+label")
                    fig.update_layout(**_LAYOUT)
                    st.plotly_chart(fig, use_container_width=True)

                with col_b:
                    # Grouped bar: YouTube vs Reddit
                    fig = px.bar(
                        sent_df,
                        x="sentiment_label",
                        y="count",
                        color="source",
                        barmode="group",
                        color_discrete_map={"YouTube": "#6366f1", "Reddit": "#f97316"},
                        title="Sentiment Count by Platform",
                        labels={"count": "Posts / Videos", "sentiment_label": "Sentiment"},
                    )
                    fig.update_layout(**_LAYOUT)
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as _e:
            st.error(f"❌ [Chart 1a – Sentiment Distribution] {type(_e).__name__}: {_e}")
            st.exception(_e)

        # ── Chart 1b: Engagement Timeline ────────────────────────────────────
        st.markdown("<div class='section-hdr'>📈 Engagement Over Time</div>", unsafe_allow_html=True)
        try:
            if yt_tl is not None and len(yt_tl):
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Scatter(
                    x=yt_tl["published_date"].astype(str), y=yt_tl["total_views"],
                    name="YouTube Views", mode="lines+markers",
                    line=dict(color="#6366f1", width=2.5),
                    fill="tozeroy", fillcolor="rgba(99,102,241,0.1)",
                    marker=dict(size=6),
                ), secondary_y=False)
                if rd_tl is not None and len(rd_tl):
                    fig.add_trace(go.Scatter(
                        x=rd_tl["created_date"].astype(str), y=rd_tl["total_score"],
                        name="Reddit Score", mode="lines+markers",
                        line=dict(color="#f97316", width=2.5),
                        fill="tozeroy", fillcolor="rgba(249,115,22,0.08)",
                        marker=dict(size=6),
                    ), secondary_y=True)
                fig.update_layout(
                    **_LAYOUT,
                    title="YouTube Views & Reddit Activity Over Time",
                    hovermode="x unified",
                    height=360,
                )
                fig.update_yaxes(title_text="YouTube Views",
                                 title_font=dict(color="#6366f1"),
                                 gridcolor="rgba(255,255,255,0.05)",
                                 secondary_y=False)
                fig.update_yaxes(title_text="Reddit Score",
                                 title_font=dict(color="#f97316"),
                                 gridcolor="rgba(255,255,255,0)",
                                 secondary_y=True)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as _e:
            st.error(f"❌ [Chart 1b – Engagement Timeline] {type(_e).__name__}: {_e}")
            st.exception(_e)

        # ── Table: Top Videos ─────────────────────────────────────────────────
        st.markdown("<div class='section-hdr'>🏅 Top Videos by View Count</div>", unsafe_allow_html=True)
        try:
            if top_df is not None and len(top_df):
                disp = top_df[[
                    "title", "view_count", "like_count", "comment_count",
                    "sentiment_label", "channel",
                ]].copy()
                disp["title"] = disp["title"].str[:60].str.rstrip() + "…"
                disp.columns  = ["Title", "Views", "Likes", "Comments", "Sentiment", "Channel"]
                disp.index    = range(1, len(disp) + 1)

                st.dataframe(
                    disp.style.background_gradient(subset=["Views"], cmap="Purples"),
                    use_container_width=True, height=320,
                )
        except Exception as _e:
            st.error(f"❌ [Table – Top Videos] {type(_e).__name__}: {_e}")
            st.exception(_e)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2 — DIAGNOSTIC
    # ═════════════════════════════════════════════════════════════════════════
    with tab2:

        # ── Chart 2a: Engagement Spike Heatmap ───────────────────────────────
        st.markdown("<div class='section-hdr'>🔥 Engagement Spike Heatmap (Hour × Day)</div>", unsafe_allow_html=True)
        try:
            if spikes_df is not None and len(spikes_df):
                spikes_df["day_name"] = spikes_df["day_of_week"].map(DAY_MAP)
                pivot = (
                    spikes_df.pivot_table(
                        values="avg_views",
                        index="day_name",
                        columns="upload_hour",
                        aggfunc="mean",
                    )
                    .fillna(0)
                    .reindex(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
                )
                fig = go.Figure(go.Heatmap(
                    z=pivot.values,
                    x=[f"{h:02d}:00" for h in range(24)],
                    y=list(pivot.index),
                    colorscale=[[0,"#0f0c29"],[0.35,"#6366f1"],[0.7,"#8b5cf6"],[1,"#e879f9"]],
                    hoverongaps=False,
                    colorbar=dict(title="Avg Views", titlefont=dict(color="rgba(255,255,255,0.7)")),
                    hovertemplate="Day: %{y}<br>Hour: %{x}<br>Avg Views: %{z:,.0f}<extra></extra>",
                ))
                fig.update_layout(
                    **_LAYOUT,
                    title="Avg Video Views by Upload Hour & Day of Week (UTC)",
                    xaxis_title="Hour of Day (UTC)",
                    yaxis_title="Day of Week",
                    height=380,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Heatmap requires more videos — try a broader keyword.")
        except Exception as _e:
            st.error(f"❌ [Chart 2a – Heatmap] {type(_e).__name__}: {_e}")
            st.exception(_e)

        # ── Chart 2b: YouTube Release vs Reddit Discussion Peak ───────────────
        st.markdown(
            "<div class='section-hdr'>🔗 YouTube Releases vs Reddit Discussion Peaks</div>",
            unsafe_allow_html=True,
        )
        col_a, col_b = st.columns([3, 2])

        with col_a:
            try:
                if yt_tl is not None and len(yt_tl) and rd_tl is not None and len(rd_tl):
                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Bar(
                        x=yt_tl["published_date"].astype(str),
                        y=yt_tl["video_count"],
                        name="YouTube Uploads",
                        marker_color="rgba(99,102,241,0.75)",
                        marker_line=dict(width=0),
                    ), secondary_y=False)
                    fig.add_trace(go.Scatter(
                        x=rd_tl["created_date"].astype(str),
                        y=rd_tl["post_count"],
                        name="Reddit Discussions",
                        mode="lines+markers",
                        line=dict(color="#f97316", width=2.5),
                        marker=dict(size=7),
                    ), secondary_y=True)
                    fig.update_layout(
                        **_LAYOUT,
                        title="Social Sharing Impact: Upload Release → Reddit Peak",
                        hovermode="x unified",
                        height=380,
                    )
                    fig.update_layout(
                        yaxis=dict(
                            title=dict(text="YouTube Videos", font=dict(color="#6366f1")),
                            gridcolor="rgba(255,255,255,0.04)",
                            linecolor="rgba(255,255,255,0.08)",
                            zeroline=False,
                        ),
                        yaxis2=dict(
                            title=dict(text="Reddit Posts", font=dict(color="#f97316")),
                            gridcolor="rgba(255,255,255,0)",
                            zeroline=False,
                            overlaying="y",
                            side="right",
                        ),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as _e:
                st.error(f"❌ [Chart 2b – YT vs Reddit Peak] {type(_e).__name__}: {_e}")
                st.exception(_e)

        with col_b:
            try:
                if subs_df is not None and len(subs_df):
                    fig = px.bar(
                        subs_df.head(12),
                        x="post_count", y="subreddit",
                        orientation="h",
                        title="Top Subreddits Discussing This Topic",
                        color="avg_sentiment",
                        color_continuous_scale=[[0,"#ef4444"],[0.5,"#fbbf24"],[1,"#22c55e"]],
                        labels={"post_count": "Posts", "subreddit": "",
                                "avg_sentiment": "Avg Sentiment"},
                    )
                    fig.update_layout(**_LAYOUT, height=380, showlegend=False)
                    fig.update_yaxes(categoryorder="total ascending")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as _e:
                st.error(f"❌ [Chart 2b – Subreddits Bar] {type(_e).__name__}: {_e}")
                st.exception(_e)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 3 — PREDICTIVE
    # ═════════════════════════════════════════════════════════════════════════
    with tab3:

        # Model metrics banner
        try:
            if metrics is not None and len(metrics):
                m = metrics.iloc[0]
                st.markdown(f"""
                <div style='display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;'>
                    <div style='background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3);
                                border-radius:12px; padding:12px 20px; flex:1; min-width:140px;'>
                        <div style='color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase;'>Algorithm</div>
                        <div style='color:white; font-weight:600;'>Random Forest (50 trees)</div>
                    </div>
                    <div style='background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3);
                                border-radius:12px; padding:12px 20px; flex:1; min-width:140px;'>
                        <div style='color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase;'>RMSE</div>
                        <div style='color:white; font-weight:600;'>{fmt_num(m["rmse"])} views</div>
                    </div>
                    <div style='background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3);
                                border-radius:12px; padding:12px 20px; flex:1; min-width:140px;'>
                        <div style='color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase;'>R² Score</div>
                        <div style='color:white; font-weight:600;'>{m["r2"]:.4f}</div>
                    </div>
                    <div style='background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3);
                                border-radius:12px; padding:12px 20px; flex:1; min-width:140px;'>
                        <div style='color:rgba(255,255,255,0.5); font-size:0.75rem; text-transform:uppercase;'>Training Samples</div>
                        <div style='color:white; font-weight:600;'>{int(m["training_samples"])} videos</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        except Exception as _e:
            st.error(f"❌ [Metrics Banner] {type(_e).__name__}: {_e}")
            st.exception(_e)

        col_a, col_b = st.columns(2)

        # ── Chart 3a: Actual vs Predicted ─────────────────────────────────────
        with col_a:
            st.markdown("<div class='section-hdr'>🎯 Actual vs Predicted View Count</div>", unsafe_allow_html=True)
            try:
                if pred_df is not None and len(pred_df):
                    max_v = max(pred_df["view_count"].max(), pred_df["prediction"].max())
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=[0, max_v], y=[0, max_v],
                        mode="lines", name="Perfect Prediction",
                        line=dict(color="rgba(255,255,255,0.25)", dash="dot", width=1.5),
                    ))
                    fig.add_trace(go.Scatter(
                        x=pred_df["view_count"], y=pred_df["prediction"],
                        mode="markers", name="Videos",
                        marker=dict(
                            color=pred_df["sentiment_score"],
                            colorscale=[[0,"#ef4444"],[0.5,"#fbbf24"],[1,"#22c55e"]],
                            size=9, opacity=0.85,
                            colorbar=dict(
                                title="Sentiment",
                                titlefont=dict(color="rgba(255,255,255,0.7)"),
                                tickfont=dict(color="rgba(255,255,255,0.6)"),
                                x=1.02,
                            ),
                            showscale=True,
                        ),
                        hovertemplate=(
                            "Actual: %{x:,.0f}<br>Predicted: %{y:,.0f}"
                            "<br>Sentiment: %{marker.color:.3f}<extra></extra>"
                        ),
                    ))
                    fig.update_layout(
                        **_LAYOUT,
                        title="Random Forest — View Count Predictions",
                        xaxis_title="Actual Views",
                        yaxis_title="Predicted Views",
                        height=420,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No prediction data yet — run analysis first.")
            except Exception as _e:
                st.error(f"❌ [Chart 3a – Actual vs Predicted] {type(_e).__name__}: {_e}")
                st.exception(_e)

        # ── Chart 3b: Feature Importance ──────────────────────────────────────
        with col_b:
            st.markdown("<div class='section-hdr'>🧩 Feature Importance (RF)</div>", unsafe_allow_html=True)
            try:
                if feat_df is not None and len(feat_df):
                    feat_sorted = feat_df.sort_values("importance", ascending=True)
                    fig = go.Figure(go.Bar(
                        x=feat_sorted["importance"],
                        y=feat_sorted["feature"].replace({
                            "like_count":      "Like Count",
                            "comment_count":   "Comment Count",
                            "sentiment_score": "Sentiment Score",
                            "engagement_rate": "Engagement Rate",
                        }),
                        orientation="h",
                        marker=dict(
                            color=feat_sorted["importance"],
                            colorscale=[[0,"#4f46e5"],[1,"#e879f9"]],
                            showscale=False,
                        ),
                        text=[f"{v:.3f}" for v in feat_sorted["importance"]],
                        textposition="outside",
                        textfont=dict(color="rgba(255,255,255,0.75)"),
                        hovertemplate="%{y}: %{x:.4f}<extra></extra>",
                    ))
                    fig.update_layout(
                        **_LAYOUT,
                        title="Which Features Drive View Count?",
                        xaxis_title="Importance Score",
                        height=420,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Feature importance unavailable.")
            except Exception as _e:
                st.error(f"❌ [Chart 3b – Feature Importance] {type(_e).__name__}: {_e}")
                st.exception(_e)

        # ── Chart 3c: Sentiment vs Views Trend ────────────────────────────────
        st.markdown("<div class='section-hdr'>📡 Sentiment Score vs View Count</div>", unsafe_allow_html=True)
        try:
            if top_df is not None and len(top_df) >= 3:
                plot_df = top_df.dropna(subset=["sentiment_score", "view_count", "like_count"])
                if len(plot_df):
                    x_vals = plot_df["sentiment_score"].values
                    y_vals = plot_df["view_count"].values
                    fig = go.Figure()
                    if len(x_vals) >= 2 and x_vals.std() > 0:
                        coeffs = np.polyfit(x_vals, y_vals, 1)
                        x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
                        y_line = np.polyval(coeffs, x_line)
                        fig.add_trace(go.Scatter(
                            x=x_line, y=y_line, mode="lines", name="OLS Trend",
                            line=dict(color="rgba(99,102,241,0.6)", dash="dash", width=2),
                        ))
                    fig.add_trace(go.Scatter(
                        x=plot_df["sentiment_score"], y=plot_df["view_count"],
                        mode="markers", name="Videos",
                        marker=dict(
                            size=np.clip(plot_df["like_count"] / plot_df["like_count"].max() * 28 + 8, 8, 36),
                            color=plot_df["sentiment_score"],
                            colorscale=[[0,"#ef4444"],[0.5,"#fbbf24"],[1,"#22c55e"]],
                            opacity=0.8,
                            line=dict(width=0.5, color="rgba(255,255,255,0.2)"),
                        ),
                        text=plot_df["title"].str[:40] + "…",
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            "Sentiment: %{x:.3f}<br>"
                            "Views: %{y:,.0f}<extra></extra>"
                        ),
                    ))
                    fig.update_layout(
                        **_LAYOUT,
                        title="Sentiment Score vs View Count  (bubble size = likes)",
                        xaxis_title="VADER Sentiment Score",
                        yaxis_title="View Count",
                        height=380,
                    )
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as _e:
            st.error(f"❌ [Chart 3c – Sentiment vs Views] {type(_e).__name__}: {_e}")
            st.exception(_e)

# ─────────────────────────────────────────────────────────────────────────────
# Welcome Screen (no data yet)
# ─────────────────────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div class='welcome-wrap'>
        <div style='font-size:4.5rem; margin-bottom:16px;'>🔭</div>
        <h2 style='font-size:1.8rem; font-weight:700; color:white;'>Ready to Explore</h2>
        <p style='color:rgba(255,255,255,0.45); max-width:480px; margin:12px auto 0; font-size:1rem; line-height:1.7;'>
            Enter a keyword in the left sidebar and click
            <b style='color:#a78bfa;'>Run Analysis</b> to start the full
            Medallion pipeline. Results appear here automatically.
        </p>
        <div class='welcome-pipeline'>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>🎬</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>YouTube API</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>Videos &amp; stats</div>
            </div>
            <div class='pipeline-arrow'>＋</div>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>💬</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>Reddit API</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>Posts &amp; sentiment</div>
            </div>
            <div class='pipeline-arrow'>→</div>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>🥉</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>Bronze</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>Raw JSON</div>
            </div>
            <div class='pipeline-arrow'>→</div>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>🥈</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>Silver</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>Cleaned Parquet</div>
            </div>
            <div class='pipeline-arrow'>→</div>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>🥇</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>Gold</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>Analytics Tables</div>
            </div>
            <div class='pipeline-arrow'>→</div>
            <div class='pipeline-node'>
                <div style='font-size:1.8rem;'>🤖</div>
                <div style='color:white; font-weight:600; margin-top:6px; font-size:0.9rem;'>Random Forest</div>
                <div style='color:rgba(255,255,255,0.4); font-size:0.75rem;'>View predictions</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
