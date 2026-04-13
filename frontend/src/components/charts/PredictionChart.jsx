import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#16162a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>Actual vs Predicted</div>
      <div>Actual: <strong>{Number(d.x).toLocaleString()}</strong></div>
      <div>Predicted: <strong>{Number(d.y).toLocaleString()}</strong></div>
      <div>Sentiment: <strong>{d.sentiment_score?.toFixed(3)}</strong></div>
    </div>
  )
}

export default function PredictionChart({ data }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No prediction data — run analysis first.</div>

  const maxV = Math.max(...data.map(r => Math.max(r.view_count || 0, r.prediction || 0)), 1)
  const chartData = data.map(r => ({ x: r.view_count || 0, y: r.prediction || 0, sentiment_score: r.sentiment_score }))

  const getColor = s => {
    if (!s && s !== 0) return '#6366f1'
    if (s >  0.05) return '#22c55e'
    if (s < -0.05) return '#ef4444'
    return '#fbbf24'
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 4, right: 12, bottom: 20, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis type="number" dataKey="x" name="Actual" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : v} label={{ value: 'Actual Views', position: 'insideBottom', offset: -10, fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} />
        <YAxis type="number" dataKey="y" name="Predicted" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : v} />
        <Tooltip content={<Tip />} />
        <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
        {/* Perfect prediction line — approximate as reference line at y=x */}
        <Scatter
          data={chartData}
          shape={props => {
            const { cx, cy, payload } = props
            const color = getColor(payload.sentiment_score)
            return <circle cx={cx} cy={cy} r={6} fill={color} fillOpacity={0.8} stroke="none" />
          }}
        />
      </ScatterChart>
    </ResponsiveContainer>
  )
}
