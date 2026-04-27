import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#A887CE', '#F17DAC']

const LegendRow = ({ data }) => (
  <div style={{ display: 'flex', justifyContent: 'center', gap: 18, flexWrap: 'wrap', marginTop: 12 }}>
    {data.map((item, index) => (
      <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text)', fontSize: 12 }}>
        <span style={{ width: 14, height: 14, borderRadius: 3, background: COLORS[index], flexShrink: 0 }} />
        <span>{item.name}</span>
      </div>
    ))}
  </div>
)

export default function PlatformShareChart({ ytTimeline, rdTimeline }) {
  const ytTotal = ytTimeline?.reduce((s, r) => s + (r.video_count || 0), 0) || 0
  const rdTotal = rdTimeline?.reduce((s, r) => s + (r.post_count || 0), 0) || 0
  const total = ytTotal + rdTotal

  if (!total) return <p style={{ color: 'var(--muted)', textAlign: 'center', paddingTop: 40 }}>No data</p>

  const data = [
    { name: 'YouTube Videos', value: ytTotal },
    { name: 'Reddit Posts', value: rdTotal },
  ]

  return (
    <div>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart margin={{ top: 8, right: 12, bottom: 8, left: 12 }}>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="46%"
            innerRadius={48}
            outerRadius={84}
            paddingAngle={4}
            stroke="#f5effd"
            strokeWidth={2}
            labelLine={false}
          >
            {data.map((_, index) => <Cell key={index} fill={COLORS[index]} />)}
          </Pie>
          <Tooltip
            allowEscapeViewBox={{ x: true, y: true }}
            contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 14, color: '#fff' }}
            itemStyle={{ color: '#fff' }}
            formatter={value => value.toLocaleString()}
          />
        </PieChart>
      </ResponsiveContainer>
      <LegendRow data={data} />
    </div>
  )
}
