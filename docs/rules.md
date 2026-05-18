# 📜 Project Rules & Developer Guidelines — NamoNexus

## 🚀 1. The NRE v5.0.0 Sovereign Standard

NamoNexus is a production-grade, highly optimized enterprise platform. All development must strictly adhere to the following **architectural boundaries** to ensure system stability, modularity, and security.

---

## 🛠️ 2. Coding & Quality Standards

### 2.1. Backend Development (FastAPI + AsyncIO)
* **100% Async/Await:** Absolutely no synchronous blocking operations are permitted inside API endpoints or agent execution loops.
  * *Bad:* `time.sleep(5)` or `requests.get(url)`
  * *Good:* `await asyncio.sleep(5)` or `async with httpx.AsyncClient() as client: await client.get(url)`
* **Type Safety:** Strict Python type hints are required for every function signature and class definition. Avoid `Any` unless explicitly justified in comments.
* **Pydantic v2 Models:** Enforce strict validation schemas for all request payloads and response entities.

### 2.2. Frontend Development (React + Vite + TS)
* **Zero `any` Types:** The TS compiler is configured with `noImplicitAny: true`. Use strict custom interface types.
* **Display Syncs:** Use the `useNamoSocket` / `useWorkflowStream` hooks to handle all streaming websocket and SSE interface updates. Avoid ad-hoc polling loops.

### 2.3. Database Migrations (Alembic)
* **Single Base Declarative:** All database entities must inherit from the shared schema declarative `Base`.
* **Automated Migrations:** Every database modification must be implemented via async-enabled Alembic migrations at `/alembic/versions`. Run upgrades with `alembic upgrade head`.

---

## 🔒 3. Security & Secret Management

1. **Zero Secret Hardcoding:** Never hardcode passwords, GCP keys, database URLs, or AI credentials inside source code.
2. **GCP Secret Manager:** Enforce the use of `backend/namo_core/config/gcp_secrets.py` (or project equivalent configuration imports) to fetch credentials dynamically from Google Cloud Secret Manager at runtime.
3. **Environment Isolation:** Keep `.env` files strictly added to `.gitignore`. Check `.env.example` to see required workspace parameters.
4. **Data Privacy:** Avoid logging raw LLM generation payloads or sensitive customer details in production console logs.

---

## 🏁 4. Dev Workflow & CI/CD Quality Gates

### 4.1. Version Control & Git Commits
* **Conventional Commits:** Git commits must follow structural tags: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
* **Jira Gating:** Commits must include a Jira issue ticket key to facilitate tracing:
  * *Example:* `feat: [NN-123] add dynamic agent spawner router`

### 4.2. Pre-Commit Verification (Git Hooks)
Before pushing any branches, the following checks must pass locally:
1. **Linter & Formatting:** Run Ruff check and format:
   ```bash
   ruff check .
   ruff format .
   ```
2. **Test Suite Execution:** The entire unit and integration test suite must execute successfully with zero failures:
   ```bash
   pytest
   ```
3. **No Leaks Gate:** Git pre-commit hooks will automatically scan for credentials, blocking commits containing API keys.
