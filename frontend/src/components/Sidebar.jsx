export default function Sidebar({ keyword, setKeyword, onRun, status, statusMsg, history, activeKw, onHistoryClick }) {
  const isRunning = status === 'running'

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">🔭</span>
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
        {isRunning ? <><div className="spinner" />Running…</> : '🚀 Run Analysis'}
      </button>

      {status && (
        <div className={`status-box ${status}`}>
          {statusMsg.split('\n').map((line, i) => <div key={i}>{line}</div>)}
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
        PySpark Medallion · Random Forest
      </div>
    </aside>
  )
}
