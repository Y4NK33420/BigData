import { useState, useCallback } from 'react'
import SentimentChart from './charts/SentimentChart.jsx'
import TimelineChart from './charts/TimelineChart.jsx'
import TopVideosTable from './charts/TopVideosTable.jsx'
import HeatmapChart from './charts/HeatmapChart.jsx'
import YTvsReddit from './charts/YTvsReddit.jsx'
import SubredditsChart from './charts/SubredditsChart.jsx'
import PredictionChart from './charts/PredictionChart.jsx'
import FeatureImport from './charts/FeatureImport.jsx'
import SentimentScatter from './charts/SentimentScatter.jsx'
import PlatformShareChart from './charts/PlatformShareChart.jsx'
import QualityReachChart from './charts/QualityReachChart.jsx'
import CommentSentimentChart from './charts/CommentSentimentChart.jsx'
import TopicViabilityRadar from './charts/TopicViabilityRadar.jsx'
import ViabilityBreakdownChart from './charts/ViabilityBreakdownChart.jsx'

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}

const scoreColor = score => score >= 75 ? 'var(--green)' : score >= 45 ? 'var(--gold)' : 'var(--red)'

export default function Dashboard({ data }) {
  const [aiCards, setAiCards] = useState(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState(null)

  const totalViews = data.top_videos?.reduce((s, r) => s + (r.view_count || 0), 0) || 0
  const totalPosts = data.rd_timeline?.reduce((s, r) => s + (r.post_count || 0), 0) || 0
  const ytVideos = data.yt_timeline?.reduce((s, r) => s + (r.video_count || 0), 0) || 0
  const avgLvRatio = data.top_videos?.length
    ? (data.top_videos.reduce((s, r) => s + (r.like_to_view_ratio || 0), 0) / data.top_videos.length * 100).toFixed(2)
    : '—'
  const avgSent = data.sentiment?.length
    ? (data.sentiment.reduce((s, r) => s + (r.avg_score || 0) * (r.count || 1), 0) /
      data.sentiment.reduce((s, r) => s + (r.count || 1), 0)).toFixed(3)
    : '—'
  const viability = data.viability_score
  const totalRecs = data.topic_recs?.find(r => r.metric === 'TOTAL_VIABILITY')

  const fetchAiCards = useCallback(async () => {
    setAiLoading(true); setAiError(null)
    try {
      const res = await fetch(`/api/prescribe?keyword=${encodeURIComponent(data.keyword)}`)
      if (!res.ok) throw new Error(await res.text())
      const json = await res.json()
      setAiCards(json.recommendations)
    } catch (e) {
      setAiError(e.message || 'Gemini API error')
    } finally {
      setAiLoading(false)
    }
  }, [data.keyword])

  return (
    <>
      {/* Topbar */}
      <div className="topbar">
        <span className="topbar-keyword">Analytics: <span>{data.keyword}</span></span>
        <span className="topbar-badge">Gold Layer ✓</span>
        {data.model_metrics?.length > 0 && <span className="topbar-badge" style={{ background: 'rgba(34,197,94,0.12)', color: 'var(--green)' }}>RF Model ✓</span>}
        {viability != null && (
          <span className="topbar-badge" style={{ background: 'rgba(139,92,246,0.12)', color: scoreColor(viability) }}>
            Viability: {viability}/100
          </span>
        )}
      </div>

      {/* Header & KPI Row */}
      <div style={{ padding: '24px 28px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: '2.6rem', fontWeight: 900, color: '#FF0000', letterSpacing: '-1px' }}>▶</span>
            <h1 style={{ fontSize: '2.4rem', fontWeight: 900, margin: 0, background: 'linear-gradient(90deg, #FF0000, #FF4500)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              YouTube + Reddit Analytics
            </h1>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 500, letterSpacing: '1.5px', textTransform: 'uppercase' }}>
            Social Media Intelligence Dashboard
          </div>
        </div>

        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">Total Views</div>
            <div className="kpi-value">{fmt(totalViews)}</div>
            <div className="kpi-sub">YouTube</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Videos Tracked</div>
            <div className="kpi-value">{fmt(ytVideos)}</div>
            <div className="kpi-sub">across timeline</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Reddit Posts</div>
            <div className="kpi-value">{fmt(totalPosts)}</div>
            <div className="kpi-sub">scraped</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg Like/View</div>
            <div className="kpi-value" style={{ color: 'var(--accent)' }}>{avgLvRatio}%</div>
            <div className="kpi-sub">engagement quality</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg Sentiment</div>
            <div className="kpi-value" style={{ color: avgSent > 0 ? 'var(--green)' : avgSent < 0 ? 'var(--red)' : 'var(--gold)' }}>
              {avgSent}
            </div>
            <div className="kpi-sub">VADER score</div>
          </div>
          {data.model_metrics?.length > 0 && (
            <div className="kpi-card">
              <div className="kpi-label">RF R² Score</div>
              <div className="kpi-value">{data.model_metrics[0].r2?.toFixed(3)}</div>
              <div className="kpi-sub">Random Forest</div>
            </div>
          )}
          {viability != null && (
            <div className="kpi-card">
              <div className="kpi-label">Viability Score</div>
              <div className="kpi-value" style={{ color: scoreColor(viability) }}>{viability}/100</div>
              <div className="kpi-sub">topic opportunity</div>
            </div>
          )}
        </div>
      </div>

      {/* Grid Layout (Netflix Dense Style) */}
      <div className="grid-masonry" style={{ padding: '0 28px 40px' }}>

        {/* ROW 1: Platform Share & Over Time */}
        <div className="grid-1-3">
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Platform Share</span></div>
            <PlatformShareChart ytTimeline={data.yt_timeline || []} rdTimeline={data.rd_timeline || []} />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Cross-Platform Engagement Over Time</span></div>
            <TimelineChart ytData={data.yt_timeline || []} rdData={data.rd_timeline || []} />
          </div>
        </div>

        {/* ROW 2: Subreddits, Genres/Sentiments */}
        <div className="grid-2">
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Top Subreddit Communities</span></div>
            <SubredditsChart data={data.subreddits || []} />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Sentiment Distribution</span></div>
            <SentimentChart data={data.sentiment || []} />
          </div>
        </div>

        {/* ROW 3: Top Videos Table (styled to fit dark theme) */}
        <div className="card">
          <div className="card-title"><span>Top Videos by View Count</span></div>
          <TopVideosTable rows={data.top_videos || []} />
        </div>

        {/* ROW 4: Heatmap & Radar */}
        <div className="grid-3-1">
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Engagement Spike Heatmap</span></div>
            <HeatmapChart data={data.spikes || []} />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Topic Viability Radar</span></div>
            <TopicViabilityRadar topicRecs={data.topic_recs || []} />
          </div>
        </div>

        {/* ROW 5: YouTube vs Reddit & Quality Reach */}
        <div className="grid-2">
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>YouTube Releases vs Reddit Discussions</span></div>
            <YTvsReddit ytData={data.yt_timeline || []} rdData={data.rd_timeline || []} />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Quality vs Reach — Clickbait Detector</span></div>
            <QualityReachChart topVideos={data.top_videos || []} />
          </div>
        </div>

        {/* ROW 6: Comment Sentiment & Sentiment Scatter */}
        <div className="grid-2">
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Comment Sentiment per Video</span></div>
            <CommentSentimentChart topVideos={data.top_videos || []} />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>Sentiment Score vs View Count</span></div>
            <SentimentScatter data={data.top_videos || []} />
          </div>
        </div>

        {/* ROW 7: Predictive — Actual vs Predicted + Feature Importance */}
        {data.predictions?.length > 0 && (
          <div className="grid-2">
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title"><span>Actual vs Predicted Views (ML)</span></div>
              <PredictionChart data={data.predictions || []} />
            </div>
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title"><span>Feature Importance (Random Forest)</span></div>
              <FeatureImport data={data.feat_import || []} />
            </div>
          </div>
        )}

        {/* ROW 8: Viability Breakdown + Prescriptive Score */}
        {data.topic_recs?.length > 0 && (
          <div className="grid-2">
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title"><span>Component Viability Score Breakdown</span></div>
              <ViabilityBreakdownChart topicRecs={data.topic_recs || []} />
            </div>
            {totalRecs && (
              <div className="card" style={{ marginBottom: 0, borderLeft: `4px solid ${scoreColor(totalRecs.raw_score)}` }}>
                <div className="card-title"><span>Topic Viability Assessment</span></div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginTop: 12 }}>
                  <div style={{ fontSize: '3.5rem', fontWeight: 900, color: scoreColor(totalRecs.raw_score) }}>
                    {totalRecs.raw_score}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span>
                  </div>
                  <p style={{ color: 'var(--text)', fontSize: 14, lineHeight: 1.6 }}>{totalRecs.note}</p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ROW 10: AI Recommendations */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-title">✨ <span>AI-Powered Strategy Recommendations (Gemini)</span></div>
          {!aiCards && !aiLoading && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <p style={{ color: 'var(--muted)', marginBottom: 16, fontSize: 13 }}>
                Click below to generate hyper-specific content strategy recommendations powered by Gemini AI, using the Gold metrics from earlier pipeline layers.
              </p>
              <button
                onClick={fetchAiCards}
                style={{
                  background: 'linear-gradient(135deg, #FF0000, #FF4500)',
                  color: '#fff', border: 'none', borderRadius: 8, padding: '12px 32px',
                  fontSize: 14, fontWeight: 600, cursor: 'pointer', letterSpacing: '0.5px',
                }}
              >
                ✨ Generate Recommendations
              </button>
            </div>
          )}
          {aiLoading && (
            <p style={{ textAlign: 'center', color: 'var(--accent)', padding: '24px 0' }}>
              🔄 Gemini is analyzing your keyword data...
            </p>
          )}
          {aiError && (
            <p style={{ textAlign: 'center', color: 'var(--red)', padding: '12px 0', fontSize: 13 }}>
              ⚠️ {aiError}
            </p>
          )}
          {aiCards && (
            <div style={{ marginTop: 16 }}>
              <div style={{
                background: 'rgba(255,0,0,0.05)', borderRadius: 8, padding: '20px 24px',
                borderLeft: '4px solid #FF4500', whiteSpace: 'pre-wrap',
                color: 'var(--text)', fontSize: 14, lineHeight: 1.8,
              }}>
                {aiCards}
              </div>
              <button
                onClick={fetchAiCards}
                style={{
                  marginTop: 14, background: 'transparent', color: 'var(--accent)',
                  border: '1px solid var(--accent)', borderRadius: 8, padding: '8px 22px',
                  fontSize: 12, cursor: 'pointer',
                }}
              >
                🔄 Regenerate
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
