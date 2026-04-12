import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer, LabelList } from 'recharts'

const LABEL_MAP = { like_count: 'Like Count', comment_count: 'Comment Count', sentiment_score: 'Sentiment Score', engagement_rate: 'Engagement Rate' }

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#16162a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div>{LABEL_MAP[payload[0].payload.feature] || payload[0].payload.feature}</div>
      <div style={{ color: '#a78bfa' }}>Importance: <strong>{Number(payload[0].value).toFixed(4)}</strong></div>
    </div>
  )
}

export default function FeatureImport({ data }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No feature data.</div>

  const sorted = [...data].sort((a, b) => (a.importance || 0) - (b.importance || 0))
    .map(r => ({ ...r, label: LABEL_MAP[r.feature] || r.feature }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 60, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 1]} />
        <YAxis type="category" dataKey="label" tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} axisLine={false} tickLine={false} width={110} />
        <Tooltip content={<Tip />} />
        <Bar dataKey="importance" radius={[0,4,4,0]}>
          <LabelList dataKey="importance" position="right" formatter={v => v.toFixed(3)} style={{ fill: 'rgba(255,255,255,0.5)', fontSize: '0.75rem' }} />
          {sorted.map((d, i) => {
            const t = i / (sorted.length - 1 || 1)
            const r = Math.round(79 + t * (232 - 79))
            const g = Math.round(70 + t * (121 - 70))
            const b = Math.round(229 + t * (249 - 229))
            return <Cell key={i} fill={`rgb(${r},${g},${b})`} fillOpacity={0.8} />
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
