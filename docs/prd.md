# 🎯 Product Requirements Document (PRD) — NamoNexus

## 🚀 1. Executive Summary & Vision

**NamoNexus (NRE v5.0.0 Sovereign Edition)** is a distributed cognitive operating infrastructure designed to enable autonomous scientific research, persistent semantic reasoning, and multi-agent coordination. 

This is **NOT a simple chatbot**. NamoNexus is a persistent, sovereign, multi-tenant enterprise cognitive engine deployed on a Hybrid Cloud stack (Lenovo Edge + Google Cloud Platform) to automate knowledge synthesis, analyze contradictions, and build long-term memory models on top of high-precision datasets (such as Dhamma repositories utilizing the "Short Chunk Strategy").

### Core Objectives
1. **Semantic Continuity:** Enable AI agents to recall context from previous research sessions across weeks, months, or years.
2. **Autonomous Scientific Discovery:** Move beyond Q&A to execute long-running, multi-phase research workflows (Planning → Parallel Investigation → Debate → Recursive Reflection → Coherent Synthesis).
3. **Enterprise Grade & Multi-Tenancy:** Secure data isolation (RLS), tenant tiered limits (Free, Pro, Enterprise), real-time FinOps quota metrics, and ROI cost tracking.
4. **Absolute Observability:** Track every step of the cognitive process via an immutable reasoning trace.

---

## 👥 2. User Personas & Core Journeys

### Primary Persona: P'Ice (พี่ไอซ์) — Research Lead & AI Architect
* **Role:** Sets research goals, triggers autonomous deep dives, analyzes contradictions in generated hypotheses, and manages tenant budgets.
* **Pain Points:** 
  * standard AI models suffer from "amnesia" between sessions.
  * AI-generated content lacks traceability and audit trails.
  * cost forecasting for complex multi-agent pipelines is highly opaque.
* **User Journey:**
  1. P'Ice logs into the **NamoNexus Dashboard**.
  2. Submits a complex research task: *“Analyze the relationship between dynamic mental states in the Abhidhamma and cognitive feedback loops.”*
  3. The system pulls prior evidence, spawns specialized agents, and executes a parallel debate.
  4. P'Ice monitors the live reasoning stream and interacts with the generated Knowledge Graph.
  5. Reviews the auditable reasoning trace, updates tenant tier limits, and tracks ROI efficiency.

---

## 🏗️ 3. Functional Requirements

### 3.1. Multi-Agent Orchestration & Coordination
* **Goal Generation:** The `AgentCoordinator` must divide a broad question into optimal sub-questions.
* **Parallel Execution:** Spawn specialized parallel agents (`HypothesisAgent` and `CritiqueAgent`) per sub-question.
* **Synthesis:** The `SynthesisAgent` consolidates all evolved hypotheses and critiques into a unified, high-confidence output.
* **Dynamic Scaling:** Live injection of agents without system downtime using the `AgentSpawner`.

### 3.2. Five-Tier Persistent Memory System
* **Vector Tier (Qdrant):** Embed and retrieve semantic chunks using `ContextEngine`.
* **Graph Tier (Neo4j):** Store hypothesis nodes, relations, and contradictions (`KnowledgeGraph`).
* **Structured Tier (PostgreSQL):** Track and persist tenants, users, tasks, workflow states, and completed traces.
* **Runtime Caching (Redis):** Session state cache (24h TTL), event stream message brokers, and live rate limiting.
* **Reactive Persistence:** `MemoryAgent` must listen to event buses and sync findings asynchronously without blocking the execution loop.

### 3.3. Recursive Reasoning & Reflection Loop
* **Hypothesis Evolution:** Iterate on a hypothesis, stress-testing it via critiques.
* **Convergence Thresholds:** Loop continues until one of three conditions is met:
  1. Quality threshold is achieved (analyzed by `QualityTracker`).
  2. No improvement detected over consecutive cycles.
  3. Max recursion depth is reached.
* **Adaptive Configuration:** The `AdaptiveConfigManager` must adjust depth and complexity dynamically based on prior quality trends.

### 3.4. Multi-Tenant identity, FinOps & ROI Gating
* **Tenant Provisioning:** API endpoints to create tenants, assign domains, and upgrade plans (`Free`, `Pro`, `Enterprise`).
* **FinOps Analytics:** Fetch live quota consumption, forecast budget depletion, and generate tier upgrade alerts.
* **ROI Tracking:** Compute hours saved, compare actual internal token costs against public cloud rates, and measure processing speeds.
* **Data Isolation:** Enforce row-level security (RLS) in PostgreSQL based on `tenant_id`.

---

## 🔒 4. Security & Compliance (Sovereign Edition)

1. **Zero-Hardcoding Policy:** All sensitive credentials, database URLs, and API tokens must be pulled from GCP Secret Manager via `backend/namo_core/config/gcp_secrets.py`.
2. **API Gating:** Custom `SecurityMiddleware` to enforce X-API-Key validation for platform actions, and JWT Bearer tokens for tenant-scoped operations.
3. **Sliding-Window Rate Limiting:** Prevent API abuse with active sliding window limits managed in Redis (60 requests/minute default).
4. **Governance Auditing:** Evaluate every message with `PolicyEnforcer` and log violating behaviors in an immutable `GovernanceAuditLog` to prevent prompt injections or policy drift.

---

## 📈 5. Success Metrics & Performance Thresholds

| Metric | Target | Verification Method |
|--------|--------|---------------------|
| **System Health** | 99.9% Uptime | Prometheus endpoint (`/metrics`) |
| **Reasoning Latency** | < 45 seconds per cycle | Telemetry reasoning timers |
| **Retrieval Precision**| > 94% on Dhamma data | Test suite vector search verification |
| **FinOps Accuracy** | 100% accurate quota tracking | Redis rate counter validation |
| **TypeScript Type Safety**| Zero `any` types in TS | `npm run build` compilation check |
| **Backend Async Integrity**| 100% Non-blocking endpoints | Asyncio event loop latency audits |
