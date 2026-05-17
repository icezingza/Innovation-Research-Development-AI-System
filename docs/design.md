# 🎨 UI/UX Frontend Design — NamoNexus

## 🌟 1. Design System & Aesthetics (NRE v5.0.0 Standard)

The NamoNexus user interface is crafted to feel like a premium, state-of-the-art **Cognitive Operating Console**. It follows strict Gen Z professional aesthetics: vibrant but balanced neon tones, sleek glassmorphism, responsive grid systems, and subtle micro-animations.

### 🎨 Color Palette & CSS Variables (`frontend/src/index.css`)
We avoid default or harsh generic colors in favor of curated HSL tones:
```css
:root {
  --bg-color: #0b0f19;       /* Deep space slate */
  --panel-bg: rgba(30, 41, 59, 0.7); /* Translucent obsidian glass */
  --text-main: #f8fafc;      /* Pure white-silver */
  --text-muted: #94a3b8;     /* Cold slate grey */
  --accent: #6366f1;         /* Electric Indigo */
  --accent-glow: rgba(99, 102, 241, 0.15);
  --success: #10b981;        /* Emerald neon */
  --warning: #f59e0b;        /* Amber warning */
  --danger: #ef4444;         /* Ruby alert */
  --border: rgba(51, 65, 85, 0.6); /* Sleek translucent borders */
  --glass-blur: blur(12px);
}
```

---

## 🏛️ 2. Core Dashboard Layout & Elements

The application dashboard is composed of a responsive grid layout divided into functional widgets:

```
┌────────────────────────────────────────────────────────┐
│                        NavBar                          │
├────────────────────────────────────────────────────────┤
│                       KpiPills                         │
├───────────────┬────────────────────────┬───────────────┤
│               │                        │               │
│  AgentStream  │     KnowledgeGraph     │ReasoningTrace │
│  (SSE Logs)   │  (Neo4j Live Network)  │ (Reflections) │
│               │                        │               │
└───────────────┴────────────────────────┴───────────────┘
```

### 2.1. Premium Navigation Bar (`NavBar.tsx`)
* **Features:**
  * **Branding:** Glass-glowing "NamoNexus Sovereign Console" title logo.
  * **Tenant Indicator:** Active Tenant Name & current Subscription Tier (Free/Pro/Enterprise) badge.
  * **Auth Switch:** Displays the currently logged-in user profile, role (Auditor/Finance/Owner), and standard JWT Logout button.
* **Styles:** Fixed-height sticky header, thin translucent bottom border, backing `backdrop-filter: blur(16px)`.

### 2.2. Critical KPI Pills (`KpiPills.tsx`)
A horizontal bar at the top displaying real-time metrics for instant system status:
* **System Health:** Neon green pill signaling active websocket/SSE connectivity (`Normal` / `Degraded` / `Disconnected`).
* **Active Agents:** Total running agents active across the worker pool (e.g. `12 Agents Running`).
* **Active Tasks:** Current research tasks queued inside `AsyncScheduler`.
* **Tenant Quota Progress:** Horizontal progress bar showing consumed api-calls (e.g. `12.4k / 50k calls used`).

### 2.3. Agent Reasoning Event Stream (`AgentStream.tsx`)
A vertical logs stream displaying live agent thoughts as they emerge:
* **SSE-Driven:** Powered by the `useWorkflowStream` hook parsing SSE events from `/api/routes/streams.py`.
* **Interactive Elements:**
  * Auto-scroll toggle checkbox.
  * Agent filter tabs (`All`, `HypothesisAgent`, `CritiqueAgent`, `SynthesisAgent`, `System`).
  * Expansion details to view raw JSON events.
* **Aesthetics:** Monospace font, glowing status dots matching the active agent color, and custom-styled terminal scrollbars.

### 2.4. Hypothesis Lineage Knowledge Graph (`KnowledgeGraph.tsx`)
An interactive 2D canvas visualizing the Neo4j hypothesis lineage:
* **Nodes:**
  * **Questions (Blue):** The sub-questions generated during planning.
  * **Hypotheses (Indigo/Green):** The proposed theories with confidence scores (0.0–1.0).
  * **Contradictions (Red):** Points of conflict flagged by the `ContradictionAnalyzer`.
* **Interactive Elements:** Zoom & Pan controls, click node to preview statement details, evidence payload, and lineage relations.

### 2.5. Deep Reasoning Trace Inspector (`ReasoningTrace.tsx`)
A dedicated component displaying the evolution steps of the `RecursiveReasoningLoop`:
* **Iteration Cards:** Shows each cycle, quality delta (`+0.12`, `-0.05`), duration timers, and reflection notes.
* **Quality Curve Chart:** Sparkline showing the hypothesis confidence trend over consecutive cycles.

---

## 🔄 3. State Management & Real-time Integration

### 3.1. Zustand-like Global Store (`useDashboardStore.ts`)
* **State Values:**
  * `tenantId`, `activeWorkflowId`, `systemStatus`
  * `agentLogs` (array of parsed stream events)
  * `graphNodes` and `graphEdges` (Neo4j structure)
  * `finopsMetrics` (limit, used, estimated cost)
* **Actions:**
  * `addLogEvent(event)`: Append and clean logs exceeding 500 entries.
  * `setGraphData(nodes, edges)`: Direct updates for graph visualization.
  * `updateFinOps(metrics)`: Sync and trigger UI warning banners when quota usage exceeds 80%.

### 3.2. Server-Sent Events (SSE) hook (`useWorkflowStream.ts`)
* **API Connection:** Establishes an `EventSource` connection pointing to `/api/routes/streams?tenant_id={id}`.
* **Strict Type Checking:** Disallows `any`. Decodes events into explicit strict interfaces:
```typescript
interface AgentEvent {
  topic: "hypothesis.generated" | "hypothesis.critiqued" | "synthesis.ready" | "coordination.progress";
  payload: {
    task_id: string;
    agent_id: string;
    content: Record<string, unknown>;
    timestamp: string;
  };
}
```
* **Reconnection Logic:** Implements exponential backoff (starting at 1s, doubling to max 30s) on disconnection to prevent flooding.
