import { useEffect, useMemo, useRef, useState } from 'react'
import ChatMessage from './ChatMessage.jsx'

const API = import.meta.env.VITE_API_URL || ''
const CHAT_TIMEOUT_MS = 180000

const readError = async res => {
  const text = await res.text()
  try {
    const json = JSON.parse(text)
    return json.detail || text
  } catch (_) {
    return text
  }
}

export default function ChatSidebar({ keyword, data }) {
  const [conversationId, setConversationId] = useState('')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [phase, setPhase] = useState('')
  const [error, setError] = useState('')
  const endRef = useRef(null)

  const canSend = useMemo(() => !!keyword && !loading && input.trim().length > 0, [keyword, loading, input])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (!keyword) return

    const start = async () => {
      setLoading(true)
      setPhase('connecting')
      setError('')
      try {
        const res = await fetch(`${API}/api/chat/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keyword }),
        })

        if (!res.ok) throw new Error(await readError(res))

        const json = await res.json()
        setConversationId(json.conversation_id)
        setMessages([
          {
            role: 'assistant',
            text: `Chat connected for '${keyword}'. Ask for insights, tools, or charts.`,
            charts: [],
            toolEvents: [],
          },
        ])
      } catch (e) {
        setError(e.message || 'Failed to start chat session')
      } finally {
        setLoading(false)
        setPhase('')
      }
    }

    start()
  }, [keyword])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || !conversationId || loading) return

    setInput('')
    setLoading(true)
    setPhase('analyzing')
    setError('')
    setMessages(prev => [...prev, { role: 'user', text, charts: [], toolEvents: [] }])

    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS)

    try {
      const res = await fetch(`${API}/api/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          conversation_id: conversationId,
          keyword,
          message: text,
          dashboard_data: data || null,
        }),
      })

      if (!res.ok) throw new Error(await readError(res))
      const json = await res.json()

      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: json.answer || 'No answer generated',
          charts: Array.isArray(json.charts) ? json.charts : [],
          toolEvents: Array.isArray(json.tool_events) ? json.tool_events : [],
        },
      ])
    } catch (e) {
      setError(e.name === 'AbortError' ? 'Chat request timed out. Check backend agent logs for the last completed step.' : (e.message || 'Chat request failed'))
    } finally {
      window.clearTimeout(timeout)
      setLoading(false)
      setPhase('')
    }
  }

  return (
    <aside className="chat-sidebar">
      <div className="chat-header">
        <div className="chat-title">AI Analyst</div>
        <div className="chat-subtitle">Gemini + Tool Execution</div>
        <div className="chat-keyword">Keyword: {keyword || '—'}</div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <ChatMessage key={idx} message={msg} />
        ))}
        {loading && (
          <div className="chat-thinking">
            {phase === 'connecting' ? 'Connecting chat...' : 'Analyzing and calling tools...'}
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-input-row">
        <input
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && canSend && sendMessage()}
          placeholder={keyword ? 'Ask about trends, sentiment, or ask for a chart...' : 'Run analysis first'}
          disabled={!keyword || loading}
        />
        <button className="chat-send-btn" onClick={sendMessage} disabled={!canSend}>
          Send
        </button>
      </div>
    </aside>
  )
}
