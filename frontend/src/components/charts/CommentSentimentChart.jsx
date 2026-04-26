import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function CommentSentimentChart({ topVideos }) {
    const data = (topVideos || [])
        .filter(v => v.title)
        .map((v, i) => ({
            name: `${i + 1}. ${(v.title || '').substring(0, 22)}…`,
            comment_sentiment: parseFloat((v.comment_sentiment || 0).toFixed(3)),
            title_sentiment: parseFloat((v.sentiment_score || 0).toFixed(3)),
        }))
        .slice(0, 10)

    const getColor = score => score >= 0.05 ? 'var(--green)' : score <= -0.05 ? 'var(--red)' : 'var(--gold)'

    return (
        <ResponsiveContainer width="100%" height={320}>
            <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 165 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" domain={[-1, 1]} tickFormatter={v => v.toFixed(1)} tick={{ fill: 'var(--text-muted)' }} stroke="var(--border)" fontSize={11} />
                <YAxis type="category" dataKey="name" stroke="var(--border)" tick={{ fill: 'var(--text-muted)' }} fontSize={10} width={160} />
                <Tooltip
                    formatter={(v, name) => [v.toFixed(3), name === 'comment_sentiment' ? 'Comment Sentiment' : 'Title Sentiment']}
                    contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 8 }}
                    labelStyle={{ color: 'var(--text)' }}
                />
                <Bar dataKey="comment_sentiment" radius={[0, 4, 4, 0]}>
                    {data.map((entry, i) => <Cell key={i} fill={getColor(entry.comment_sentiment)} />)}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    )
}
