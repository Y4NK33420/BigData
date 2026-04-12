import { useState } from 'react'
import SentimentChart   from './charts/SentimentChart.jsx'
import TimelineChart    from './charts/TimelineChart.jsx'
import TopVideosTable   from './charts/TopVideosTable.jsx'
import HeatmapChart     from './charts/HeatmapChart.jsx'
import YTvsReddit       from './charts/YTvsReddit.jsx'
import SubredditsChart  from './charts/SubredditsChart.jsx'
import PredictionChart  from './charts/PredictionChart.jsx'
import FeatureImport    from './charts/FeatureImport.jsx'
import SentimentScatter from './charts/SentimentScatter.jsx'

const TABS = ['📊 Descriptive', '🔬 Diagnostic', '🤖 Predictive']

const fmt = n => {
  if (!n && n !== 0) return '—'
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
}

export default function Dashboard({ data }) {
  const [tab, setTab] = useState(0)

  const totalViews = data.top_videos?.reduce((s, r) => s + (r.view_count || 0), 0) || 0
  const totalPosts = data.rd_timeline?.reduce((s, r) => s + (r.post_count || 0), 0) || 0
  const ytVideos   = data.yt_timeline?.reduce((s, r) => s + (r.video_count || 0), 0) || 0
  const avgSent    = data.sentiment?.length
    ? (data.sentiment.reduce((s, r) => s + (r.avg_score || 0) * (r.count || 1), 0) /
       data.sentiment.reduce((s, r) => s + (r.count || 1), 0)).toFixed(3)
    : '—'

  return (
    <>
      <div className="topbar">
        <span className="topbar-keyword">Analytics: <span>{data.keyword}</span></span>
        <span className="topbar-badge">Gold Layer ✓</span>
        {data.model_metrics?.length > 0 && <span className="topbar-badge" style={{ background: 'rgba(34,197,94,0.12)', color: 'var(--green)' }}>RF Model ✓</span>}
      </div>

      {/* KPI row */}
      <div style={{ padding: '16px 28px 0' }}>
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
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {TABS.map((t, i) => (
          <button key={t} className={`tab-btn${tab === i ? ' active' : ''}`} onClick={() => setTab(i)}>{t}</button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {tab === 0 && (
          <>
            <div className="grid-2">
              <div className="card">
                <div className="card-title">💡 <span>Sentiment Distribution</span></div>
                <SentimentChart data={data.sentiment || []} />
              </div>
              <div className="card">
                <div className="card-title">📈 <span>Engagement Over Time</span></div>
                <TimelineChart ytData={data.yt_timeline || []} rdData={data.rd_timeline || []} />
              </div>
            </div>
            <div className="card">
              <div className="card-title">🏅 <span>Top Videos by View Count</span></div>
              <TopVideosTable rows={data.top_videos || []} />
            </div>
          </>
        )}

        {tab === 1 && (
          <>
            <div className="card">
              <div className="card-title">🔥 <span>Engagement Spike Heatmap (Hour × Day)</span></div>
              <HeatmapChart data={data.spikes || []} />
            </div>
            <div className="grid-3-1">
              <div className="card">
                <div className="card-title">🔗 <span>YouTube Releases vs Reddit Discussions</span></div>
                <YTvsReddit ytData={data.yt_timeline || []} rdData={data.rd_timeline || []} />
              </div>
              <div className="card">
                <div className="card-title">📣 <span>Top Subreddits</span></div>
                <SubredditsChart data={data.subreddits || []} />
              </div>
            </div>
          </>
        )}

        {tab === 2 && (
          <>
            {data.model_metrics?.length > 0 && (
              <div className="kpi-row" style={{ marginBottom: 20 }}>
                {[
                  ['Algorithm', 'Random Forest (50 trees)', ''],
                  ['RMSE', fmt(data.model_metrics[0].rmse) + ' views', ''],
                  ['R² Score', data.model_metrics[0].r2?.toFixed(4), ''],
                  ['Train Samples', data.model_metrics[0].training_samples + ' videos', ''],
                ].map(([label, val]) => (
                  <div key={label} className="kpi-card">
                    <div className="kpi-label">{label}</div>
                    <div className="kpi-value" style={{ fontSize: '1rem' }}>{val}</div>
                  </div>
                ))}
              </div>
            )}
            <div className="grid-2">
              <div className="card">
                <div className="card-title">🎯 <span>Actual vs Predicted Views</span></div>
                <PredictionChart data={data.predictions || []} />
              </div>
              <div className="card">
                <div className="card-title">🧩 <span>Feature Importance</span></div>
                <FeatureImport data={data.feat_import || []} />
              </div>
            </div>
            <div className="card">
              <div className="card-title">📡 <span>Sentiment Score vs View Count</span></div>
              <SentimentScatter data={data.top_videos || []} />
            </div>
          </>
        )}
      </div>
    </>
  )
}
