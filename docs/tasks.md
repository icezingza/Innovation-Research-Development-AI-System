# ⏳ Execution Runtimes & Workflow Tasks — NamoNexus

## 🚀 1. The Research Execution Pipeline

Scientific research and reasoning require durable, long-running workflow runtimes. NamoNexus handles this through the `ResearchWorkflow` orchestrator, which implements a state-driven, resilient processing loop.

```
                  ┌────────────────────────┐
                  │    POST /workflows     │
                  └───────────┬────────────┘
                              │ registers task
                              ▼
                  ┌────────────────────────┐
                  │     AsyncScheduler     │
                  └───────────┬────────────┘
                              │ allocates worker
                              ▼
                  ┌────────────────────────┐
                  │    ResearchWorkflow    │
                  │                        │
                  │  1. Plan               │
                  │  2. Parallel Research  │
                  │  3. Debate             │
                  │  4. Recursive Evolution│
                  │  5. Synthesis          │
                  └────────────────────────┘
```

---

## 🛠️ 2. Execution Orchestrators

### 2.1. ResearchWorkflow (`src/orchestration/research_workflow.py`)
* **Role:** Orchestrates the multi-stage research lifecycle.
* **Execution Steps:**
  1. **Planning:** Takes a broad question and splits it into discrete sub-questions.
  2. **Parallel Research:** Dispatches sub-questions to parallelized agents.
  3. **Debate:** Spawns debate rounds between agents proposing differing viewpoints.
  4. **Recursive Evolution:** Runs `RecursiveReasoningLoop` to refine confidence scores.
  5. **Synthesis:** Consolidated concluding findings are compiled.
* **Resiliency:** Progress states are updated in PostgreSQL and broadcasted to SSE stream channels (`StreamManager`) in real-time.

### 2.2. ResearchAgenda (`src/orchestration/research_agenda.py`)
* **Role:** Autonomous gap analyst.
* **Execution Flow:**
  * Periodically scans `ResearchMemory` nodes and aggregates findings by topic.
  * Identifies **Research Gaps**: Topics where confidence is low (≤ 0.55) or evidence count is shallow (≤ 3 entries).
  * Automatically creates `AgendaItem`s with computed priority levels (1 to 10).
  * Submits high-priority agenda tasks to `AsyncScheduler` for background execution.

### 2.3. AsyncScheduler & Priority Execution (`src/runtime/scheduler.py`)
* **Role:** Priority-based task queue dispatcher.
* **Task Queueing:** Queue tasks by `TaskPriority`:
  * `1 = CRITICAL` (User interactive requests)
  * `5 = DEFAULTS` (Scheduled tenant workflow requests)
  * `10 = BACKGROUND` (ResearchAgenda gaps scans)
* **Starvation Prevention:** Boosts the priority of long-waiting low-priority tasks periodically to ensure even cluster scheduling.

### 2.4. Worker Pool (`src/runtime/worker_pool.py`)
* **Role:** Manages concurrent worker threads and `asyncio.Task` runtimes.
* **Thread Throttling:** Keeps worker concurrency bounded by the host hardware capacity (concurrency default: `cpu_count * 2`).

### 2.5. Distributed Manager (`src/runtime/distributed_manager.py`)
* **Role:** Coordinates cluster node synchronization using Redis.
* **Features:**
  * Distributed Locks (`Redlock` pattern) to guarantee that unique background agenda items are executed by only one node.
  * Node health heartbeats with automated failover handling.
* **Failure Edge Cases:** If a node running a critical research workflow dies, the distributed manager catches the heartbeat loss and automatically re-assigns the task back to an active scheduler queue.

---

## 🔄 3. State Transition Lifecycle

The state transitions of a `ResearchTask` and `WorkflowRecord` must strictly follow this flowchart:

```
                  ┌───────────────┐
                  │    pending    │
                  └───────┬───────┘
                          │ task starts
                          ▼
                  ┌───────────────┐
                  │    running    │
                  └──────┬──────┬─┘
        error / abort    │      │ complete
       ┌─────────────────┘      └────────────────┐
       ▼                                         ▼
┌───────────────┐                         ┌───────────────┐
│    failed     │                         │   completed   │
└───────────────┘                         └───────────────┘
```

* **Failed Cleanup:** When a task moves to `failed`, the system logs the full error traceback in `error_message`, terminates active agent reasoning threads, and releases reserved tenant tokens immediately.
