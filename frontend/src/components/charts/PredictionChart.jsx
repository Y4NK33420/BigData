import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#1a1a1a', border: '1px solid #383838', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>Actual vs Predicted</div>
      <div>Actual: <strong>{Number(d.x).toLocaleString()}</strong></div>
      <div>Predicted: <strong>{Number(d.y).toLocaleString()}</strong></div>
      <div>Sentiment: <strong>{d.sentiment_score?.toFixed(3)}</strong></div>
    </div>
  )
}

export default function PredictionChart({ data, modelMetrics }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No prediction data — run analysis first.</div>

  const sampleCount = data.length
  const isLowSample = sampleCount < 15

  const chartData = data.map(r => ({ x: r.view_count || 0, y: r.prediction || 0, sentiment_score: r.sentiment_score }))

  const getColor = s => {
    if (!s && s !== 0) return '#FF0000'
    if (s > 0.05) return '#22c55e'
    if (s < -0.05) return '#FF0000'
    return '#fbbf24'
  }

  return (
    <div>
      {isLowSample && (
        <div style={{
          background: 'rgba(255,165,0,0.1)', border: '1px solid rgba(255,165,0,0.4)',
          borderRadius: 6, padding: '8px 14px', marginBottom: 12, fontSize: '0.8rem', color: '#fbbf24'
        }}>
          ⚠️ Only {sampleCount} sample{sampleCount !== 1 ? 's' : ''} available — predictions may not be reliable with small datasets. Run the pipeline with more varied keywords to improve accuracy.
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 4, right: 12, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis type="number" dataKey="x" name="Actual" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : v} label={{ value: 'Actual Views', position: 'insideBottom', offset: -10, fill: 'rgba(255,255,255,0.3)', fontSize: 11 }} />
          <YAxis type="number" dataKey="y" name="Predicted" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}K` : v} />
          <Tooltip content={<Tip />} />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" />
          <Scatter
            data={chartData}
            shape={props => {
              const { cx, cy, payload } = props
              const color = getColor(payload.sentiment_score)
              return <circle cx={cx} cy={cy} r={6} fill={color} fillOpacity={0.85} stroke="none" />
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
