import { useState, useCallback } from 'react'
import axios from 'axios'
import Sidebar from './components/Sidebar.jsx'
import Dashboard from './components/Dashboard.jsx'
import Welcome from './components/Welcome.jsx'

const API = import.meta.env.VITE_API_URL || ''

export default function App() {
  const [keyword, setKeyword]   = useState('')
  const [status, setStatus]     = useState(null)   // null | 'running' | 'success' | 'error'
  const [statusMsg, setStatusMsg] = useState('')
  const [data, setData]         = useState(null)
  const [history, setHistory]   = useState([])
  const [activeKw, setActiveKw] = useState('')

  const runPipeline = useCallback(async (kw) => {
    const target = (kw || keyword).trim()
    if (!target) return
    setStatus('running')
    setStatusMsg('🎬 Querying YouTube API …\n💬 Scraping Reddit …')
    setData(null)

    try {
      await axios.post(`${API}/api/pipeline/run`, { keyword: target })
      setStatusMsg('📊 Processing with PySpark …')
      const res = await axios.get(`${API}/api/data`, { params: { keyword: target } })
      setData(res.data)
      setActiveKw(target)
      setStatus('success')
      setStatusMsg('✅ Pipeline complete!')
      if (!history.includes(target)) setHistory(prev => [target, ...prev].slice(0, 10))
    } catch (err) {
      setStatus('error')
      const detail = err.response?.data?.detail || err.message
      setStatusMsg(`❌ ${detail}`)
    }
  }, [keyword, history])

  const loadKeyword = useCallback(async (kw) => {
    setActiveKw(kw)
    setStatus('running')
    setStatusMsg('Loading cached results …')
    try {
      const res = await axios.get(`${API}/api/data`, { params: { keyword: kw } })
      setData(res.data)
      setStatus('success')
      setStatusMsg('✅ Loaded!')
    } catch (err) {
      setStatus('error')
      setStatusMsg(`❌ ${err.response?.data?.detail || err.message}`)
    }
  }, [])

  return (
    <div className="layout">
      <Sidebar
        keyword={keyword}
        setKeyword={setKeyword}
        onRun={() => runPipeline()}
        status={status}
        statusMsg={statusMsg}
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
    </div>
  )
}
