import { useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SentimentChart from './charts/SentimentChart.jsx'
import TimelineChart from './charts/TimelineChart.jsx'
import TopVideosTable from './charts/TopVideosTable.jsx'
import HeatmapChart from './charts/HeatmapChart.jsx'
import YTvsReddit from './charts/YTvsReddit.jsx'
import SubredditsChart from './charts/SubredditsChart.jsx'
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
  const [aiIdeas, setAiIdeas] = useState([])
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
    setAiLoading(true)
    setAiError(null)
    try {
      const res = await fetch(`/api/prescribe?keyword=${encodeURIComponent(data.keyword)}`)
      if (!res.ok) throw new Error(await res.text())
      const json = await res.json()
      setAiCards(json.recommendations)
      setAiIdeas(json.video_ideas || [])
    } catch (e) {
      setAiError(e.message || 'Gemini API error')
    } finally {
      setAiLoading(false)
    }
  }, [data.keyword])

  return (
    <>
      <div className="topbar">
        <span className="topbar-keyword">Dashboard <span>{data.keyword}</span></span>
        <div className="topbar-badges">
          <span className="topbar-badge">Gold Layer</span>
          {data.model_metrics?.length > 0 && <span className="topbar-badge" style={{ color: 'var(--green)' }}>RF Model Ready</span>}
          {viability != null && <span className="topbar-badge" style={{ color: scoreColor(viability) }}>Viability {viability}/100</span>}
        </div>
      </div>

      <div className="dashboard-intro">
        <div className="dashboard-hero">
          <section className="dashboard-titleblock">
            <div className="eyebrow">Cross-platform intelligence</div>
            <h1>YouTube + Reddit signal board</h1>
            <p>
              A softer, premium control room for trend diagnostics, model-backed opportunity scoring,
              and recommendation generation from your latest pipeline outputs.
            </p>
          </section>
          <aside className="hero-sidecard">
            <div className="hero-sidecard-label">Opportunity Index</div>
            <div className="hero-sidecard-value">{viability != null ? `${viability}/100` : 'Live'}</div>
            <div className="hero-sidecard-meta">
              <div>
                Model confidence
                <strong>{data.model_metrics?.[0]?.r2 != null ? data.model_metrics[0].r2.toFixed(3) : 'Pending'}</strong>
              </div>
              <div>
                Active videos
                <strong>{fmt(ytVideos)}</strong>
              </div>
            </div>
          </aside>
        </div>

        <div className="kpi-row">
          <div className="kpi-card">
            <div className="kpi-label">Total Views</div>
            <div className="kpi-value">{fmt(totalViews)}</div>
            <div className="kpi-sub">YouTube reach</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Videos Tracked</div>
            <div className="kpi-value">{fmt(ytVideos)}</div>
            <div className="kpi-sub">timeline coverage</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Reddit Posts</div>
            <div className="kpi-value">{fmt(totalPosts)}</div>
            <div className="kpi-sub">community demand</div>
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
            <div className="kpi-sub">weighted polarity</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">{data.model_metrics?.length > 0 ? 'RF R² Score' : 'Model State'}</div>
            <div className="kpi-value" style={{ color: data.model_metrics?.length > 0 ? 'var(--text)' : 'var(--text-muted)' }}>
              {data.model_metrics?.length > 0 ? data.model_metrics[0].r2?.toFixed(3) : 'Pending'}
            </div>
            <div className="kpi-sub">{data.model_metrics?.length > 0 ? 'predictive fit' : 'no metrics yet'}</div>
          </div>
        </div>
      </div>

      <div className="tab-content">
        <div className="grid-masonry">
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

          <div className="card">
            <div className="card-title"><span>Top Videos by View Count</span></div>
            <TopVideosTable rows={data.top_videos || []} />
          </div>

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

          <div className="grid-2">
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title"><span>YouTube Releases vs Reddit Discussions</span></div>
              <YTvsReddit ytData={data.yt_timeline || []} rdData={data.rd_timeline || []} />
            </div>
            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-title"><span>Quality vs Reach</span></div>
              <QualityReachChart topVideos={data.top_videos || []} />
            </div>
          </div>

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

          {data.feat_import?.length > 0 && (
            <div className="card">
              <div className="card-title"><span>Feature Importance</span></div>
              <FeatureImport data={data.feat_import || []} />
            </div>
          )}

          {data.topic_recs?.length > 0 && (
            <div className="grid-2">
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card-title"><span>Viability Score Breakdown</span></div>
                <ViabilityBreakdownChart topicRecs={data.topic_recs || []} />
              </div>
              {totalRecs && (
                <div className="card" style={{ marginBottom: 0, border: `1px solid ${scoreColor(totalRecs.raw_score)}33` }}>
                  <div className="card-title"><span>Topic Viability Assessment</span></div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginTop: 12 }}>
                    <div style={{ fontSize: '3.5rem', fontWeight: 900, color: scoreColor(totalRecs.raw_score) }}>
                      {totalRecs.raw_score}<span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>/100</span>
                    </div>
                    <p style={{ color: 'var(--text)', fontSize: 14, lineHeight: 1.7 }}>{totalRecs.note}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-title"><span>AI Strategy Recommendations</span></div>
            {!aiCards && !aiLoading && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <p style={{ color: 'var(--muted)', marginBottom: 16, fontSize: 13 }}>
                  Generate title concepts and predicted-view estimates from the current dashboard state.
                </p>
                <button
                  onClick={fetchAiCards}
                  style={{
                    background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 12,
                    padding: '12px 32px',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Generate Recommendations
                </button>
              </div>
            )}
            {aiLoading && (
              <p style={{ textAlign: 'center', color: 'var(--accent)', padding: '24px 0' }}>
                Gemini is analyzing your keyword data...
              </p>
            )}
            {aiError && (
              <p style={{ textAlign: 'center', color: 'var(--red)', padding: '12px 0', fontSize: 13 }}>
                {aiError}
              </p>
            )}
            {aiIdeas.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginTop: 16 }}>
                {aiIdeas.map((idea, index) => (
                  <div
                    key={`${idea.title}-${index}`}
                    style={{
                      background: 'rgba(255,255,255,0.035)',
                      border: '1px solid var(--border)',
                      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04)',
                      borderRadius: 18,
                      padding: 16,
                    }}
                  >
                    <div style={{ color: 'var(--text-muted)', fontSize: 11, textTransform: 'uppercase', fontWeight: 700, marginBottom: 8 }}>
                      Idea {index + 1}
                    </div>
                    <h3 style={{ fontSize: 16, lineHeight: 1.4, marginBottom: 12 }}>{idea.title}</h3>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', marginBottom: 12 }}>
                      <span style={{ color: 'var(--green)', fontSize: 26, fontWeight: 900 }}>
                        {fmt(idea.predicted_views || 0)}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>predicted views</span>
                    </div>
                    {idea.predicted_view_range && (
                      <div style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 12 }}>
                        Range: {fmt(idea.predicted_view_range.low)} - {fmt(idea.predicted_view_range.high)}
                      </div>
                    )}
                    <p style={{ color: 'var(--text)', fontSize: 13, lineHeight: 1.7, marginBottom: 10 }}>
                      <strong>Format:</strong> {idea.format}
                    </p>
                    <p style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.7, marginBottom: 10 }}>
                      <strong>Audience:</strong> {idea.target_audience}
                    </p>
                    <p style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.7, marginBottom: 10 }}>
                      <strong>Why it may work:</strong> {idea.rationale}
                    </p>
                    <p style={{ color: 'var(--text-muted)', fontSize: 12, lineHeight: 1.7, marginBottom: 10 }}>
                      <strong>Distribution:</strong> {idea.distribution_strategy}
                    </p>
                    <p style={{ color: 'var(--gold)', fontSize: 12, lineHeight: 1.7 }}>
                      <strong>Risk:</strong> {idea.risk_warning}
                    </p>
                  </div>
                ))}
              </div>
            )}
            {aiCards && aiIdeas.length === 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{
                  background: 'rgba(168,135,206,0.08)',
                  borderRadius: 18,
                  padding: '20px 24px',
                  border: '1px solid rgba(168,135,206,0.18)',
                  color: 'var(--text)',
                  fontSize: 14,
                  lineHeight: 1.8,
                }} className="markdown-text ai-markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {aiCards}
                  </ReactMarkdown>
                </div>
                <button
                  onClick={fetchAiCards}
                  style={{
                    marginTop: 14,
                    background: 'transparent',
                    color: 'var(--accent)',
                    border: '1px solid var(--accent)',
                    borderRadius: 12,
                    padding: '8px 22px',
                    fontSize: 12,
                    cursor: 'pointer',
                  }}
                >
                  Refresh
                </button>
              </div>
            )}
            {aiCards && aiIdeas.length > 0 && (
              <button
                onClick={fetchAiCards}
                style={{
                  marginTop: 14,
                  background: 'transparent',
                  color: 'var(--accent)',
                  border: '1px solid var(--accent)',
                  borderRadius: 12,
                  padding: '8px 22px',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                Regenerate & Predict
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
