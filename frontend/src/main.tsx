import React, { FormEvent, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

type RunState = {
  run_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | string
  step: string
  progress: number
  run_dir: string | null
  search_results: number
  filtered_urls: number
  extracted_documents: number
  failed_fetches: number
  map_summaries: number
  final_report: string | null
  warnings: string[]
  error: string | null
}

const defaultQuery = 'AI regulation latest developments'

function App() {
  const [query, setQuery] = useState(defaultQuery)
  const [run, setRun] = useState<RunState | null>(null)
  const [report, setReport] = useState('')
  const [error, setError] = useState<string | null>(null)
  const isActive = run?.status === 'queued' || run?.status === 'running'

  async function startRun(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setReport('')
    const response = await fetch('/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })
    if (!response.ok) {
      setError(`Failed to start run: ${response.status}`)
      return
    }
    setRun(await response.json())
  }

  useEffect(() => {
    if (!run || !isActive) return
    const timer = window.setInterval(async () => {
      const response = await fetch(`/runs/${run.run_id}`)
      if (!response.ok) return
      const nextRun: RunState = await response.json()
      setRun(nextRun)
      if (nextRun.status === 'completed') {
        window.clearInterval(timer)
      }
    }, 1500)
    return () => window.clearInterval(timer)
  }, [run?.run_id, isActive])

  useEffect(() => {
    if (run?.status !== 'completed') return
    fetch(`/runs/${run.run_id}/final-report`)
      .then((response) => (response.ok ? response.text() : ''))
      .then(setReport)
      .catch(() => setReport(''))
  }, [run?.run_id, run?.status])

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Local LLM News Research</p>
          <h1>Tsuzuri turns noisy search results into cited briefings.</h1>
          <p className="lede">
            Launch a research run, watch the pipeline progress, and review the final Markdown report.
          </p>
        </div>
        <div className="status-card">
          <span className="pulse" />
          <strong>API ready</strong>
          <small>Search, fetch, summarize, upload</small>
        </div>
      </section>

      <form className="run-form" onSubmit={startRun}>
        <label htmlFor="query">Research query</label>
        <div className="query-row">
          <input
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What should Tsuzuri research?"
          />
          <button disabled={isActive || query.trim().length === 0} type="submit">
            {isActive ? 'Running...' : 'Run Research'}
          </button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}

      {run && <ProgressPanel run={run} />}
      {report && <ReportPanel markdown={report} />}
    </main>
  )
}

function ProgressPanel({ run }: { run: RunState }) {
  const metrics = [
    ['Search results', run.search_results],
    ['Filtered URLs', run.filtered_urls],
    ['Extracted docs', run.extracted_documents],
    ['Failed fetches', run.failed_fetches],
    ['Map summaries', run.map_summaries],
  ]

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Run {run.run_id}</p>
          <h2>{run.step}</h2>
        </div>
        <span className={`badge ${run.status}`}>{run.status}</span>
      </div>
      <div className="progress-track">
        <div className="progress-bar" style={{ width: `${Math.max(0, Math.min(100, run.progress))}%` }} />
      </div>
      <div className="metrics">
        {metrics.map(([label, value]) => (
          <div className="metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      {run.final_report && <p className="artifact">Final report: {run.final_report}</p>}
      {run.error && <p className="error">{run.error}</p>}
      {run.warnings.length > 0 && (
        <div className="warnings">
          <strong>Warnings</strong>
          {run.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}
    </section>
  )
}

function ReportPanel({ markdown }: { markdown: string }) {
  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Generated Markdown</p>
          <h2>Final Briefing</h2>
        </div>
      </div>
      <pre className="report">{markdown}</pre>
    </section>
  )
}

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
