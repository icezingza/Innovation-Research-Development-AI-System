# Phase 2 Design Spec — Cognitive Dashboard (Investor-Grade)

**Date:** 2026-05-16
**Author:** Namo (AI Project Leader)
**Status:** Approved — ready for implementation
**Target:** namonexus.com/dashboard

---

## 1. Objective

Build a production-grade, investor-facing real-time dashboard for the IRD-AI Cognitive Research Runtime. The dashboard must communicate system intelligence visually — without requiring explanation. An investor opening the URL should immediately see AI agents reasoning in real-time, with measurable confidence metrics and a live knowledge graph.

**Success criterion:** Investor sees the dashboard and understands the system's value within 90 seconds, without a walkthrough.

---

## 2. Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend stack | React 18 + Vite + TypeScript + shadcn/ui | Investor-grade credibility, rich ecosystem for data viz |
| Visualization | Recharts (charts) + Cytoscape.js (graph) | Best-in-class for each use case, React-native |
| Real-time | EventSource API → existing SSE `/streams/workflows/{id}` | SSE already implemented in FastAPI — zero backend changes needed |
| Graph data source | PostgreSQL `HypothesisRecord` + `ReasoningTraceRecord` | Neo4j has no graceful degradation — PostgreSQL is reliable now |
| Layout | Command Center — all panels visible simultaneously | No clicks required during demo; maximum WOW factor |
| Deploy | Build → FastAPI `/static` → namonexus.com/dashboard | Single deploy, no separate frontend server |
| State management | Zustand | Lightweight, no boilerplate |
| Data fetching | React Query (`@tanstack/react-query`) | Caching + auto-refresh for polling endpoints |

---

## 3. Layout Architecture

```
┌─────────────────────────────────────────────────────┐
│  NAV: Logo · "IRD-AI Cognitive Dashboard" · LIVE    │
│       KPI pills: Agents · Confidence · Hypotheses   │
├─────────────────────────────────────────────────────┤
│                                                      │
│   PANEL 1 — Real-Time Agent Stream (full width)     │
│   SSE feed · agent name · event text · conf badge   │
│                                                      │
├──────────────────────┬──────────────────────────────┤
│                      │                              │
│  PANEL 2             │  PANEL 3                    │
│  Reasoning Trace     │  Knowledge Graph            │
│  Confidence chart    │  Hypothesis node network    │
│  (Recharts bar)      │  (Cytoscape.js)             │
│  + 3 metric cards    │  + 3 stat cards             │
│                      │                              │
└──────────────────────┴──────────────────────────────┘
```

---

## 4. Component Design

### 4.1 Navigation Bar (`components/NavBar.tsx`)
- Brand: logo + "IRD-AI Cognitive Dashboard · v1.0"
- Live badge: animated green dot + "LIVE" text
- KPI pills (auto-refresh every 5s via React Query):
  - Active Agents (from `/api/runtime/status`)
  - Avg Confidence (from `/api/intelligence/quality-trends`)
  - Total Hypotheses (from `/api/intelligence/hypotheses` count)
  - Reasoning Cycles (from `/api/reasoning/traces` count)

### 4.2 Agent Stream Panel (`components/AgentStream.tsx`)
- Connects to `GET /streams/workflows/{workflow_id}` via `EventSource`
- Workflow ID: pulled from `/api/research/workflows?status=active` — uses most recent active workflow
- Renders last 20 events as scrolling feed (newest at bottom)
- Each event row: timestamp · agent name (color-coded by type) · event text · confidence badge
- Color coding:
  - `hypothesis.*` → blue (`#60a5fa`)
  - `synthesis.*` → purple (`#a78bfa`)
  - `coordination.*` → green (`#34d399`)
  - critique events → amber (`#fbbf24`)
- Confidence badge: green ≥0.80, amber 0.60–0.79, red <0.60
- Auto-reconnect on disconnect (exponential backoff, max 30s)

### 4.3 Reasoning Trace Panel (`components/ReasoningTrace.tsx`)
- Data: `GET /reasoning/traces` (React Query, refetch every 10s)
- Chart: Recharts `BarChart` — x-axis: cycle number, y-axis: avg confidence per cycle (0.0–1.0)
- Latest bar highlighted with glow effect
- 3 metric cards below chart:
  - Current Confidence (latest cycle avg)
  - Quality Trend (from `QualityTracker`: "improving" / "stable" / "declining")
  - Total Cycles
