import { ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const Tip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, padding: '8px 14px', fontSize: '0.82rem' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</div>
      {payload.map(p => <div key={p.name} style={{ color: p.color }}>{p.name}: <strong>{Number(p.value).toLocaleString()}</strong></div>)}
    </div>
  )
}

export default function YTvsReddit({ ytData, rdData }) {
  if (!ytData.length && !rdData.length) {
    return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No data.</div>
  }

  const dateMap = {}
  ytData.forEach(r => { dateMap[r.published_date] = { date: r.published_date, 'YT Uploads': r.video_count || 0 } })
  rdData.forEach(r => {
    if (!dateMap[r.created_date]) dateMap[r.created_date] = { date: r.created_date }
    dateMap[r.created_date]['Reddit Posts'] = r.post_count || 0
  })
  const merged = Object.values(dateMap).sort((a, b) => a.date > b.date ? 1 : -1)
    .map(r => ({ ...r, date: String(r.date).slice(0, 10) }))

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={merged} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis yAxisId="left" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
        <YAxis yAxisId="right" orientation="right" tick={{ fill: '#d9b5ff', fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
        <Tooltip content={<Tip />} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: '0.78rem' }} />
        <Bar yAxisId="left" dataKey="YT Uploads" fill="rgba(241,125,172,0.72)" radius={[5, 5, 0, 0]} />
        <Line yAxisId="right" type="monotone" dataKey="Reddit Posts" stroke="#A887CE" strokeWidth={2.5} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
