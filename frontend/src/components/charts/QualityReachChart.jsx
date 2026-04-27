import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Label, ReferenceLine } from 'recharts'

const fmt = n => n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? (n / 1e3).toFixed(1) + 'K' : n

export default function QualityReachChart({ topVideos }) {
    const data = (topVideos || []).map(v => ({
        x: v.view_count || 0,
        y: parseFloat((v.like_to_view_ratio || 0).toFixed(4)),
        name: (v.title || '').substring(0, 40),
    }))

    const avgY = data.length ? data.reduce((s, d) => s + d.y, 0) / data.length : 0

    const CustomTooltip = ({ active, payload }) => {
        if (!active || !payload?.length) return null
        const d = payload[0]?.payload
        return (
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', maxWidth: 260 }}>
                <p style={{ color: 'var(--text)', fontSize: 11, marginBottom: 4 }}>{d.name}</p>
                <p style={{ color: 'var(--accent)', fontSize: 12 }}>Views: {fmt(d.x)}</p>
                <p style={{ color: 'var(--green)', fontSize: 12 }}>Like/View: {(d.y * 100).toFixed(2)}%</p>
            </div>
        )
    }

    return (
        <div>
            <p style={{ color: 'var(--muted)', fontSize: 11, marginBottom: 8 }}>
                Top-right = "Hidden Gems" (high quality, lower reach) · Bottom-right = "Clickbait" (high views, low quality)
            </p>
            <ResponsiveContainer width="100%" height={280}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="x" type="number" tickFormatter={fmt} stroke="var(--muted)" fontSize={11}>
                        <Label value="View Count" offset={-10} position="insideBottom" fill="var(--muted)" fontSize={11} />
                    </XAxis>
                    <YAxis dataKey="y" type="number" stroke="var(--muted)" fontSize={11} tickFormatter={v => `${(v * 100).toFixed(1)}%`}>
                        <Label value="Like/View Ratio" angle={-90} position="insideLeft" fill="var(--muted)" fontSize={11} />
                    </YAxis>
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine y={avgY} stroke="var(--gold)" strokeDasharray="4 4" label={{ value: 'Avg Quality', fill: 'var(--gold)', fontSize: 10 }} />
                    <Scatter data={data} fill="var(--accent)" fillOpacity={0.75} />
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    )
}