- Color theme: purple (`#a78bfa` / `#4c1d95`)

### 4.4 Knowledge Graph Panel (`components/KnowledgeGraph.tsx`)
- Data: `GET /intelligence/hypotheses` (React Query, refetch every 15s)
- Builds graph: each `HypothesisRecord` = node, edges from `evidence` field references
- Cytoscape.js layout: `cose` (force-directed, auto-arranges)
- Node styling:
  - Size: proportional to `confidence`
  - Color: blue for hypothesis, green for synthesis result, red for contradiction
  - Label: truncated `statement` (first 20 chars)
- 3 stat cards: total nodes · total edges · contradictions count
- Click node → tooltip with full `statement` + `confidence` + `generation`
- Color theme: green (`#34d399` / `#064e3b`)

---

## 5. Data Flow

```
FastAPI Backend (:8000)
│
├── GET /streams/workflows/{id}  →  AgentStream (SSE, push)
├── GET /reasoning/traces        →  ReasoningTrace (poll 10s)
├── GET /intelligence/hypotheses →  KnowledgeGraph (poll 15s)
├── GET /intelligence/quality-trends → NavBar KPI (poll 5s)
└── GET /runtime/status          →  NavBar KPI (poll 5s)

React App (Vite build → /static/dashboard)
├── Zustand store: { activeWorkflowId, streamEvents[], connectionStatus }
├── React Query: traces, hypotheses, kpi (parallel, independent)
└── EventSource: single connection per active workflow
```

---

## 6. File Structure

```
frontend/
├── index.html
├── vite.config.ts           ← proxy /api → localhost:8000
├── tailwind.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx              ← root layout (NavBar + grid)
│   ├── store.ts             ← Zustand store
│   ├── api/
│   │   └── client.ts        ← axios instance, base URL from env
│   ├── components/
│   │   ├── NavBar.tsx
│   │   ├── AgentStream.tsx
│   │   ├── ReasoningTrace.tsx
│   │   └── KnowledgeGraph.tsx
│   └── hooks/
│       ├── useActiveWorkflow.ts
│       ├── useReasoningTraces.ts
│       └── useHypotheses.ts
```

---

## 7. Backend Changes Required

**Minimal** — existing endpoints are sufficient. One addition needed:

| Endpoint | Status | Notes |
|---|---|---|
| `GET /streams/workflows/{id}` | ✅ Exists | SSE stream, no change |
| `GET /reasoning/traces` | ✅ Exists | Add `?limit=50` param support |
| `GET /intelligence/hypotheses` | ✅ Exists | Add `?limit=200` param support |
| `GET /intelligence/quality-trends` | ✅ Exists | No change |
| `GET /runtime/status` | ✅ Exists | No change |
| `GET /research/workflows?status=active` | ⚠️ Verify | Must return active workflow ID |
| `FastAPI StaticFiles /dashboard` | 🆕 Add | Mount React build output |

---

## 8. Deploy

```bash
# Build
cd frontend && npm run build   # outputs to frontend/dist/

# FastAPI — add to src/api/main.py
from fastapi.staticfiles import StaticFiles
app.mount("/dashboard", StaticFiles(directory="frontend/dist", html=True), name="dashboard")
```

Cloudflare Tunnel already routes `namonexus.com` → local FastAPI — no infra changes needed.

---

## 9. Neo4j — Future Path

Graph Viewer currently uses PostgreSQL `HypothesisRecord` as data source. When Neo4j block (HTTP 403) is resolved:
1. Add graceful degradation to `neo4j_connector.py` (try Neo4j → fallback to PostgreSQL)
2. Swap `KnowledgeGraph.tsx` data source to `/memory/graph` endpoint
3. No frontend component changes required

---

## 10. Out of Scope (Phase 2)

- WebSocket (SSE covers real-time needs)
- User authentication on dashboard (internal tool, Phase 3)
- Multi-tenant views (Phase 3)
- Mobile responsive (desktop investor demo only)
- Neo4j live graph (Phase 3, after resilience fix)
