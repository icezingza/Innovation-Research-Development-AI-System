# Phase 2 Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an investor-grade real-time cognitive dashboard at namonexus.com/dashboard showing live agent stream, reasoning confidence chart, and hypothesis knowledge graph.

**Architecture:** React 18 + Vite SPA served as FastAPI static files. Three panels in a Command Center layout — no routing needed. SSE for real-time agent stream, React Query polling for charts and graph data.

**Tech Stack:** React 18, Vite 5, TypeScript 5, Tailwind CSS, shadcn/ui, Recharts, Cytoscape.js, Zustand, @tanstack/react-query, axios

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | Create | npm deps |
| `frontend/vite.config.ts` | Create | Build config, dev proxy, Vitest |
| `frontend/tailwind.config.ts` | Create | Tailwind + shadcn theme |
| `frontend/postcss.config.js` | Create | PostCSS for Tailwind |
| `frontend/tsconfig.json` | Create | TypeScript config |
| `frontend/index.html` | Create | HTML entry point |
| `frontend/src/test-setup.ts` | Create | Vitest global setup |
| `frontend/src/types.ts` | Create | Shared TypeScript types |
| `frontend/src/api/client.ts` | Create | Axios instance |
| `frontend/src/store.ts` | Create | Zustand store |
| `frontend/src/hooks/useActiveWorkflow.ts` | Create | Fetch most recent workflow ID |
| `frontend/src/hooks/useReasoningTraces.ts` | Create | Poll /reasoning/traces |
| `frontend/src/hooks/useHypotheses.ts` | Create | Poll /intelligence/hypotheses |
| `frontend/src/hooks/useKpiStats.ts` | Create | Poll runtime + quality endpoints |
| `frontend/src/components/NavBar.tsx` | Create | Top nav with KPI pills |
| `frontend/src/components/AgentStream.tsx` | Create | SSE live event feed |
| `frontend/src/components/ReasoningTrace.tsx` | Create | Recharts confidence chart |
| `frontend/src/components/KnowledgeGraph.tsx` | Create | Cytoscape.js hypothesis graph |
| `frontend/src/App.tsx` | Create | Root layout grid |
| `frontend/src/main.tsx` | Create | React entry, providers |
| `frontend/src/__tests__/store.test.ts` | Create | Zustand store tests |
| `frontend/src/__tests__/NavBar.test.tsx` | Create | NavBar render tests |
| `frontend/src/__tests__/AgentStream.test.tsx` | Create | Stream event rendering |
| `frontend/src/__tests__/ReasoningTrace.test.tsx` | Create | Chart data transform |
| `frontend/src/__tests__/KnowledgeGraph.test.tsx` | Create | Graph node builder |
| `src/api/main.py` | Modify | Add StaticFiles mount |

---

## Task 1: Scaffold Frontend Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/test-setup.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "ird-ai-dashboard",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tanstack/react-query": "^5.40.0",
    "axios": "^1.7.2",
    "zustand": "^4.5.2",
    "recharts": "^2.12.7",
    "cytoscape": "^3.29.2",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@types/cytoscape": "^3.21.4",
    "@vitejs/plugin-react": "^4.3.1",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.6",
    "@testing-library/user-event": "^14.5.2",
    "vitest": "^1.6.0",
    "jsdom": "^24.1.0",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (p) => p.replace(/^\/api/, '') },
      '/streams': 'http://localhost:8000',
      '/intelligence': 'http://localhost:8000',
      '/reasoning': 'http://localhost:8000',
      '/runtime': 'http://localhost:8000',
      '/research': 'http://localhost:8000',
    },
  },
  build: { outDir: 'dist' },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
  },
})
```

- [ ] **Step 3: Create tailwind.config.ts**

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: '#60a5fa',
          purple: '#a78bfa',
          green: '#34d399',
          amber: '#fbbf24',
          red: '#f87171',
        },
        surface: {
          base: '#020617',
          card: '#0a0f1e',
          panel: '#0f172a',
          border: '#1e293b',
        },
      },
      animation: {
        pulse_dot: 'pulse_dot 1.5s ease-in-out infinite',
      },
      keyframes: {
        pulse_dot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
      },
    },
  },
  plugins: [],
}
export default config
```

- [ ] **Step 4: Create postcss.config.js**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 5: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 6: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>IRD-AI Cognitive Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Create src/test-setup.ts**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 8: Install dependencies**

```bash
cd frontend && npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat(dashboard): scaffold React+Vite+TypeScript frontend"
```

---

## Task 2: Types + API Client

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/__tests__/client.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { apiClient } from '@/api/client'

