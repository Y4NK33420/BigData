import { useState, useCallback, useRef, useEffect } from 'react'
import axios from 'axios'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './components/Dashboard.jsx'
import Welcome from './components/Welcome.jsx'
import ChatSidebar from './components/ChatSidebar.jsx'

const API = import.meta.env.VITE_API_URL || ''
const POLL_INTERVAL_MS = 2000  // poll every 2 seconds while job is running

export default function App() {
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState(null)   // null | 'running' | 'done' | 'failed'
  const [step, setStep] = useState('')
  const [logs, setLogs] = useState([])
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [activeKw, setActiveKw] = useState('')
  const pollRef = useRef(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), [])

  const fetchData = useCallback(async (target) => {
    const res = await axios.get(`${API}/api/data`, { params: { keyword: target } })
    setData(res.data)
    setActiveKw(target)
    if (!history.includes(target)) setHistory(prev => [target, ...prev].slice(0, 10))
  }, [history])

  const runPipeline = useCallback(async (kw) => {
    const target = (kw || keyword).trim()
    if (!target) return
    stopPolling()
    setStatus('running')
    setStep('queued')
    setLogs(['▶ Starting pipeline…'])
    setData(null)

    let jobId
    try {
      const res = await axios.post(`${API}/api/pipeline/run`, { keyword: target })
      jobId = res.data.job_id

      // If already running (returned existing job), pick up from there
      if (res.data.status === 'done') {
        await fetchData(target)
        setStatus('done')
        return
      }
    } catch (err) {
      setStatus('failed')
      setLogs(prev => [...prev, `❌ ${err.response?.data?.detail || err.message}`])
      return
    }

    // Poll for status
    pollRef.current = setInterval(async () => {
      try {
        const statusRes = await axios.get(`${API}/api/pipeline/status/${jobId}`)
        const job = statusRes.data
        setStep(job.step || '')
        setLogs(job.logs || [])

        if (job.status === 'done') {
          stopPolling()
          setStatus('done')
          try { await fetchData(target) } catch (_) { }
        } else if (job.status === 'failed') {
          stopPolling()
          setStatus('failed')
          setLogs(prev => [...prev, `❌ Error: ${job.error || 'Unknown failure'}`])
        }
      } catch (err) {
        stopPolling()
        setStatus('failed')
        setLogs(prev => [...prev, `❌ Polling error: ${err.message}`])
      }
    }, POLL_INTERVAL_MS)
  }, [keyword, history, fetchData])

  const loadKeyword = useCallback(async (kw) => {
    stopPolling()
    setActiveKw(kw)
    setStatus('running')
    setStep('')
    setLogs(['📂 Loading saved results…'])
    try {
      const res = await axios.get(`${API}/api/data`, { params: { keyword: kw } })
      setData(res.data)
      setStatus('done')
      setLogs(['✅ Loaded from cache!'])
    } catch (err) {
      setStatus('failed')
      setLogs([`❌ ${err.response?.data?.detail || err.message}`])
    }
  }, [])

  return (
    <div className={`layout ${data ? 'layout-with-chat' : ''}`}>
      <Sidebar
        keyword={keyword}
        setKeyword={setKeyword}
        onRun={() => runPipeline()}
        status={status}
        step={step}
        logs={logs}
        history={history}
        activeKw={activeKw}
        onHistoryClick={loadKeyword}
      />
      <main className="main">
        {data
          ? <Dashboard data={data} />
          : <Welcome />
        }
      </main>
      {data && (
        <ChatSidebar keyword={activeKw || data.keyword || keyword} data={data} />
      )}
    </div>
  )
}
