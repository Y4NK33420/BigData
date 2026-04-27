import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#1a1a1a', border: '1px solid #383838', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div style={{ fontWeight: 600 }}>{d.subreddit}</div>
      <div style={{ color: '#FF4500' }}>Posts: {d.post_count}</div>
      <div style={{ color: d.avg_sentiment > 0 ? '#22c55e' : '#FF0000' }}>Avg Sentiment: {d.avg_sentiment?.toFixed(3)}</div>
    </div>
  )
}

export default function SubredditsChart({ data }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No subreddit data.</div>

  const sorted = [...data].sort((a, b) => (a.post_count || 0) - (b.post_count || 0)).slice(-12)

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 40, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="subreddit" tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 10 }} axisLine={false} tickLine={false} width={90} />
        <Tooltip content={<Tip />} />
        <Bar dataKey="post_count" radius={[0, 4, 4, 0]}>
          {sorted.map((d, i) => {
            const s = d.avg_sentiment || 0
            const color = s > 0.05 ? '#22c55e' : s < -0.05 ? '#ef4444' : '#fbbf24'
            return <Cell key={i} fill={color} fillOpacity={0.75} />
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
