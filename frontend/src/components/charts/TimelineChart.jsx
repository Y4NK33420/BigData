import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: '#16162a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div style={{ color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>{label}</div>
      {payload.map(p => <div key={p.name} style={{ color: p.color }}>{p.name}: <strong>{Number(p.value).toLocaleString()}</strong></div>)}
    </div>
  )
}

export default function TimelineChart({ ytData, rdData }) {
  if (!ytData.length && !rdData.length) {
    return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No timeline data yet.</div>
  }

  // Merge by date
  const dateMap = {}
  ytData.forEach(r => { dateMap[r.published_date] = { date: r.published_date, yt_views: r.total_views || 0 } })
  rdData.forEach(r => {
    if (!dateMap[r.created_date]) dateMap[r.created_date] = { date: r.created_date }
    dateMap[r.created_date].rd_score = r.total_score || 0
  })
  const merged = Object.values(dateMap).sort((a, b) => a.date > b.date ? 1 : -1)

  const maxYT = Math.max(...merged.map(r => r.yt_views || 0), 1)
  const maxRD = Math.max(...merged.map(r => r.rd_score || 0), 1)

  // Normalize Reddit score to YT scale for dual axis simulation
  const chartData = merged.map(r => ({
    date: String(r.date).slice(0, 10),
    'YouTube Views': r.yt_views || 0,
    'Reddit Score':  Math.round(((r.rd_score || 0) / maxRD) * maxYT),
    _rd_raw: r.rd_score || 0,
  }))

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={chartData} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="ytGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6366f1" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="rdGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f97316" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#f97316" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} width={40} tickFormatter={v => v >= 1e6 ? `${(v/1e6).toFixed(1)}M` : v >= 1e3 ? `${(v/1e3).toFixed(0)}K` : v} />
        <Tooltip content={<Tip />} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: '0.78rem' }} />
        <Area type="monotone" dataKey="YouTube Views" stroke="#6366f1" fill="url(#ytGrad)" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Reddit Score" stroke="#f97316" strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
