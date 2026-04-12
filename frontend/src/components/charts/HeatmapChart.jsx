import { useMemo } from 'react'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
// day_of_week in process.py: 1=Sun,2=Mon,...7=Sat
const DAY_MAP = { 1:'Sun',2:'Mon',3:'Tue',4:'Wed',5:'Thu',6:'Fri',7:'Sat' }
const HOURS = Array.from({ length: 24 }, (_, i) => i)

export default function HeatmapChart({ data }) {
  const grid = useMemo(() => {
    const map = {}
    data.forEach(r => {
      const day = DAY_MAP[r.day_of_week] || '?'
      const key = `${day}-${r.upload_hour}`
      map[key] = r.avg_views || 0
    })
    const vals = Object.values(map)
    const maxV = Math.max(...vals, 1)
    return { map, maxV }
  }, [data])

  if (!data.length) return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Not enough data for heatmap — try a broader keyword.</div>

  const fmt = n => n >= 1e6 ? `${(n/1e6).toFixed(1)}M` : n >= 1e3 ? `${(n/1e3).toFixed(0)}K` : String(Math.round(n))

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `60px repeat(24, 1fr)`, gap: 2, minWidth: 700 }}>
        {/* Header row */}
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 6 }}>Day</div>
        {HOURS.map(h => (
          <div key={h} style={{ fontSize: '0.62rem', color: 'var(--text-muted)', textAlign: 'center' }}>{String(h).padStart(2,'0')}</div>
        ))}
        {/* Data rows */}
        {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(day => (
          <>
            <div key={day} style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 8 }}>{day}</div>
            {HOURS.map(h => {
              const v = grid.map[`${day}-${h}`] || 0
              const intensity = v / grid.maxV
              const alpha = 0.08 + intensity * 0.9
              return (
                <div
                  key={h}
                  title={`${day} ${String(h).padStart(2,'0')}:00 — Avg Views: ${fmt(v)}`}
                  style={{
                    height: 28, borderRadius: 3,
                    background: `rgba(${intensity > 0.5 ? '232,121,249' : '99,102,241'}, ${alpha})`,
                    transition: 'transform 0.1s',
                    cursor: 'default',
                  }}
                />
              )
            })}
          </>
        ))}
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 12, fontSize: '0.72rem', color: 'var(--text-muted)', alignItems: 'center' }}>
        <span>Low</span>
        {[0.1,0.3,0.5,0.7,0.9].map(t => (
          <div key={t} style={{ width: 20, height: 10, borderRadius: 2, background: `rgba(${t>0.5?'232,121,249':'99,102,241'}, ${0.08+t*0.9})` }} />
        ))}
        <span>High views</span>
      </div>
    </div>
  )
}
