const SENT_CLASS = { positive: 'badge-positive', negative: 'badge-negative', neutral: 'badge-neutral' }

const fmt = n => n >= 1e9 ? `${(n/1e9).toFixed(1)}B` : n >= 1e6 ? `${(n/1e6).toFixed(1)}M` : n >= 1e3 ? `${(n/1e3).toFixed(1)}K` : String(n)

export default function TopVideosTable({ rows }) {
  if (!rows.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No video data yet.</div>

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>#</th><th>Title</th><th>Views</th><th>Likes</th><th>Comments</th><th>Sentiment</th><th>Channel</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 15).map((r, i) => (
            <tr key={i}>
              <td style={{ color: 'var(--text-muted)' }}>{i + 1}</td>
              <td style={{ maxWidth: 300 }}>
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={r.title}>
                  {r.title}
                </div>
              </td>
              <td style={{ fontWeight: 600 }}>{fmt(r.view_count || 0)}</td>
              <td>{fmt(r.like_count || 0)}</td>
              <td>{fmt(r.comment_count || 0)}</td>
              <td><span className={`badge ${SENT_CLASS[r.sentiment_label] || 'badge-neutral'}`}>{r.sentiment_label || '—'}</span></td>
              <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{r.channel}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
