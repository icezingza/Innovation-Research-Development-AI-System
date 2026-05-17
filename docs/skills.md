# 🛠️ Skill System & Context7 Integration — NamoNexus

## 🚀 1. Dynamic Skill Packages Architecture

NamoNexus leverages a modular **Skill System** to dynamically extend the capabilities of active AI agents at runtime. Instead of hardcoding tools or embedding static prompt instructions, agents load domain-specific skills from standardized packages.

```
┌────────────────────────────────────────────────────────┐
│                   Standard Skill Package               │
├────────────────────────────────────────────────────────┤
│ SKILL.md     — Frontmatter metadata + MD instruction  │
│ scripts/     — Helper tools and python execution files │
│ examples/    — Sample inputs and references           │
│ resources/   — Standard templates and configurations   │
└────────────────────────────────────────────────────────┘
```

Each skill folder contains:
1. **`SKILL.md` (Required):** Contains YAML frontmatter metadata (defining target agents, description, and dependencies) followed by rich markdown usage patterns.
2. **`scripts/`:** Custom utility scripts loaded dynamically into agent reasoning environments.
3. **`examples/` & `resources/`:** Multi-shot prompt training guides and configuration constants.

---

## 🔍 2. Documentation Lookup & Context7 CLI Integration

To avoid the **"Claude Guessing API Syntax"** problem (where AI models guess how third-party libraries or internal tools operate based on outdated training data), NamoNexus implements the **Context7 CLI Integration**.

Whenever an agent or developer needs to utilize, configure, or debug a library, they **MUST** fetch up-to-date documentation using the Context7 API instead of relying on generic training knowledge.

### 2.1. The Context7 CLI (`ctx7`) Tool
* **Verify CLI presence:**
  ```bash
  npx ctx7@latest --help
  ```
* **Step 1: Resolve Library Name to ID**
  Always perform this step first to identify the correct `/org/project` ID.
  ```bash
  npx ctx7@latest library react "How to clean up useEffect with async operations"
  ```
* **Step 2: Query Targeted Documentation**
  Fetch high-relevance code and info snippets matching the precise question context:
  ```bash
  npx ctx7@latest docs /facebook/react "React useEffect cleanup function with async operations"
  ```

---

## 🧩 3. MCP Integration Guidelines

NamoNexus coordinates external capabilities by registering Model Context Protocol (MCP) server handlers in the backend runtime lifecycle.

### 3.1. Registering MCP Servers
MCP configurations are registered inside `mcp_config.json`:
```json
{
  "mcpServers": {
    "cloudrun": {
      "command": "npx",
      "args": ["-y", "@google-cloud/cloud-run-mcp"]
    },
    "github-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN"
      }
    }
  }
}
```

### 3.2. Agent MCP Execution Flow
1. **Tool Discovery:** The `ResearchAgent` inspects registered MCP servers to discover available tools.
2. **Context Resolution:** If a tool matches the task requirement, the agent automatically executes the MCP tool call (e.g. `mcp_github-mcp-server_search_code`) to pull code, rather than grepping raw disk workspace folders.
3. **Prompt Injection:** Output results are formatted and injected as a strict markdown snippet back into the `RecursiveReasoningLoop`.
