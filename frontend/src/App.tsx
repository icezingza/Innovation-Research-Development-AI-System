import { useState, useCallback, useEffect, useRef } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, PolarAngleAxis,
  BarChart, Bar, Cell,
} from 'recharts'
import { api, type HealthStatus, type RedTeamReport, type ComplexityResult } from './api'
import './index.css'

// ─── Types ─────────────────────────────────────────────────────────────────
type Page = 'dashboard' | 'redteam' | 'complexity' | 'selfheal' | 'rag' | 'debate' | 'finops'

interface LogEntry { ts: string; level: 'info' | 'warn' | 'error' | 'success'; msg: string }

// ─── Sidebar Nav ────────────────────────────────────────────────────────────
const NAV = [
  { id: 'dashboard' as Page, icon: '⬡', label: 'Command Center' },
  { id: 'debate' as Page, icon: '⚔️', label: 'Live Debate' },
  { id: 'finops' as Page, icon: '💰', label: 'FinOps' },
  { id: 'complexity' as Page, icon: '🧠', label: 'Adaptive Reasoning' },
  { id: 'redteam' as Page, icon: '🥷', label: 'Red Team' },
  { id: 'selfheal' as Page, icon: '🛡️', label: 'Self-Healing' },
  { id: 'rag' as Page, icon: '📚', label: 'RAG Corpus' },
]

// ─── Helpers ────────────────────────────────────────────────────────────────
function ts(): string {
  return new Date().toLocaleTimeString('en-US', { hour12: false })
}

