export default function Welcome() {
  return (
    <div className="welcome">
      <div className="welcome-icon">🔭</div>
      <h2>Ready to Explore</h2>
      <p>Enter a keyword in the sidebar and click <strong style={{ color: '#a78bfa' }}>Run Analysis</strong> to start the full Medallion pipeline.</p>

      <div className="pipeline-row">
        {[
          ['🎬', 'YouTube', 'Videos & stats'],
          ['💬', 'Reddit',  'Posts & sentiment'],
          ['🥉', 'Bronze',  'Raw JSON'],
          ['🥈', 'Silver',  'Cleaned Parquet'],
          ['🥇', 'Gold',    'Analytics tables'],
          ['🤖', 'RF Model', 'View predictions'],
        ].map(([icon, name, sub], i, arr) => (
          <>
            <div key={name} className="pipeline-node">
              <div className="icon">{icon}</div>
              <div className="name">{name}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{sub}</div>
            </div>
            {i < arr.length - 1 && <span key={`a${i}`} className="pipeline-arrow">→</span>}
          </>
        ))}
      </div>
    </div>
  )
}
