import { useRef, useEffect } from 'react'

const STEP_LABELS = {
  queued: '⏳ Queued',
  ingest: '📡 Fetching data…',
  process: '⚡ PySpark processing…',
  complete: '✅ Complete',
}

export default function Sidebar({ keyword, setKeyword, onRun, status, step, logs, history, activeKw, onHistoryClick }) {
  const isRunning = status === 'running'
  const logEndRef = useRef(null)

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">▶</span>
        <h1>BigD Analytics</h1>
      </div>

      <div className="sidebar-section">Keyword</div>
      <input
        className="sidebar-input"
        type="text"
        placeholder="e.g. artificial intelligence"
        value={keyword}
        onChange={e => setKeyword(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && !isRunning && onRun()}
      />
      <button className="run-btn" onClick={onRun} disabled={isRunning || !keyword.trim()}>
        {isRunning ? <><div className="spinner" />{STEP_LABELS[step] || 'Running…'}</> : '🚀 Run Analysis'}
      </button>

      {/* Live pipeline log output */}
      {logs.length > 0 && (
        <div className="pipeline-log">
          {logs.map((line, i) => (
            <div key={i} className={`log-line ${line.startsWith('❌') ? 'log-error' : line.startsWith('✅') || line.startsWith('🎉') ? 'log-success' : ''}`}>
              {line}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      )}

      {history.length > 0 && (
        <div className="sidebar-history">
          <div className="sidebar-section" style={{ marginBottom: 10 }}>Recent</div>
          {history.map(kw => (
            <div
              key={kw}
              className={`history-item ${kw === activeKw ? 'active' : ''}`}
              onClick={() => onHistoryClick(kw)}
            >
              <span className="history-dot" />
              {kw}
            </div>
          ))}
        </div>
      )}

      <div className="sidebar-footer">
        YouTube API · Reddit Scraper<br />
        PySpark Medallion · Random Forest<br />
        <span style={{ color: 'var(--accent)', fontSize: '0.7rem' }}>✦ Gemini AI</span>
      </div>
    </aside>
  )
}
