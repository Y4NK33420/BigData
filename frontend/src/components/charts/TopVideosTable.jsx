import { useState } from 'react'

const SENT_CLASS = { positive: 'badge-positive', negative: 'badge-negative', neutral: 'badge-neutral' }
const fmt = n => n >= 1e9 ? `${(n / 1e9).toFixed(1)}B` : n >= 1e6 ? `${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `${(n / 1e3).toFixed(1)}K` : String(n)
const sentColor = s => s >= 0.05 ? 'var(--green)' : s <= -0.05 ? 'var(--red)' : 'var(--gold)'
const sentLabel = s => s >= 0.05 ? '😊 Positive' : s <= -0.05 ? '😠 Negative' : '😐 Neutral'

function VideoModal({ video, onClose }) {
  if (!video) return null
  const ytUrl = `https://www.youtube.com/watch?v=${video.video_id || ''}`
  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', zIndex: 1000, backdropFilter: 'blur(4px)' }}
      />
      {/* Panel */}
      <div style={{
        position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%,-50%)',
        width: 'min(520px, 92vw)', background: '#1a1a1a', border: '1px solid #383838',
        borderRadius: 12, padding: 28, zIndex: 1001, maxHeight: '80vh', overflowY: 'auto',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div style={{ fontWeight: 700, fontSize: '1rem', lineHeight: 1.4, flex: 1, paddingRight: 12 }}>
            {video.title}
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.4rem', cursor: 'pointer', lineHeight: 1 }}>✕</button>
        </div>

        {/* Channel + date */}
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: 18 }}>
          📺 {video.channel}
          {video.published_date ? ` · 📅 ${String(video.published_date).slice(0, 10)}` : ''}
        </div>

        {/* Metric grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 18 }}>
          {[
            { label: '👁 Views', value: fmt(video.view_count || 0), color: 'var(--text)' },
            { label: '👍 Likes', value: fmt(video.like_count || 0), color: 'var(--accent)' },
            { label: '💬 Comments', value: fmt(video.comment_count || 0), color: 'var(--text)' },
            { label: 'Like/View', value: `${((video.like_to_view_ratio || 0) * 100).toFixed(2)}%`, color: 'var(--accent)' },
            { label: 'Title Sentiment', value: sentLabel(video.sentiment_score || 0), color: sentColor(video.sentiment_score || 0) },
            { label: 'Comment Sentiment', value: sentLabel(video.comment_sentiment || 0), color: sentColor(video.comment_sentiment || 0) },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ background: '#111', borderRadius: 8, padding: '10px 12px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
              <div style={{ fontWeight: 700, color, fontSize: '0.95rem' }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Tags */}
        {video.tags?.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Tags</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {video.tags.slice(0, 10).map((tag, i) => (
                <span key={i} style={{ background: 'rgba(255,69,0,0.12)', border: '1px solid rgba(255,69,0,0.3)', borderRadius: 20, padding: '2px 10px', fontSize: '0.73rem', color: '#FF4500' }}>
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Open on YouTube */}
        {video.video_id && (
          <a href={ytUrl} target="_blank" rel="noreferrer"
            style={{
              display: 'inline-block', marginTop: 6,
              background: 'linear-gradient(135deg, #FF0000, #FF4500)', color: '#fff',
              borderRadius: 8, padding: '10px 20px', fontSize: '0.85rem', fontWeight: 600,
              textDecoration: 'none',
            }}>
            ▶ Open on YouTube ↗
          </a>
        )}
      </div>
    </>
  )
}

export default function TopVideosTable({ rows }) {
  const [selected, setSelected] = useState(null)

  if (!rows.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No video data yet.</div>

  return (
    <>
      <VideoModal video={selected} onClose={() => setSelected(null)} />
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th><th>Title</th><th>Views</th><th>Likes</th><th>Like/View %</th><th>Comments</th>
              <th>Comment Sentiment</th><th>Title Sentiment</th><th>Channel</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 15).map((r, i) => (
              <tr key={i} onClick={() => setSelected(r)}
                style={{ cursor: 'pointer', transition: 'background 0.15s' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,69,0,0.06)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}
              >
                <td style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
                <td style={{ maxWidth: 260 }}>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.title}>
                    {r.title}
                  </div>
                </td>
                <td style={{ fontWeight: 600 }}>{fmt(r.view_count || 0)}</td>
                <td>{fmt(r.like_count || 0)}</td>
                <td style={{ color: 'var(--accent)', fontWeight: 600 }}>
                  {r.like_to_view_ratio != null ? (r.like_to_view_ratio * 100).toFixed(2) + '%' : '—'}
                </td>
                <td>{fmt(r.comment_count || 0)}</td>
                <td style={{ color: sentColor(r.comment_sentiment || 0), fontWeight: 600 }}>
                  {r.comment_sentiment != null ? (r.comment_sentiment).toFixed(3) : '—'}
                </td>
                <td><span className={`badge ${SENT_CLASS[r.sentiment_label] || 'badge-neutral'}`}>{r.sentiment_label || '—'}</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{r.channel}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8, paddingLeft: 4 }}>
          💡 Click any row to view full video details
        </div>
      </div>
    </>
  )
}
