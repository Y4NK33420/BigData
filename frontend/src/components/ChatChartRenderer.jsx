import {
  ResponsiveContainer,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ScatterChart,
  Scatter,
} from 'recharts'

const PIE_COLORS = ['#FF0000', '#FF4500', '#fbbf24', '#22c55e', '#06b6d4', '#8b5cf6']

export default function ChatChartRenderer({ chart }) {
  const data = Array.isArray(chart?.data) ? chart.data : []
  if (!data.length) return null

  const chartType = (chart.chart_type || 'bar').toLowerCase()
  const xKey = chart.x_key || Object.keys(data[0] || {})[0]
  const yKey = chart.y_key || Object.keys(data[0] || {})[1]

  return (
    <div className="chat-chart-card">
      <div className="chat-chart-title">{chart.title || 'Chart'}</div>
      <ResponsiveContainer width="100%" height={230}>
        {chartType === 'line' ? (
          <LineChart data={data} margin={{ top: 5, right: 12, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey={xKey} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <Tooltip />
            <Line type="monotone" dataKey={yKey} stroke="#FF4500" strokeWidth={2} dot={false} />
          </LineChart>
        ) : null}

        {chartType === 'pie' ? (
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} outerRadius={80} label>
              {data.map((_, idx) => (
                <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        ) : null}

        {chartType === 'radar' ? (
          <RadarChart data={data}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey={xKey} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <PolarRadiusAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <Radar dataKey={yKey} stroke="#FF0000" fill="#FF0000" fillOpacity={0.35} />
            <Tooltip />
          </RadarChart>
        ) : null}

        {chartType === 'scatter' ? (
          <ScatterChart margin={{ top: 5, right: 12, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis type="category" dataKey={xKey} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <YAxis type="number" dataKey={yKey} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <Tooltip />
            <Scatter data={data} fill="#FF4500" />
          </ScatterChart>
        ) : null}

        {chartType === 'bar' || !['line', 'pie', 'radar', 'scatter'].includes(chartType) ? (
          <BarChart data={data} margin={{ top: 5, right: 12, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey={xKey} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey={yKey} fill="#FF0000" radius={[4, 4, 0, 0]} />
          </BarChart>
        ) : null}
      </ResponsiveContainer>
    </div>
  )
}
