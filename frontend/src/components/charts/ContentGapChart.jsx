import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer, LabelList } from 'recharts'

const Tip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
        <div style={{ background: '#1a1a1a', border: '1px solid #383838', borderRadius: 8, padding: '10px 14px', fontSize: '0.82rem', maxWidth: 280 }}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>"{d.gap_phrase}"</div>
            <div style={{ color: '#FF4500' }}>Opportunity Score: <strong>{d.opportunity_score}</strong></div>
            <div style={{ color: 'var(--text-muted)' }}>Reddit demand: <strong>{d.demand_count}×</strong></div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 4 }}>
                🔴 Not covered by any YouTube video on this keyword
            </div>
        </div>
    )
}

export default function ContentGapChart({ data }) {
    if (!data || !data.length) {
        return (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 32, fontSize: '0.87rem' }}>
                <div style={{ fontSize: '1.8rem', marginBottom: 8 }}>🔍</div>
                No content gaps detected yet — run the pipeline to generate analysis.
            </div>
        )
    }

    const sorted = [...data].sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0)).slice(0, 8)

    return (
        <div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.81rem', marginBottom: 10 }}>
                🎯 Sub-topics people ask about on Reddit that have no YouTube video coverage — prime content opportunities
            </p>
            <ResponsiveContainer width="100%" height={280}>
                <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 70, bottom: 0, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                    <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="gap_phrase" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false} width={170} />
                    <Tooltip content={<Tip />} />
                    <Bar dataKey="opportunity_score" radius={[0, 4, 4, 0]}>
                        <LabelList dataKey="demand_count" position="right" formatter={v => `${v}× asks`} style={{ fill: 'var(--text-muted)', fontSize: '0.7rem' }} />
                        {sorted.map((_, i) => {
                            const t = i / (sorted.length - 1 || 1)
                            return <Cell key={i} fill={`rgba(255,${Math.round(69 + t * 69)},0, 0.85)`} />
                        })}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    )
}
