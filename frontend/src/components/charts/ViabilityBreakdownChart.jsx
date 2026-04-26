import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts'

export default function ViabilityBreakdownChart({ topicRecs }) {
    const metrics = {
        growth_velocity: 'Growth Velocity',
        engagement_quality: 'Engagement Quality',
        yt_comment_sentiment: 'YT Comment Sentiment',
        reddit_sentiment: 'Reddit Sentiment',
        saturation_penalty: 'Low Saturation',
    }

    const data = Object.entries(metrics).map(([key, label]) => {
        const row = (topicRecs || []).find(r => r.metric === key)
        return {
            metric: label,
            score: row ? parseFloat((row.raw_score || 0).toFixed(1)) : 0,
            note: row?.note || '',
        }
    }).filter(d => d.score > 0)

    const getColor = score => score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--gold)' : 'var(--red)'

    const CustomTooltip = ({ active, payload }) => {
        if (!active || !payload?.length) return null
        const d = payload[0]?.payload
        return (
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', maxWidth: 280 }}>
                <p style={{ color: 'var(--text)', fontWeight: 600, marginBottom: 4 }}>{d.metric}: {d.score}/100</p>
                <p style={{ color: 'var(--muted)', fontSize: 11 }}>{d.note}</p>
            </div>
        )
    }

    return (
        <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="metric" stroke="var(--border)" fontSize={10} tick={{ fill: 'var(--text-muted)', angle: -15, textAnchor: 'end' }} />
                <YAxis domain={[0, 100]} stroke="var(--border)" fontSize={11} tick={{ fill: 'var(--text-muted)' }} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={50} stroke="var(--muted)" strokeDasharray="4 4" />
                <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                    {data.map((entry, i) => <Cell key={i} fill={getColor(entry.score)} />)}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    )
}
