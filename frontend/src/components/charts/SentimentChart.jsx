import { PieChart, Pie, Cell, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend } from 'recharts'

const COLORS = { positive: '#22c55e', negative: '#ef4444', neutral: '#fbbf24' }

const Tip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#16162a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      {payload.map(p => <div key={p.name} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></div>)}
    </div>
  )
}

export default function SentimentChart({ data }) {
  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No sentiment data yet.</div>

  // Aggregate for donut
  const donut = Object.entries(
    data.reduce((acc, r) => { acc[r.sentiment_label] = (acc[r.sentiment_label] || 0) + (r.count || 0); return acc }, {})
  ).map(([name, value]) => ({ name, value }))

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
      <div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>Overall (YouTube + Reddit)</div>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={donut} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value" label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`} labelLine={false}>
              {donut.map(d => <Cell key={d.name} fill={COLORS[d.name] || '#6366f1'} />)}
            </Pie>
            <Tooltip content={<Tip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8 }}>By Platform</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="sentiment_label" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} axisLine={false} tickLine={false} width={30} />
            <Tooltip content={<Tip />} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: '0.78rem' }} />
            <Bar dataKey="count" name="YouTube" fill="#6366f1" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
