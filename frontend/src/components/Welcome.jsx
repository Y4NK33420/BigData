export default function Welcome() {
  return (
    <div className="welcome">
      <div className="welcome-panel welcome-panel-single">
        <section className="welcome-hero">
          <div className="welcome-icon">⌁</div>
          <h2>Run a keyword to open the analytics workspace.</h2>

          <div className="pipeline-row">
            {[
              ['YouTube', 'videos and stats'],
              ['Reddit', 'posts and demand'],
              ['Bronze', 'raw ingestion'],
              ['Gold', 'analytics outputs'],
              ['RF Model', 'predicted views'],
            ].map(([name, sub], i, arr) => ([
              <div key={name} className="pipeline-node">
                <div className="name">{name}</div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.74rem' }}>{sub}</div>
              </div>,
              i < arr.length - 1 ? <span key={`a${i}`} className="pipeline-arrow">→</span> : null,
            ]))}
          </div>
        </section>
      </div>
    </div>
  )
}
