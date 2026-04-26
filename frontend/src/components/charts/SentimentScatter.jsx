import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#1a1a1a', border: '1px solid #383838', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem', maxWidth: 220 }}>
      <div style={{ fontWeight: 600, marginBottom: 4, wordBreak: 'break-word' }}>{d.title?.slice(0, 60)}…</div>
      <div>Sentiment: <strong>{d.sentiment_score?.toFixed(3)}</strong></div>
      <div>Views: <strong>{Number(d.view_count).toLocaleString()}</strong></div>
      <div>Likes: <strong>{Number(d.like_count).toLocaleString()}</strong></div>
    </div>
  )
}

export default function SentimentScatter({ data }) {
  if (!data || data.length < 3) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Need more data for scatter plot.</div>

  const df = data.filter(r => r.sentiment_score != null && r.view_count != null && r.like_count != null)
  const maxLikes = Math.max(...df.map(r => r.like_count || 0), 1)

  const getColor = s => {
    if (s > 0.05) return '#22c55e'
    if (s < -0.05) return '#ef4444'
    return '#fbbf24'
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <ScatterChart margin={{ top: 4, right: 12, bottom: 24, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          type="number" dataKey="sentiment_score" name="Sentiment"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false}
          label={{ value: 'VADER Sentiment Score', position: 'insideBottom', offset: -12, fill: 'rgba(255,255,255,0.3)', fontSize: 11 }}
        />
        <YAxis
          type="number" dataKey="view_count" name="Views"
          tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false}
          tickFormatter={v => v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : v}
        />
        <Tooltip content={<Tip />} />
        <Scatter
          data={df}
          shape={props => {
            const { cx, cy, payload } = props
            const r = 8 + (payload.like_count / maxLikes) * 20
            return <circle cx={cx} cy={cy} r={r} fill={getColor(payload.sentiment_score)} fillOpacity={0.75} stroke="rgba(255,255,255,0.1)" strokeWidth={0.5} />
          }}
        />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