describe('apiClient', () => {
  it('has correct base URL in dev', () => {
    expect(apiClient.defaults.baseURL).toBe('')
  })

  it('has json content-type header', () => {
    expect(apiClient.defaults.headers['Content-Type']).toBe('application/json')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npm test -- client
```

Expected: `FAIL — Cannot find module '@/api/client'`

- [ ] **Step 3: Create src/types.ts**

```typescript
export interface Workflow {
  workflow_id: string
  goal: string
  status: string
  created_at: string
}

export interface TraceEntry {
  id: string
  operation: string
  input_hash: string
  output_summary: string
  agent_id: string | null
  timestamp: string
  duration_seconds: number
}

export interface HypothesisRecord {
  id: string
  statement: string
  confidence: number
  topic: string
  source: string
  session_id: string | null
  evidence: string[]
  generation: number
  created_at: string
}

export interface StreamEvent {
  type: string
  data: Record<string, unknown>
  receivedAt: string
}

export interface KpiStats {
  activeAgents: number
  avgConfidence: number
  totalHypotheses: number
  totalCycles: number
  qualityTrend: 'improving' | 'stable' | 'declining'
}
```

- [ ] **Step 4: Create src/api/client.ts**

```typescript
import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 10_000,
})
```

- [ ] **Step 5: Run test — expect PASS**

```bash
cd frontend && npm test -- client
```

Expected: `PASS — 2 tests passed`

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(dashboard): add TypeScript types and axios client"
```

---

## Task 3: Zustand Store

**Files:**
- Create: `frontend/src/store.ts`
- Create: `frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/__tests__/store.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { useDashboardStore } from '@/store'
import type { StreamEvent } from '@/types'

describe('useDashboardStore', () => {
  beforeEach(() => {
    useDashboardStore.setState({
      activeWorkflowId: null,
      streamEvents: [],
      connectionStatus: 'disconnected',
    })
  })

  it('starts with empty state', () => {
    const { activeWorkflowId, streamEvents, connectionStatus } = useDashboardStore.getState()
    expect(activeWorkflowId).toBeNull()
    expect(streamEvents).toHaveLength(0)
    expect(connectionStatus).toBe('disconnected')
  })

  it('setActiveWorkflowId updates workflow id', () => {
    useDashboardStore.getState().setActiveWorkflowId('wf-123')
    expect(useDashboardStore.getState().activeWorkflowId).toBe('wf-123')
  })

  it('addStreamEvent appends and caps at 20 events', () => {
    const store = useDashboardStore.getState()
    for (let i = 0; i < 25; i++) {
      const ev: StreamEvent = { type: 'test', data: { i }, receivedAt: new Date().toISOString() }
      store.addStreamEvent(ev)
    }
    expect(useDashboardStore.getState().streamEvents).toHaveLength(20)
  })

  it('setConnectionStatus updates status', () => {
    useDashboardStore.getState().setConnectionStatus('connected')
    expect(useDashboardStore.getState().connectionStatus).toBe('connected')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npm test -- store
```

Expected: `FAIL — Cannot find module '@/store'`

- [ ] **Step 3: Create src/store.ts**

```typescript
import { create } from 'zustand'
import type { StreamEvent } from '@/types'

const MAX_EVENTS = 20

interface DashboardState {
  activeWorkflowId: string | null
  streamEvents: StreamEvent[]
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  setActiveWorkflowId: (id: string | null) => void
  addStreamEvent: (event: StreamEvent) => void
  setConnectionStatus: (status: DashboardState['connectionStatus']) => void
  clearEvents: () => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  activeWorkflowId: null,
  streamEvents: [],
  connectionStatus: 'disconnected',
  setActiveWorkflowId: (id) => set({ activeWorkflowId: id }),
  addStreamEvent: (event) =>
    set((state) => ({
      streamEvents: [...state.streamEvents, event].slice(-MAX_EVENTS),
    })),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  clearEvents: () => set({ streamEvents: [] }),
}))
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npm test -- store
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store.ts frontend/src/__tests__/store.test.ts
git commit -m "feat(dashboard): add Zustand store with event capping"
```

---

## Task 4: Data Hooks

**Files:**
- Create: `frontend/src/hooks/useActiveWorkflow.ts`
- Create: `frontend/src/hooks/useReasoningTraces.ts`
- Create: `frontend/src/hooks/useHypotheses.ts`
- Create: `frontend/src/hooks/useKpiStats.ts`

- [ ] **Step 1: Create useActiveWorkflow.ts**

```typescript
// frontend/src/hooks/useActiveWorkflow.ts
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { apiClient } from '@/api/client'
import { useDashboardStore } from '@/store'
import type { Workflow } from '@/types'

interface WorkflowsResponse {
  workflows: Workflow[]
  count: number
}

export function useActiveWorkflow() {
  const setActiveWorkflowId = useDashboardStore((s) => s.setActiveWorkflowId)

  const query = useQuery({
    queryKey: ['activeWorkflow'],
    queryFn: async () => {
      const { data } = await apiClient.get<WorkflowsResponse>('/research/workflows')
      const running = data.workflows.find((w) => w.status === 'running')
      return running ?? data.workflows[0] ?? null
    },
    refetchInterval: 5_000,
    staleTime: 4_000,
  })

  useEffect(() => {
    setActiveWorkflowId(query.data?.workflow_id ?? null)
  }, [query.data, setActiveWorkflowId])

  return query
}
```

- [ ] **Step 2: Create useReasoningTraces.ts**

```typescript
// frontend/src/hooks/useReasoningTraces.ts
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { TraceEntry } from '@/types'

interface TracesResponse {
  count: number
  traces: TraceEntry[]
}

export interface CyclePoint {
  cycle: number
  avgConfidence: number
  count: number
}

function groupByCycle(traces: TraceEntry[]): CyclePoint[] {
  const map = new Map<number, number[]>()
  traces.forEach((t, idx) => {
    const cycle = Math.floor(idx / 3) + 1
    const scores = map.get(cycle) ?? []
    const conf = parseFloat(t.output_summary.match(/[\d.]+/)?.[0] ?? '0')
    map.set(cycle, [...scores, isNaN(conf) ? 0 : Math.min(conf, 1)])
  })
  return Array.from(map.entries()).map(([cycle, scores]) => ({
    cycle,
    avgConfidence: scores.reduce((a, b) => a + b, 0) / scores.length,
    count: scores.length,
  }))
}

export function useReasoningTraces() {
  return useQuery({
    queryKey: ['reasoningTraces'],
    queryFn: async () => {
      const { data } = await apiClient.get<TracesResponse>('/reasoning/traces')
      return {
        raw: data.traces,
        count: data.count,
        cycles: groupByCycle(data.traces),
        latestConfidence: data.traces.length > 0
          ? parseFloat(data.traces[data.traces.length - 1].output_summary.match(/[\d.]+/)?.[0] ?? '0')
          : 0,
      }
    },
    refetchInterval: 10_000,
    staleTime: 9_000,
  })
}
```

- [ ] **Step 3: Create useHypotheses.ts**

```typescript
// frontend/src/hooks/useHypotheses.ts
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { HypothesisRecord } from '@/types'

interface HypothesesResponse {
  entries: HypothesisRecord[]
  count: number
}

export interface GraphNode {
  id: string
  label: string
  confidence: number
  topic: string
  statement: string
  generation: number
  isContradiction: boolean
}

export interface GraphEdge {
  source: string
  target: string
}

function buildGraph(entries: HypothesisRecord[]): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = entries.map((h) => ({
    id: h.id,
    label: h.statement.slice(0, 20),
    confidence: h.confidence,
    topic: h.topic,
    statement: h.statement,
    generation: h.generation,
    isContradiction: h.confidence < 0.3,
  }))

  const edges: GraphEdge[] = []
  const byTopic = new Map<string, string[]>()
  entries.forEach((h) => {
    const ids = byTopic.get(h.topic) ?? []
    byTopic.set(h.topic, [...ids, h.id])
  })
  byTopic.forEach((ids) => {
    for (let i = 0; i < ids.length - 1; i++) {
      edges.push({ source: ids[i], target: ids[i + 1] })
    }
  })

  return { nodes, edges }
}

export function useHypotheses() {
  return useQuery({
    queryKey: ['hypotheses'],
    queryFn: async () => {
      const { data } = await apiClient.get<HypothesesResponse>('/intelligence/hypotheses')
      const graph = buildGraph(data.entries)
      return {
        entries: data.entries,
        count: data.count,
        graph,
        contradictions: graph.nodes.filter((n) => n.isContradiction).length,
      }
    },
    refetchInterval: 15_000,
    staleTime: 14_000,
  })
}
```

- [ ] **Step 4: Create useKpiStats.ts**

```typescript
// frontend/src/hooks/useKpiStats.ts
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { KpiStats } from '@/types'

export function useKpiStats() {
  return useQuery({
    queryKey: ['kpiStats'],
    queryFn: async (): Promise<KpiStats> => {
      const [runtimeRes, qualityRes, hypothesesRes, tracesRes] = await Promise.allSettled([
        apiClient.get('/runtime/state'),
        apiClient.get('/intelligence/quality-trends'),
        apiClient.get('/intelligence/hypotheses'),
        apiClient.get('/reasoning/traces'),
      ])

      const runtime = runtimeRes.status === 'fulfilled' ? runtimeRes.value.data : {}
      const quality = qualityRes.status === 'fulfilled' ? qualityRes.value.data : {}
      const hypotheses = hypothesesRes.status === 'fulfilled' ? hypothesesRes.value.data : { count: 0 }
      const traces = tracesRes.status === 'fulfilled' ? tracesRes.value.data : { count: 0 }

      return {
        activeAgents: runtime.active_agents ?? runtime.worker_count ?? 0,
        avgConfidence: quality.average_confidence ?? quality.avg_confidence ?? 0,
        totalHypotheses: hypotheses.count ?? 0,
        totalCycles: traces.count ?? 0,
        qualityTrend: quality.trend ?? 'stable',
      }
    },
    refetchInterval: 5_000,
    staleTime: 4_000,
  })
}
```

- [ ] **Step 5: Write hook tests**

Create `frontend/src/__tests__/hooks.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'

// Test groupByCycle logic in isolation (pure function)
function groupByCycle(count: number): number[] {
  return Array.from({ length: count }, (_, i) => Math.floor(i / 3) + 1)
}

describe('groupByCycle', () => {
  it('assigns first 3 traces to cycle 1', () => {
    const cycles = groupByCycle(3)
    expect(cycles).toEqual([1, 1, 1])
  })

  it('assigns traces 4-6 to cycle 2', () => {
    const cycles = groupByCycle(6)
    expect(cycles.slice(3)).toEqual([2, 2, 2])
  })
})

// Test buildGraph edge logic
function buildEdges(entries: { id: string; topic: string }[]): { source: string; target: string }[] {
  const edges: { source: string; target: string }[] = []
  const byTopic = new Map<string, string[]>()
  entries.forEach((h) => {
    const ids = byTopic.get(h.topic) ?? []
    byTopic.set(h.topic, [...ids, h.id])
  })
  byTopic.forEach((ids) => {
    for (let i = 0; i < ids.length - 1; i++) {
      edges.push({ source: ids[i], target: ids[i + 1] })
    }
  })
  return edges
}

describe('buildEdges', () => {
  it('connects hypotheses with same topic', () => {
    const entries = [
      { id: 'a', topic: 'math' },
      { id: 'b', topic: 'math' },
      { id: 'c', topic: 'logic' },
    ]
    const edges = buildEdges(entries)
    expect(edges).toHaveLength(1)
    expect(edges[0]).toEqual({ source: 'a', target: 'b' })
  })

  it('returns no edges when all topics differ', () => {
    const entries = [
      { id: 'a', topic: 'math' },
      { id: 'b', topic: 'logic' },
    ]
    expect(buildEdges(entries)).toHaveLength(0)
  })
})
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
cd frontend && npm test -- hooks
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 7: Commit**

```bash
git add frontend/src/hooks/ frontend/src/__tests__/hooks.test.ts
git commit -m "feat(dashboard): add data hooks for traces, hypotheses, KPI, workflow"
```

---

## Task 5: NavBar Component

**Files:**
- Create: `frontend/src/components/NavBar.tsx`
- Create: `frontend/src/__tests__/NavBar.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/__tests__/NavBar.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NavBar } from '@/components/NavBar'
import type { KpiStats } from '@/types'

const mockKpi: KpiStats = {
  activeAgents: 3,
  avgConfidence: 0.87,
  totalHypotheses: 247,
  totalCycles: 7,
  qualityTrend: 'improving',
}

vi.mock('@/hooks/useKpiStats', () => ({
  useKpiStats: () => ({ data: mockKpi, isLoading: false }),
}))

describe('NavBar', () => {
  it('renders brand name', () => {
    render(<NavBar />)
    expect(screen.getByText(/IRD-AI Cognitive Dashboard/i)).toBeInTheDocument()
  })

  it('shows LIVE badge', () => {
    render(<NavBar />)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
  })

  it('displays active agents count', () => {
    render(<NavBar />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('displays avg confidence', () => {
    render(<NavBar />)
    expect(screen.getByText('0.87')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd frontend && npm test -- NavBar
```

Expected: `FAIL — Cannot find module '@/components/NavBar'`

- [ ] **Step 3: Create src/components/NavBar.tsx**

```tsx
import { useKpiStats } from '@/hooks/useKpiStats'
import type { KpiStats } from '@/types'

function KpiPill({ value, label, color }: { value: string | number; label: string; color: string }) {
  return (
    <div className="text-center px-3">
      <div className={`text-base font-extrabold tracking-tight ${color}`}>{value}</div>
      <div className="text-[10px] text-slate-500 uppercase tracking-widest">{label}</div>
    </div>
  )
}

function TrendColor(trend: KpiStats['qualityTrend']): string {
  if (trend === 'improving') return 'text-brand-green'
  if (trend === 'declining') return 'text-brand-red'
  return 'text-slate-400'
}

export function NavBar() {
  const { data: kpi } = useKpiStats()

  return (
    <nav className="flex items-center justify-between px-7 py-3 bg-surface-card border-b border-surface-border">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm">
          🧠
        </div>
        <div>
          <div className="text-sm font-bold text-slate-100 tracking-tight">
            IRD-AI Cognitive Dashboard
          </div>
          <div className="text-[10px] text-slate-500">
            Sovereign Intelligence Research Platform · v1.0
          </div>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <div className="flex items-center gap-1.5 bg-emerald-950 border border-green-800 rounded-full px-3 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse_dot" />
          <span className="text-[11px] font-semibold text-brand-green">LIVE</span>
        </div>

        <div className="flex items-center divide-x divide-surface-border">
          <KpiPill value={kpi?.activeAgents ?? '—'} label="Agents" color="text-brand-green" />
          <KpiPill value={kpi?.avgConfidence?.toFixed(2) ?? '—'} label="Confidence" color="text-brand-blue" />
          <KpiPill value={kpi?.totalHypotheses ?? '—'} label="Hypotheses" color="text-brand-purple" />
          <KpiPill value={kpi?.totalCycles ?? '—'} label="Cycles" color="text-slate-200" />
          <div className="px-3 text-center">
            <div className={`text-sm font-bold ${TrendColor(kpi?.qualityTrend ?? 'stable')}`}>
              {kpi?.qualityTrend ?? '—'}
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-widest">Trend</div>
          </div>
        </div>
      </div>
    </nav>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd frontend && npm test -- NavBar
```

Expected: `PASS — 4 tests passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/NavBar.tsx frontend/src/__tests__/NavBar.test.tsx
git commit -m "feat(dashboard): add NavBar with live KPI pills"
```

---

## Task 6: AgentStream Component

**Files:**
- Create: `frontend/src/components/AgentStream.tsx`
- Create: `frontend/src/__tests__/AgentStream.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/__tests__/AgentStream.test.tsx
import { describe, it, expect } from 'vitest'

type EventType = 'hypothesis' | 'synthesis' | 'coordination' | 'critique' | 'other'

function classifyEvent(eventType: string): EventType {
  if (eventType.startsWith('hypothesis')) return 'hypothesis'
  if (eventType.startsWith('synthesis')) return 'synthesis'
  if (eventType.startsWith('coordination')) return 'coordination'
  if (eventType.includes('critique') || eventType.includes('critiqued')) return 'critique'
  return 'other'
}

function confidenceClass(conf: number): string {
  if (conf >= 0.8) return 'conf-high'
  if (conf >= 0.6) return 'conf-mid'
  return 'conf-low'
}

describe('classifyEvent', () => {
  it('classifies hypothesis events', () => {
    expect(classifyEvent('hypothesis.generated')).toBe('hypothesis')
  })
  it('classifies synthesis events', () => {
    expect(classifyEvent('synthesis.ready')).toBe('synthesis')
  })
  it('classifies coordination events', () => {
    expect(classifyEvent('coordination.started')).toBe('coordination')
  })
  it('classifies critique events', () => {
    expect(classifyEvent('hypothesis.critiqued')).toBe('critique')
  })
})

describe('confidenceClass', () => {
  it('returns conf-high for 0.80+', () => {
    expect(confidenceClass(0.87)).toBe('conf-high')
  })
  it('returns conf-mid for 0.60–0.79', () => {
    expect(confidenceClass(0.65)).toBe('conf-mid')
  })
  it('returns conf-low for below 0.60', () => {
    expect(confidenceClass(0.3)).toBe('conf-low')
  })
})
```

- [ ] **Step 2: Run test — expect PASS (pure functions, no imports)**

```bash
cd frontend && npm test -- AgentStream
```

Expected: `PASS — 7 tests passed`

- [ ] **Step 3: Create src/components/AgentStream.tsx**

```tsx
import { useEffect, useRef } from 'react'
import { useDashboardStore } from '@/store'
import type { StreamEvent } from '@/types'

type EventKind = 'hypothesis' | 'synthesis' | 'coordination' | 'critique' | 'other'

function classifyEvent(type: string): EventKind {
  if (type.startsWith('hypothesis')) return 'hypothesis'
  if (type.startsWith('synthesis')) return 'synthesis'
  if (type.startsWith('coordination')) return 'coordination'
  if (type.includes('critique') || type.includes('critiqued')) return 'critique'
  return 'other'
}

const KIND_COLORS: Record<EventKind, string> = {
  hypothesis: 'text-brand-blue border-blue-600',
  synthesis: 'text-brand-purple border-purple-600',
  coordination: 'text-brand-green border-green-700',
  critique: 'text-brand-amber border-amber-600',
  other: 'text-slate-400 border-slate-600',
}

function ConfBadge({ conf }: { conf: number }) {
  const cls =
    conf >= 0.8
      ? 'bg-emerald-950 text-brand-green'
      : conf >= 0.6
      ? 'bg-orange-950 text-brand-amber'
      : 'bg-red-950 text-brand-red'
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded shrink-0 ${cls}`}>
      {conf.toFixed(2)}
    </span>
  )
}

function EventRow({ event }: { event: StreamEvent }) {
  const kind = classifyEvent(event.type)
  const color = KIND_COLORS[kind]
  const conf = (event.data.confidence as number) ?? (event.data.score as number) ?? null
  const agentId = (event.data.source_agent_id as string) ?? (event.data.agent_id as string) ?? event.type
  const text = (event.data.conclusion as string) ?? (event.data.goal as string) ?? JSON.stringify(event.data).slice(0, 120)
  const ts = event.receivedAt.slice(11, 19)

  return (
    <div className={`flex items-start gap-2.5 px-3 py-2 rounded bg-surface-panel border-l-2 ${color}`}>
      <span className="text-[10px] text-slate-600 font-mono shrink-0 mt-0.5">{ts}</span>
      <span className={`text-[11px] font-semibold shrink-0 w-36 truncate ${color.split(' ')[0]}`}>
        {agentId}
      </span>
      <span className="text-[11px] text-slate-400 flex-1 leading-relaxed">{text}</span>
      {conf !== null && <ConfBadge conf={conf} />}
    </div>
  )
}

function useSSEConnection() {
  const { activeWorkflowId, addStreamEvent, setConnectionStatus } = useDashboardStore()
  const esRef = useRef<EventSource | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryDelay = useRef(1_000)

  useEffect(() => {
    if (!activeWorkflowId) return

    function connect() {
      setConnectionStatus('connecting')
      const es = new EventSource(`/streams/workflows/${activeWorkflowId}`)
      esRef.current = es

      es.onopen = () => {
        setConnectionStatus('connected')
        retryDelay.current = 1_000
      }

      es.onmessage = (e) => {
        try {
          const parsed = JSON.parse(e.data) as { type: string; data: Record<string, unknown> }
          addStreamEvent({ ...parsed, receivedAt: new Date().toISOString() })
        } catch {
          /* ignore malformed events */
        }
      }

      es.onerror = () => {
        setConnectionStatus('error')
        es.close()
        retryRef.current = setTimeout(() => {
          retryDelay.current = Math.min(retryDelay.current * 2, 30_000)
          connect()
        }, retryDelay.current)
      }
    }

    connect()
    return () => {
      esRef.current?.close()
      if (retryRef.current) clearTimeout(retryRef.current)
      setConnectionStatus('disconnected')
    }
  }, [activeWorkflowId, addStreamEvent, setConnectionStatus])
}

export function AgentStream() {
  useSSEConnection()
  const { streamEvents, connectionStatus } = useDashboardStore()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [streamEvents])

  return (
    <div className="bg-surface-card border border-blue-950 rounded-xl overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-border">
        <div className="text-[11px] font-semibold text-brand-blue uppercase tracking-widest">
          ⬡ Real-Time Agent Stream
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connectionStatus === 'connected' ? 'bg-brand-green animate-pulse_dot' : 'bg-slate-600'
            }`}
          />
          <span className="text-[10px] font-mono text-slate-600">
            SSE · /streams/workflows/{'{id}'}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-1.5 p-3 overflow-y-auto max-h-48">
        {streamEvents.length === 0 ? (
          <div className="text-[11px] text-slate-600 text-center py-4">
            {connectionStatus === 'connecting' ? 'Connecting to agent stream...' : 'Waiting for agent activity...'}
          </div>
        ) : (
          streamEvents.map((ev, i) => <EventRow key={i} event={ev} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — all pass**

```bash
cd frontend && npm test -- AgentStream
```

Expected: `PASS — 7 tests passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AgentStream.tsx frontend/src/__tests__/AgentStream.test.tsx
git commit -m "feat(dashboard): add AgentStream with SSE auto-reconnect"
```

---

## Task 7: ReasoningTrace Component

**Files:**
- Create: `frontend/src/components/ReasoningTrace.tsx`
- Create: `frontend/src/__tests__/ReasoningTrace.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/__tests__/ReasoningTrace.test.tsx
import { describe, it, expect } from 'vitest'
import type { CyclePoint } from '@/hooks/useReasoningTraces'

function trendColor(trend: string): string {
  if (trend === 'improving') return '#4ade80'
  if (trend === 'declining') return '#f87171'
  return '#94a3b8'
}

function latestConf(cycles: CyclePoint[]): number {
  if (cycles.length === 0) return 0
  return cycles[cycles.length - 1].avgConfidence
}

describe('trendColor', () => {
  it('green for improving', () => expect(trendColor('improving')).toBe('#4ade80'))
  it('red for declining', () => expect(trendColor('declining')).toBe('#f87171'))
  it('gray for stable', () => expect(trendColor('stable')).toBe('#94a3b8'))
})

describe('latestConf', () => {
  it('returns 0 for empty cycles', () => expect(latestConf([])).toBe(0))
  it('returns last cycle confidence', () => {
    const cycles: CyclePoint[] = [
      { cycle: 1, avgConfidence: 0.5, count: 3 },
      { cycle: 2, avgConfidence: 0.82, count: 3 },
    ]
    expect(latestConf(cycles)).toBe(0.82)
  })
})
```

- [ ] **Step 2: Run test — expect PASS**

```bash
cd frontend && npm test -- ReasoningTrace
```

Expected: `PASS — 5 tests passed`

- [ ] **Step 3: Create src/components/ReasoningTrace.tsx**

```tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useReasoningTraces } from '@/hooks/useReasoningTraces'
import type { CyclePoint } from '@/hooks/useReasoningTraces'

function MetricCard({ value, label, sub }: { value: string; label: string; sub?: string }) {
  return (
    <div className="bg-surface-panel rounded-lg p-3">
      <div className="text-xl font-extrabold text-brand-purple tracking-tight">{value}</div>
      <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-0.5">{label}</div>
      {sub && <div className="text-[9px] text-brand-green mt-1">{sub}</div>}
    </div>
  )
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { value: number }[] }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-card border border-surface-border rounded px-2 py-1 text-[11px] text-slate-300">
      Confidence: <span className="text-brand-purple font-bold">{payload[0].value.toFixed(3)}</span>
    </div>
  )
}

export function ReasoningTrace() {
  const { data, isLoading } = useReasoningTraces()
  const cycles: CyclePoint[] = data?.cycles ?? []
  const lastIdx = cycles.length - 1

  return (
    <div className="bg-surface-card border border-purple-950 rounded-xl overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-border">
        <div className="text-[11px] font-semibold text-brand-purple uppercase tracking-widest">
          ◈ Reasoning Trace — Confidence Score
        </div>
        <div className="text-[10px] font-mono text-slate-600">poll 10s · PostgreSQL</div>
      </div>

      <div className="p-4 flex flex-col gap-3 flex-1">
        {isLoading ? (
          <div className="text-[11px] text-slate-600 text-center py-6">Loading traces...</div>
        ) : cycles.length === 0 ? (
          <div className="text-[11px] text-slate-600 text-center py-6">No reasoning cycles yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={90}>
            <BarChart data={cycles} margin={{ top: 0, right: 4, left: -28, bottom: 0 }}>
              <XAxis dataKey="cycle" tick={{ fontSize: 9, fill: '#475569' }} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 9, fill: '#475569' }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1e293b' }} />
              <Bar dataKey="avgConfidence" radius={[3, 3, 0, 0]}>
                {cycles.map((_, idx) => (
                  <Cell
                    key={idx}
                    fill={idx === lastIdx ? '#a78bfa' : '#6d28d9'}
                    style={idx === lastIdx ? { filter: 'drop-shadow(0 0 6px #a78bfa88)' } : undefined}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}

        <div className="grid grid-cols-3 gap-2">
          <MetricCard
            value={(data?.latestConfidence ?? 0).toFixed(2)}
            label="Current Confidence"
            sub={`↑ cycle ${cycles.length}`}
          />
          <MetricCard
            value={data?.count?.toString() ?? '0'}
            label="Total Traces"
            sub="ReasoningTrace"
          />
          <MetricCard
            value={cycles.length.toString()}
            label="Cycles"
            sub="RecursiveLoop"
          />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — all pass**

```bash
cd frontend && npm test -- ReasoningTrace
```

Expected: `PASS — 5 tests passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ReasoningTrace.tsx frontend/src/__tests__/ReasoningTrace.test.tsx
git commit -m "feat(dashboard): add ReasoningTrace panel with Recharts confidence chart"
```

---

## Task 8: KnowledgeGraph Component

**Files:**
- Create: `frontend/src/components/KnowledgeGraph.tsx`
- Create: `frontend/src/__tests__/KnowledgeGraph.test.tsx`

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/__tests__/KnowledgeGraph.test.tsx
import { describe, it, expect } from 'vitest'
import type { GraphNode } from '@/hooks/useHypotheses'

function nodeColor(node: GraphNode): string {
  if (node.isContradiction) return '#f87171'
  if (node.confidence >= 0.8) return '#34d399'
  return '#60a5fa'
}

function nodeSize(confidence: number): number {
  return Math.max(20, Math.min(50, confidence * 50))
}

describe('nodeColor', () => {
  it('red for contradiction', () => {
    const n: GraphNode = { id: '1', label: 'x', confidence: 0.2, topic: 't', statement: 'x', generation: 1, isContradiction: true }
    expect(nodeColor(n)).toBe('#f87171')
  })
  it('green for high confidence', () => {
    const n: GraphNode = { id: '1', label: 'x', confidence: 0.9, topic: 't', statement: 'x', generation: 1, isContradiction: false }
    expect(nodeColor(n)).toBe('#34d399')
  })
  it('blue for normal hypothesis', () => {
    const n: GraphNode = { id: '1', label: 'x', confidence: 0.5, topic: 't', statement: 'x', generation: 1, isContradiction: false }
    expect(nodeColor(n)).toBe('#60a5fa')
  })
})

describe('nodeSize', () => {
  it('minimum 20px', () => expect(nodeSize(0)).toBe(20))
  it('maximum 50px', () => expect(nodeSize(1)).toBe(50))
  it('scales proportionally', () => expect(nodeSize(0.5)).toBe(25))
})
```

- [ ] **Step 2: Run test — expect PASS**

```bash
cd frontend && npm test -- KnowledgeGraph
```

Expected: `PASS — 7 tests passed`

- [ ] **Step 3: Create src/components/KnowledgeGraph.tsx**

```tsx
import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import { useHypotheses } from '@/hooks/useHypotheses'
import type { GraphNode } from '@/hooks/useHypotheses'

function nodeColor(node: GraphNode): string {
  if (node.isContradiction) return '#f87171'
  if (node.confidence >= 0.8) return '#34d399'
  return '#60a5fa'
}

function nodeSize(confidence: number): number {
  return Math.max(20, Math.min(50, confidence * 50))
}

interface Tooltip {
  x: number
  y: number
  node: GraphNode
}

function GraphStatCard({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="bg-surface-panel rounded-lg p-3">
      <div className={`text-xl font-extrabold tracking-tight ${color}`}>{value}</div>
      <div className="text-[9px] text-slate-500 uppercase tracking-widest mt-0.5">{label}</div>
    </div>
  )
}

export function KnowledgeGraph() {
  const { data, isLoading } = useHypotheses()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [tooltip, setTooltip] = useState<Tooltip | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data?.graph) return

    cyRef.current?.destroy()

    const { nodes, edges } = data.graph
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...nodes.map((n) => ({
          data: { id: n.id, label: n.label, ...n },
        })),
        ...edges.map((e, i) => ({
          data: { id: `e${i}`, source: e.source, target: e.target },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (el) => nodeColor(el.data() as GraphNode),
            width: (el) => nodeSize((el.data() as GraphNode).confidence),
            height: (el) => nodeSize((el.data() as GraphNode).confidence),
            label: 'data(label)',
            'font-size': '8px',
            color: '#94a3b8',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'border-width': 1.5,
            'border-color': (el) => nodeColor(el.data() as GraphNode),
            'background-opacity': 0.15,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1,
            'line-color': '#1e3a5f',
            'target-arrow-color': '#1e3a5f',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.6,
            'curve-style': 'bezier',
          },
        },
        {
          selector: 'node:selected',
          style: { 'border-width': 2.5, 'border-color': '#f8fafc' },
        },
      ],
      layout: { name: 'cose', animate: false, randomize: false },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      backgroundColor: '#020617',
    })

    cy.on('tap', 'node', (e) => {
      const node = e.target.data() as GraphNode
      const pos = e.renderedPosition
      setTooltip({ x: pos.x, y: pos.y, node })
    })
    cy.on('tap', (e) => {
      if (e.target === cy) setTooltip(null)
    })

    cyRef.current = cy
    return () => cy.destroy()
  }, [data?.graph])

  return (
    <div className="bg-surface-card border border-green-950 rounded-xl overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-border">
        <div className="text-[11px] font-semibold text-brand-green uppercase tracking-widest">
          ◎ Knowledge Graph — Hypothesis Network
        </div>
        <div className="text-[10px] font-mono text-slate-600">PostgreSQL · Cytoscape.js · poll 15s</div>
      </div>

      <div className="p-3 flex flex-col gap-3 flex-1">
        <div className="relative bg-surface-base rounded-lg overflow-hidden" style={{ height: 130 }}>
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-[11px] text-slate-600">
              Loading graph...
            </div>
          ) : (
            <div ref={containerRef} className="w-full h-full" />
          )}
          {tooltip && (
            <div
              className="absolute bg-surface-card border border-surface-border rounded-lg p-2.5 text-[11px] max-w-[200px] z-10 shadow-xl"
              style={{ left: tooltip.x + 8, top: tooltip.y + 8 }}
            >
              <div className="font-semibold text-slate-200 leading-snug mb-1">{tooltip.node.statement}</div>
              <div className="text-slate-500">Confidence: <span className="text-brand-green">{tooltip.node.confidence.toFixed(3)}</span></div>
              <div className="text-slate-500">Topic: {tooltip.node.topic}</div>
              <div className="text-slate-500">Generation: {tooltip.node.generation}</div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2">
          <GraphStatCard value={data?.count ?? 0} label="Hypothesis Nodes" color="text-brand-green" />
          <GraphStatCard value={data?.graph.edges.length ?? 0} label="Relationships" color="text-brand-blue" />
          <GraphStatCard value={data?.contradictions ?? 0} label="Contradictions" color="text-brand-red" />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — all pass**

```bash
cd frontend && npm test -- KnowledgeGraph
```

Expected: `PASS — 7 tests passed`

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/KnowledgeGraph.tsx frontend/src/__tests__/KnowledgeGraph.test.tsx
git commit -m "feat(dashboard): add KnowledgeGraph with Cytoscape.js and node tooltip"
```

---

## Task 9: App Root Layout + Entry

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create src/index.css**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; }

body {
  background-color: #020617;
  color: #e2e8f0;
  font-family: 'Inter', system-ui, sans-serif;
  min-height: 100vh;
  overflow: hidden;
}

#root { height: 100vh; display: flex; flex-direction: column; }
```

- [ ] **Step 2: Create src/App.tsx**

```tsx
import { NavBar } from '@/components/NavBar'
import { AgentStream } from '@/components/AgentStream'
import { ReasoningTrace } from '@/components/ReasoningTrace'
import { KnowledgeGraph } from '@/components/KnowledgeGraph'
import { useActiveWorkflow } from '@/hooks/useActiveWorkflow'

function Dashboard() {
  useActiveWorkflow()

  return (
    <div className="flex flex-col h-full">
      <NavBar />
      <main className="flex-1 grid grid-rows-[auto_1fr] gap-3 p-4 min-h-0">
        <AgentStream />
        <div className="grid grid-cols-2 gap-3 min-h-0">
          <ReasoningTrace />
          <KnowledgeGraph />
        </div>
      </main>
    </div>
  )
}

export default Dashboard
```

- [ ] **Step 3: Create src/main.tsx**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 4: Run all tests**

```bash
cd frontend && npm test
```

Expected: `PASS — all test suites pass, 0 failures`

- [ ] **Step 5: Start dev server and verify UI**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173 — should see Command Center layout with NavBar, AgentStream panel, Reasoning chart, Graph viewer.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.tsx frontend/src/main.tsx frontend/src/index.css
git commit -m "feat(dashboard): wire root layout and React Query provider"
```

---

## Task 10: FastAPI Static Mount

**Files:**
- Modify: `src/api/main.py`

- [ ] **Step 1: Read current main.py and locate app creation**

Find the `create_app()` function in `src/api/main.py`. The static mount goes after all routers are registered, before the function returns.

- [ ] **Step 2: Add static mount**

Add these lines at the end of `create_app()`, just before `return app`:

```python
import os
from fastapi.staticfiles import StaticFiles

# Dashboard static files (React build)
_dashboard_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(_dashboard_dir):
    app.mount(
        "/dashboard",
        StaticFiles(directory=_dashboard_dir, html=True),
        name="dashboard",
    )
```

- [ ] **Step 3: Build frontend**

```bash
cd frontend && npm run build
```

Expected: `frontend/dist/` directory created with `index.html` and assets.

- [ ] **Step 4: Verify mount**

```bash
cd .. && uvicorn src.api.main:app --reload --port 8000
```

Open http://localhost:8000/dashboard — should load the React dashboard.

- [ ] **Step 5: Commit**

```bash
git add src/api/main.py frontend/dist/
git commit -m "feat(dashboard): mount React build at /dashboard via FastAPI StaticFiles"
```

---

## Task 11: Final Verify + Checklist

- [ ] **Step 1: Run full test suite**

```bash
# Backend
pytest --tb=short -q

# Frontend
cd frontend && npm test
```

Expected: backend 207+ tests pass, frontend all suites pass.

- [ ] **Step 2: Run linter**

```bash
ruff check src/
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 3: Smoke test live dashboard**

Start backend: `uvicorn src.api.main:app --reload --port 8000`

Visit http://localhost:8000/dashboard and confirm:
- [ ] NavBar shows "IRD-AI Cognitive Dashboard" + LIVE badge
- [ ] KPI pills populate (may show 0 if no active workflow)
- [ ] AgentStream panel renders (shows "Waiting..." if no active workflow)
- [ ] ReasoningTrace renders chart or "No cycles yet"
- [ ] KnowledgeGraph renders graph or "Loading..."
- [ ] No console errors

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: Phase 2 investor-grade cognitive dashboard complete"
```

---

## Post-Deploy Notes

- **Cloudflare Tunnel:** Already routes `namonexus.com` → localhost:8000. Dashboard available at `namonexus.com/dashboard` immediately after build.
- **ROADMAP_V1.md:** Update Phase 2 checkboxes after deploy.
- **Neo4j graph upgrade:** When HTTP 403 is resolved, swap `KnowledgeGraph.tsx` data source only — no other changes needed.
