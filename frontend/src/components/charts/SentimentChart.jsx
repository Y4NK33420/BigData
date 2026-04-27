import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts'

const COLORS = { positive: '#7DE0A6', negative: '#F08BA0', neutral: '#F4C37A' }

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '8px 14px', fontSize: '0.82rem' }}>
      {payload.map(p => <div key={p.name} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></div>)}
    </div>
  )
}

const LegendRow = ({ items }) => (
  <div style={{ display: 'flex', justifyContent: 'center', gap: 16, flexWrap: 'wrap', marginTop: 10 }}>
    {items.map(item => (
      <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text)', fontSize: 12 }}>
        <span style={{ width: 12, height: 12, borderRadius: 3, background: item.color, flexShrink: 0 }} />
        <span>{item.name}</span>
      </div>
    ))}
  </div>
)

export default function SentimentChart({ data }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No sentiment data yet.</div>

  const donut = Object.entries(
    data.reduce((acc, r) => { acc[r.sentiment_label] = (acc[r.sentiment_label] || 0) + (r.count || 0); return acc }, {})
  ).map(([name, value]) => ({ name, value }))

  const byLabel = {}
  data.forEach(r => {
    if (!byLabel[r.sentiment_label]) byLabel[r.sentiment_label] = { label: r.sentiment_label, YouTube: 0, Reddit: 0 }
    const src = (r.source || '').toLowerCase()
    if (src === 'youtube') byLabel[r.sentiment_label].YouTube += r.count || 0
    else if (src === 'reddit') byLabel[r.sentiment_label].Reddit += r.count || 0
  })
  const barData = Object.values(byLabel)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>Overall</div>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart margin={{ top: 6, right: 6, bottom: 6, left: 6 }}>
            <Pie
              data={donut}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={3}
              dataKey="value"
              labelLine={false}
              stroke="#f5effd"
              strokeWidth={2}
            >
              {donut.map(d => <Cell key={d.name} fill={COLORS[d.name] || '#aaaaaa'} />)}
            </Pie>
            <Tooltip allowEscapeViewBox={{ x: true, y: true }} content={<Tip />} />
          </PieChart>
        </ResponsiveContainer>
        <LegendRow items={donut.map(item => ({ name: item.name, color: COLORS[item.name] || '#aaaaaa' }))} />
      </div>

      <div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>By Platform</div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={barData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="label" tick={{ fill: 'rgba(255,255,255,0.72)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }} axisLine={false} tickLine={false} width={30} />
            <Tooltip allowEscapeViewBox={{ x: true, y: true }} content={<Tip />} />
            <Bar dataKey="YouTube" fill="#F17DAC" radius={[5, 5, 0, 0]} />
            <Bar dataKey="Reddit" fill="#A887CE" radius={[5, 5, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <LegendRow items={[{ name: 'YouTube', color: '#F17DAC' }, { name: 'Reddit', color: '#A887CE' }]} />
      </div>
    </div>
  )
}
