import ChatChartRenderer from './ChatChartRenderer.jsx'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const charts = Array.isArray(message.charts) ? message.charts : []
  const toolEvents = Array.isArray(message.toolEvents) ? message.toolEvents : []

  return (
    <div className={`chat-msg ${isUser ? 'user' : 'assistant'}`}>
      <div className="chat-avatar">{isUser ? 'U' : 'AI'}</div>
      <div className="chat-bubble">
        <div className="chat-text markdown-text">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.text || ''}
          </ReactMarkdown>
        </div>

        {toolEvents.length > 0 && (
          <div className="chat-tools-wrap">
            {toolEvents.map((ev, idx) => (
              <div key={idx} className={`chat-tool-chip ${ev.ok ? 'ok' : 'err'}`}>
                {ev.ok ? 'OK' : 'ERR'} {ev.tool_name}: {ev.summary}
              </div>
            ))}
          </div>
        )}

        {charts.map((chart, idx) => (
          <ChatChartRenderer key={idx} chart={chart} />
        ))}
      </div>
    </div>
  )
}
