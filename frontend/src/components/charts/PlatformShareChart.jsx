import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = { YouTube: '#ff4444', Reddit: '#ff6314' }

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
        <ResponsiveContainer width="100%" height={240}>
            <PieChart>
                <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                    <Cell fill={COLORS.YouTube} />
                    <Cell fill={COLORS.Reddit} />
                </Pie>
                <Tooltip formatter={v => v.toLocaleString()} />
                <Legend />
            </PieChart>
        </ResponsiveContainer>
    )
}
