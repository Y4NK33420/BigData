import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts'

export default function TopicViabilityRadar({ topicRecs }) {
    const metrics = {
        growth_velocity: 'Growth Velocity',
        engagement_quality: 'Eng. Quality',
        yt_comment_sentiment: 'YT Comment Sent.',
        reddit_sentiment: 'Reddit Sentiment',
        saturation_penalty: 'Low Saturation',
    }

    const data = Object.entries(metrics).map(([key, label]) => {
        const row = (topicRecs || []).find(r => r.metric === key)
        return { metric: label, score: row ? parseFloat((row.raw_score || 0).toFixed(1)) : 0 }
    })

    if (!data.length) return <p style={{ color: 'var(--muted)', textAlign: 'center', paddingTop: 40 }}>Run pipeline to see viability scores.</p>

    return (
        <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={data}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                <PolarRadiusAxis domain={[0, 100]} tick={{ fill: 'var(--muted)', fontSize: 9 }} />
                <Radar name="Viability" dataKey="score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.35} />
                <Tooltip contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8 }} labelStyle={{ color: 'var(--text)' }} formatter={v => [`${v}/100`]} />
                <Legend />
            </RadarChart>
        </ResponsiveContainer>
    )
}