// ─── Dashboard Page ─────────────────────────────────────────────────────────
function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)

  // Simulated throughput data for chart
  const [throughputData] = useState(() =>
    Array.from({ length: 20 }, (_, i) => ({
      t: `${i}s`,
      req: Math.floor(Math.random() * 80 + 10),
      blocked: Math.floor(Math.random() * 40),
    }))
  )

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false))
  }, [])

  const statusColor = health?.status === 'ok' ? 'green' : 'red'

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Command Center</h1>
        <p className="page-subtitle">NamoNexus AI System — Real-time health overview</p>
      </div>

      <div className="stats-grid">
        {[
          { label: 'System Status', value: loading ? '...' : (health ? '● ONLINE' : '✕ OFFLINE'), cls: statusColor },
          { label: 'API Version', value: health?.version ?? 'N/A', cls: 'cyan' },
          { label: 'Req/sec (Peak)', value: '14.3', cls: 'primary' },
          { label: 'Block Rate', value: '97%', cls: 'green' },
        ].map(({ label, value, cls }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className={`stat-value ${cls}`}>{value}</div>
          </div>
        ))}
      </div>

      <div className="charts-grid">
        <div className="card chart-full">
          <div className="card-header">
            <span className="card-title">Request Throughput (Simulated)</span>
            <span className="badge badge-green">● Live</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={throughputData}>
              <defs>
                <linearGradient id="gradReq" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradBlocked" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d4a" />
              <XAxis dataKey="t" stroke="#475569" fontSize={11} />
              <YAxis stroke="#475569" fontSize={11} />
              <Tooltip contentStyle={{ background: '#121828', border: '1px solid #1f2d4a', borderRadius: 8 }} />
              <Area type="monotone" dataKey="req" stroke="#6366f1" fill="url(#gradReq)" strokeWidth={2} name="Requests" />
              <Area type="monotone" dataKey="blocked" stroke="#ef4444" fill="url(#gradBlocked)" strokeWidth={2} name="Blocked" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Services</span></div>
          <table className="data-table">
            <thead><tr><th>Service</th><th>Status</th></tr></thead>
            <tbody>
              {[
                ['FastAPI', 'RUNNING'],
                ['SQLite (fallback)', 'ACTIVE'],
                ['Qdrant', 'DEGRADED'],
                ['Neo4j', 'DEGRADED'],
                ['Redis', 'DEGRADED'],
                ['Jaeger/OTLP', 'DEGRADED'],
              ].map(([svc, st]) => (
                <tr key={svc}>
                  <td>{svc}</td>
                  <td>
                    <span className={`badge ${st === 'RUNNING' || st === 'ACTIVE' ? 'badge-green' : 'badge-amber'}`}>
                      {st}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Middleware Stack</span></div>
          {[
            { name: 'SecurityMiddleware', load: 12 },
            { name: 'TenantMiddleware', load: 18 },
            { name: 'RateLimitMiddleware', load: 72 },
            { name: 'QuotaMiddleware', load: 45 },
          ].map(({ name, load }) => (
            <div key={name} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{load}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${load}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ─── Adaptive Reasoning Page ────────────────────────────────────────────────
function ComplexityPage() {
  const [task, setTask] = useState('')
  const [result, setResult] = useState<ComplexityResult | null>(null)
  const [loading, setLoading] = useState(false)

  const strategyColor: Record<string, string> = {
    bayesian_debate: 'red',
    chain_of_thought: 'amber',
    heuristic: 'green',
  }

  async function evaluate() {
    if (!task.trim()) return
    setLoading(true)
    try {
      setResult(await api.complexity(task))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const gaugeData = result ? [{ value: result.complexity_score * 10 }] : [{ value: 0 }]

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">🧠 Adaptive Reasoning</h1>
        <p className="page-subtitle">Evaluate task complexity and auto-select optimal reasoning strategy</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">Task Complexity Evaluator</span></div>
        <textarea
          value={task}
          onChange={e => setTask(e.target.value)}
          placeholder="Paste your research task or query here..."
          style={{
            width: '100%', minHeight: 120, background: '#030508', border: '1px solid var(--border)',
            borderRadius: 8, padding: 14, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem', resize: 'vertical', outline: 'none', lineHeight: 1.6
          }}
        />
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-primary" onClick={evaluate} disabled={loading || !task.trim()}>
            {loading ? <><span className="spinner" /> Analyzing...</> : '⚡ Evaluate Complexity'}
          </button>
        </div>
      </div>

      {result && (
        <div className="charts-grid">
          <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div className="card-header" style={{ width: '100%' }}>
              <span className="card-title">Complexity Score</span>
              <span className={`badge badge-${strategyColor[result.strategy] ?? 'cyan'}`}>{result.strategy}</span>
            </div>
            <ResponsiveContainer width={200} height={200}>
              <RadialBarChart cx="50%" cy="50%" innerRadius={60} outerRadius={90} data={gaugeData} startAngle={90} endAngle={-270}>
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar dataKey="value" cornerRadius={8} fill="#6366f1" />
              </RadialBarChart>
            </ResponsiveContainer>
            <div style={{ fontSize: '3rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--primary-glow)', marginTop: -16 }}>
              {result.complexity_score}/10
            </div>
          </div>

          <div className="card">
            <div className="card-header"><span className="card-title">Resource Allocation</span></div>
            <table className="data-table">
              <tbody>
                {[
                  ['Inference Tier', result.inference_tier],
                  ['Agents Required', String(result.agents_required)],
                  ['Allocated Tokens', result.allocated_tokens.toLocaleString()],
                  ['Strategy', result.strategy],
                ].map(([k, v]) => (
                  <tr key={k}><td style={{ color: 'var(--text-muted)' }}>{k}</td><td>{v}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

// ─── Red Team Page ───────────────────────────────────────────────────────────
function RedTeamPage() {
  const [rounds, setRounds] = useState(6)
  const [report, setReport] = useState<RedTeamReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [log, setLog] = useState<LogEntry[]>([])

  function addLog(level: LogEntry['level'], msg: string) {
    setLog(prev => [...prev, { ts: ts(), level, msg }])
  }

  async function runAttack() {
    setLoading(true)
    setReport(null)
    setLog([])
    addLog('info', `Red Team session starting — ${rounds} attack rounds`)
    try {
      addLog('warn', 'Spawning adversarial prompt corpus...')
      const r = await api.redTeam(rounds)
      setReport(r)
      addLog('success', `Session complete: ${r.block_rate_pct}% block rate`)
      addLog(r.verdict === 'FORTRESS_SOLID' ? 'success' : 'warn', `Verdict: ${r.verdict}`)
    } catch (e) {
      addLog('error', `Attack failed: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  const barData = report
    ? Object.entries(report.category_breakdown).map(([cat, d]) => ({
        cat: cat.replace('_', ' '),
        blocked: d.blocked,
        passed: d.total - d.blocked,
      }))
    : []

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">🥷 Red Team Attack Simulation</h1>
        <p className="page-subtitle">Autonomous adversarial probing — exercises guardrails and feeds Self-Healing</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Attack Configuration</span>
          {report && (
            <span className={`badge ${report.verdict === 'FORTRESS_SOLID' ? 'badge-green' : 'badge-red'}`}>
              {report.verdict === 'FORTRESS_SOLID' ? '🛡 FORTRESS SOLID' : '⚠ NEEDS REINFORCEMENT'}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <label style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            Attack Rounds: <strong style={{ color: 'var(--accent-amber)' }}>{rounds}</strong>
          </label>
          <input type="range" min={1} max={12} value={rounds} onChange={e => setRounds(Number(e.target.value))}
            style={{ accentColor: 'var(--primary)' }} />
          <button className="btn btn-danger" onClick={runAttack} disabled={loading}>
            {loading ? <><span className="spinner" /> Attacking...</> : '💀 Launch Attack'}
          </button>
        </div>
      </div>

      <div className="charts-grid">
        <div className="card">
          <div className="card-header"><span className="card-title">Attack Log</span></div>
          <div className="log-terminal">
            {log.length === 0 && <span style={{ color: 'var(--text-muted)' }}>$ Waiting for attack session...</span>}
            {log.map((l, i) => (
              <div key={i}>
                <span className="log-timestamp">[{l.ts}] </span>
                <span className={`log-${l.level}`}>{l.msg}</span>
              </div>
            ))}
          </div>
        </div>

        {report && (
          <div className="card">
            <div className="card-header"><span className="card-title">Results by Category</span></div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2d4a" horizontal={false} />
                <XAxis type="number" stroke="#475569" fontSize={11} />
                <YAxis dataKey="cat" type="category" stroke="#475569" fontSize={10} width={90} />
                <Tooltip contentStyle={{ background: '#121828', border: '1px solid #1f2d4a', borderRadius: 8 }} />
                <Bar dataKey="blocked" stackId="a" fill="#10b981" name="Blocked" />
                <Bar dataKey="passed" stackId="a" fill="#ef4444" name="Passed" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {report && (
          <div className="card chart-full">
            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4,1fr)', gap: 12, margin: 0 }}>
              {[
                { label: 'Total Attacks', value: report.total_attacks, cls: 'cyan' },
                { label: 'Blocked', value: report.blocked, cls: 'green' },
                { label: 'Passed Through', value: report.passed_through, cls: 'red' },
                { label: 'Block Rate', value: `${report.block_rate_pct}%`, cls: 'primary' },
              ].map(({ label, value, cls }) => (
                <div key={label} style={{ textAlign: 'center' }}>
                  <div className="stat-label">{label}</div>
                  <div className={`stat-value ${cls}`} style={{ fontSize: '1.5rem' }}>{value}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}

// ─── Self-Healing Page ───────────────────────────────────────────────────────
function SelfHealPage() {
  const [eventType, setEventType] = useState('guardrail_violation')
  const [result, setResult] = useState<string | null>(null)
  const [rules, setRules] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  async function fireEvent() {
    setLoading(true)
    try {
      const r = await api.selfHeal(eventType, { agent_id: 'global', violation_type: 'pii' })
      setResult(JSON.stringify(r.patch_applied, null, 2))
      await loadRules()
    } catch (e) {
      setResult(String(e))
    } finally { setLoading(false) }
  }

  async function loadRules() {
    try {
      const r = await api.healingRules()
      setRules(r.active_rules)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadRules() }, [])

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">🛡️ Self-Healing Optimizer</h1>
        <p className="page-subtitle">Inject failure events and observe autonomous prompt/weight patches</p>
      </div>

      <div className="charts-grid">
        <div className="card">
          <div className="card-header"><span className="card-title">Ingest Failure Event</span></div>
          <select
            value={eventType}
            onChange={e => setEventType(e.target.value)}
            style={{
              width: '100%', padding: '10px 14px', background: '#030508', border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)', fontSize: '0.875rem', marginBottom: 16, outline: 'none'
            }}
          >
            {['guardrail_violation', 'hallucination_detected', 'circuit_breaker_tripped'].map(e => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
          <button className="btn btn-primary" onClick={fireEvent} disabled={loading}>
            {loading ? <><span className="spinner" /> Applying...</> : '⚡ Trigger Self-Healing'}
          </button>

          {result && (
            <pre style={{
              marginTop: 16, background: '#030508', border: '1px solid var(--border)', borderRadius: 8,
              padding: 14, fontSize: '0.75rem', color: 'var(--accent-green)', overflowX: 'auto', lineHeight: 1.6
            }}>
              {result}
            </pre>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Active Optimization Rules</span>
            <span className="badge badge-purple">{rules.length} rules</span>
          </div>
          {rules.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No rules yet. Trigger a failure event to generate patches.</p>
          ) : (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {rules.map((r: any, i) => {
                const rule = r
                return (
                  <div key={i} style={{ marginBottom: 12, padding: 12, background: '#030508', borderRadius: 8, border: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                        {String(rule.patch_id ?? '').slice(0, 12)}...
                      </span>
                      <span className="badge badge-green">{String(rule.status ?? '')}</span>
                    </div>
                    {rule.prompt_injection && (
                      <p style={{ fontSize: '0.75rem', color: 'var(--accent-amber)' }}>
                        💉 {String(rule.prompt_injection)}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

// ─── RAG Corpus Page ─────────────────────────────────────────────────────────
function RAGPage() {
  const [corpus, setCorpus] = useState('dhamma-corpus-v1')
  const [domain, setDomain] = useState('dhamma')
  const [text, setText] = useState('')
  const [tokens, setTokens] = useState({ min: 100, max: 150, overlap: 20 })
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  async function ingest() {
    if (!text.trim()) return
    setLoading(true)
    try {
      const res = await api.ragIngest(corpus, text, {
        domain,
        min_tokens: tokens.min,
        max_tokens: tokens.max,
        overlap_tokens: tokens.overlap
      })
      setResult(res)
    } catch (e) { setResult({ error: String(e) }) }
    finally { setLoading(false) }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">📚 RAG Corpus Ingestor</h1>
        <p className="page-subtitle">Short Chunk Strategy — 100–150 tokens max, 20-token overlap for zero-hallucination recall</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <span className="card-title">Corpus Configuration</span>
          <span className="badge badge-purple">NRE v5.0.0 Sovereign Standard</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <div>
            <label className="stat-label">Corpus ID</label>
            <input value={corpus} onChange={e => setCorpus(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="stat-label">Domain</label>
            <select value={domain} onChange={e => setDomain(e.target.value)} className="input-field">
              <option value="dhamma">Dhamma (Abhidhamma)</option>
              <option value="law">Legal / Compliance</option>
              <option value="science">Scientific Research</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 }}>
          {[
            { label: 'Min Tokens', key: 'min', val: tokens.min },
            { label: 'Max Tokens', key: 'max', val: tokens.max },
            { label: 'Overlap', key: 'overlap', val: tokens.overlap },
          ].map(({ label, key, val }) => (
            <div key={key}>
              <label className="stat-label">{label}</label>
              <input type="number" value={val} onChange={e => setTokens({ ...tokens, [key]: Number(e.target.value) })} className="input-field" />
            </div>
          ))}
        </div>

        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste document text here (Dhamma, legal corpus, research papers)..."
          style={{
            width: '100%', minHeight: 180, background: '#030508', border: '1px solid var(--border)',
            borderRadius: 8, padding: 14, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem', resize: 'vertical', outline: 'none', lineHeight: 1.6, marginBottom: 12
          }}
        />
        <button className="btn btn-primary" onClick={ingest} disabled={loading || !text.trim()}>
          {loading ? <><span className="spinner" /> Embedding...</> : '⚡ Ingest to Specialized Memory'}
        </button>
      </div>

      {result && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Ingestion Summary</span>
            <span className={`badge ${result.error ? 'badge-red' : 'badge-green'}`}>
              {result.error ? 'FAILED' : 'SUCCESS'}
            </span>
          </div>
          {result.error ? (
            <p className="log-error">{result.error}</p>
          ) : (
            <div style={{ display: 'flex', gap: 24 }}>
              {[
                { label: 'Docs Ingested', value: result.documents_ingested, cls: 'cyan' },
                { label: 'Total Chunks', value: result.chunks_ingested, cls: 'primary' },
                { label: 'Collection', value: result.collection, cls: 'amber' },
                { label: 'Status', value: result.status, cls: 'green' },
              ].map(({ label, value, cls }) => (
                <div key={label}>
                  <div className="stat-label">{label}</div>
                  <div className={`stat-value ${cls}`} style={{ fontSize: '1.2rem' }}>{value}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  )
}

// ─── Live Debate Page ───────────────────────────────────────────────────────
function LiveDebatePage() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [streaming, setStreaming] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [messages])

  function startDebate() {
    if (!query.trim() || streaming) return
    setMessages([])
    setStreaming(true)

    const eventSource = new EventSource(`/api/streams/research?query=${encodeURIComponent(query)}`)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setMessages(prev => [...prev, data])
      if (data.status === 'all_phases_complete' || data.status === 'aborted') {
        eventSource.close()
        setStreaming(false)
      }
    }

    eventSource.onerror = () => {
      setMessages(prev => [...prev, { status: 'error', msg: '✖ Connection lost or server error.' }])
      eventSource.close()
      setStreaming(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">⚔️ Live Agent Debate</h1>
        <p className="page-subtitle">Real-time reasoning stream from AgentCoordinator (SSE)</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header"><span className="card-title">Initiate Cognitive Session</span></div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && startDebate()}
            placeholder="Enter research query (e.g. Impact of CBDC on liquidity...)"
            style={{
              flex: 1, padding: '10px 14px', background: '#030508', border: '1px solid var(--border)',
              borderRadius: 8, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.875rem',
              outline: 'none'
            }}
          />
          <button className="btn btn-primary" onClick={startDebate} disabled={streaming || !query.trim()}>
            {streaming ? <><span className="spinner" /> Reasoning...</> : '🔥 Start Debate'}
          </button>
        </div>
      </div>

      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 400 }}>
        <div className="card-header">
          <span className="card-title">Reasoning Stream</span>
          {streaming && <span className="badge badge-green pulse">● LIVE STREAMING</span>}
        </div>
        <div className="log-terminal" ref={logRef} style={{ flex: 1, overflowY: 'auto', maxHeight: '60vh' }}>
          {messages.length === 0 && <span style={{ color: 'var(--text-muted)' }}>$ Ready for input...</span>}
          {messages.map((m, i) => (
            <div key={i} className={`debate-msg debate-status-${m.status}`}>
              {m.msg && <div className="debate-text">{m.msg}</div>}
              {m.chunk && m.status === 'phase_0_stream' && (
                <div className="debate-chunk guard">
                  <span className="badge badge-red">RED TEAM</span> {m.chunk.thought}
                </div>
              )}
              {m.chunk && m.status === 'phase_1_stream' && (
                <div className="debate-chunk diver">
                  <span className="badge badge-cyan">DEEP DIVER</span> {m.chunk.step}
                </div>
              )}
              {m.chunk && m.status === 'phase_2_stream' && (
                <div className="debate-chunk resolver">
                  <span className="badge badge-amber">RESOLVER</span> {m.chunk.analysis}
                </div>
              )}
              {m.data && <pre className="debate-data">{JSON.stringify(m.data, null, 2)}</pre>}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

// ─── FinOps Page ────────────────────────────────────────────────────────────
function FinOpsPage() {
  const [metrics, setMetrics] = useState<any>(null)
  const [roi, setRoi] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [tenantId] = useState('internal_001') // Default for demo

  useEffect(() => {
    setLoading(true)
    Promise.all([api.finops(tenantId), api.roi(tenantId)])
      .then(([m, r]) => {
        setMetrics(m)
        setRoi(r)
      })
      .catch(e => console.error('FinOps load failed', e))
      .finally(() => setLoading(false))
  }, [tenantId])

  if (loading) return <div className="page-loading"><span className="spinner" /> Loading FinOps Intelligence...</div>

  const pieData = metrics ? [
    { name: 'Used', value: metrics.quota_used, fill: 'var(--primary)' },
    { name: 'Remaining', value: Math.max(0, metrics.quota_limit - metrics.quota_used), fill: '#1f2d4a' },
  ] : []

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">💰 Cognitive FinOps</h1>
        <p className="page-subtitle">Real-time token economy and ROI tracking for <strong>{tenantId}</strong></p>
      </div>

      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)' }}>
        {[
          { label: 'Total Quota', value: metrics?.quota_limit.toLocaleString(), cls: 'cyan' },
          { label: 'Used Tokens', value: metrics?.quota_used.toLocaleString(), cls: 'amber' },
          { label: 'Estimated Cost', value: `$${metrics?.estimated_cost}`, cls: 'primary' },
          { label: 'ROI Savings', value: `${roi?.savings_percentage}%`, cls: 'green' },
        ].map(({ label, value, cls }) => (
          <div key={label} className="stat-card">
            <div className="stat-label">{label}</div>
            <div className={`stat-value ${cls}`}>{value}</div>
          </div>
        ))}
      </div>

      <div className="charts-grid">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div className="card-header" style={{ width: '100%' }}><span className="card-title">Quota Consumption</span></div>
          <ResponsiveContainer width="100%" height={200}>
            <RadialBarChart cx="50%" cy="50%" innerRadius={60} outerRadius={90} data={pieData} startAngle={90} endAngle={-270}>
              <PolarAngleAxis type="number" domain={[0, metrics?.quota_limit ?? 10000]} angleAxisId={0} tick={false} />
              <RadialBar dataKey="value" cornerRadius={8} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div style={{ textAlign: 'center', marginTop: -20 }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {Math.round((metrics?.quota_used / metrics?.quota_limit) * 100)}%
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>LIMIT EXHAUSTION</div>
          </div>
        </div>

        <div className="card">
          <div className="card-header"><span className="card-title">Efficiency Analysis (ROI)</span></div>
          <table className="data-table">
            <tbody>
              {[
                ['Hours Saved', `${roi?.hours_saved}h`],
                ['Cloud Cost (Equiv)', `$${roi?.token_cost_cloud_equivalent}`],
                ['Actual Edge Cost', `$${roi?.total_on_premise_cost}`],
                ['Net Savings', `$${Math.round(roi?.token_cost_cloud_equivalent - roi?.total_on_premise_cost)}`],
                ['Tasks Completed', roi?.tasks_completed],
              ].map(([k, v]) => (
                <tr key={k}><td style={{ color: 'var(--text-muted)' }}>{k}</td><td style={{ textAlign: 'right', fontWeight: 600 }}>{v}</td></tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 16, padding: 12, background: 'rgba(16, 185, 129, 0.1)', borderRadius: 8, border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--accent-green)', fontWeight: 600 }}>REVENUE PROTECTION</div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>{roi?.recommendation}</p>
          </div>
        </div>

        <div className="card chart-full">
          <div className="card-header">
            <span className="card-title">Budget Depletion Forecast</span>
            <span className="badge badge-amber">EXTRAPOLATED</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '12px 0' }}>
            <div style={{ fontSize: '3rem' }}>⏳</div>
            <div>
              <div style={{ fontSize: '1.2rem', color: 'var(--accent-amber)', fontWeight: 700 }}>
                {metrics?.budget_depletion_forecast ? new Date(metrics.budget_depletion_forecast).toLocaleDateString() : 'Infinite'}
              </div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                Estimated date when current tier quota will be exhausted based on trailing daily average.
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// ─── App Shell ───────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState<Page>('dashboard')

  const PAGES: Record<Page, JSX.Element> = {
    dashboard: <DashboardPage />,
    debate: <LiveDebatePage />,
    finops: <FinOpsPage />,
    complexity: <ComplexityPage />,
    redteam: <RedTeamPage />,
    selfheal: <SelfHealPage />,
    rag: <RAGPage />,
  }

  return (
    <div className="app-shell">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-logo">NN</div>
          NamoNexus
          <span className="topbar-version">NRE v5.0.0</span>
        </div>
        <div className="status-dot">
          <span className="dot" />
          System Operational
        </div>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-section">Navigation</div>
        {NAV.map(({ id, icon, label }) => (
          <div
            key={id}
            className={`sidebar-item ${page === id ? 'active' : ''}`}
            onClick={() => setPage(id)}
          >
            <span className="sidebar-icon">{icon}</span>
            {label}
          </div>
        ))}

        <div className="sidebar-section" style={{ marginTop: 32 }}>NRE v5.0.0</div>
        <div style={{ padding: '8px 24px', fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.8 }}>
          <div>Backend: FastAPI 0.9.0</div>
          <div>DB: SQLite → PostgreSQL</div>
          <div>ASI: Adaptive + Self-Healing</div>
          <div>Branch: claude/docs</div>
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        {PAGES[page]}
      </main>
    </div>
  )
}
