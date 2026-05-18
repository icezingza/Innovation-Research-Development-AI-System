// API client for NamoNexus Control Center
// All calls proxy through Vite dev server to FastAPI at 127.0.0.1:8085

const BASE = import.meta.env.DEV ? '/api' : ''

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

// --- Types ---
export interface HealthStatus {
  status: string
  version: string
  timestamp: string
  services?: Record<string, string>
}

export interface ComplexityResult {
  task_preview: string
  complexity_score: number
  strategy: string
  inference_tier: string
  agents_required: number
  allocated_tokens: number
}

export interface SelfHealPatch {
  patch_id: string
  target_agent: string
  adjusted_weight: Record<string, number> | null
  prompt_injection: string | null
  status: string
}

export interface RedTeamReport {
  session_id: string
  total_attacks: number
  blocked: number
  passed_through: number
  rate_limited: number
  block_rate_pct: number
  total_time_seconds: number
  verdict: 'FORTRESS_SOLID' | 'NEEDS_REINFORCEMENT'
  category_breakdown: Record<string, { total: number; blocked: number }>
}

export interface FinOpsMetrics {
  tenant_id: string
  tokens_used: number
  tokens_limit: number
  requests_today: number
  cost_usd: number
}

// --- API calls ---
export const api = {
  health: (): Promise<HealthStatus> => fetchJSON('/health'),

  complexity: (task: string): Promise<ComplexityResult> =>
    fetchJSON('/autonomy/complexity', {
      method: 'POST',
      body: JSON.stringify({ task }),
    }),

  selfHeal: (event_type: string, context = {}): Promise<{ patch_applied: SelfHealPatch }> =>
    fetchJSON('/autonomy/self-heal', {
      method: 'POST',
      body: JSON.stringify({ event_type, context }),
    }),

  healingRules: (agent_id = 'global'): Promise<{ active_rules: SelfHealPatch[]; count: number }> =>
    fetchJSON(`/autonomy/self-heal/rules?agent_id=${agent_id}`),

  redTeam: (attack_rounds = 5): Promise<RedTeamReport> =>
    fetchJSON('/autonomy/red-team/run', {
      method: 'POST',
      body: JSON.stringify({ target_endpoint: '/research/tasks', attack_rounds }),
    }),

  ragIngest: (
    corpus_name: string,
    text: string,
    options: { domain: string; min_tokens: number; max_tokens: number; overlap_tokens: number }
  ): Promise<any> =>
    fetchJSON('/autonomy/rag/ingest', {
      method: 'POST',
      body: JSON.stringify({ corpus_name, text, ...options }),
    }),

  finops: (tenantId: string): Promise<FinOpsMetrics> =>
    fetchJSON(`/tenants/${tenantId}/finops`),

  roi: (tenantId: string): Promise<any> =>
    fetchJSON(`/tenants/${tenantId}/roi`),
}
