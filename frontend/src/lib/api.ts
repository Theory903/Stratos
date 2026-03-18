import axios from "axios"

export function normalizeBaseUrl(baseUrl: string, pathPrefix = ""): string {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "")
  if (!pathPrefix) {
    return normalizedBaseUrl
  }

  const normalizedPathPrefix = pathPrefix.startsWith("/") ? pathPrefix : `/${pathPrefix}`
  return normalizedBaseUrl.endsWith(normalizedPathPrefix)
    ? normalizedBaseUrl
    : `${normalizedBaseUrl}${normalizedPathPrefix}`
}

const API_URLS = {
  dataFabric: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000",
    "/api/v1"
  ),
  dataFabricV2: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000",
    "/api/v2"
  ),
  research: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000",
    "/api/v2/research"
  ),
  ml: normalizeBaseUrl(process.env.NEXT_PUBLIC_ML_SERVICE_URL ?? "http://localhost:8003/ml"),
  nlp: normalizeBaseUrl(process.env.NEXT_PUBLIC_NLP_SERVICE_URL ?? "http://localhost:8004/nlp"),
  orchestrator: normalizeBaseUrl(
    process.env.NEXT_PUBLIC_ORCHESTRATOR_URL ?? "http://localhost:8005"
  ),
}

export interface SnapshotMeta {
  entity_type: string
  entity_id: string
  as_of: string | null
  freshness: "fresh" | "stale" | "pending"
  refresh_enqueued: boolean
  feature_version: string | null
  provider_set: string[]
}

export interface SnapshotEnvelope<T> {
  data: T
  meta: SnapshotMeta
}

export interface PendingSnapshot {
  status: "pending"
  entity_type: string
  entity_id: string
  refresh_enqueued: boolean
  suggested_retry_seconds: number
}

type PendingHandler = (pending: PendingSnapshot, attempt: number) => void

const SNAPSHOT_CACHE_TTL_MS = 3000
const snapshotCache = new Map<string, { expiresAt: number; value: SnapshotEnvelope<unknown> }>()
const snapshotInFlight = new Map<
  string,
  {
    promise: Promise<SnapshotEnvelope<unknown>>
    subscribers: Set<PendingHandler>
  }
>()

async function wait(milliseconds: number): Promise<void> {
  await new Promise((resolve) => {
    globalThis.setTimeout(resolve, milliseconds)
  })
}

function getSnapshotCacheKey(path: string, attempts: number): string {
  return `${path}::${attempts}`
}

function notifyPending(
  subscribers: Set<PendingHandler>,
  pending: PendingSnapshot,
  attempt: number
): void {
  for (const subscriber of subscribers) {
    subscriber(pending, attempt)
  }
}

async function pollSnapshot<T>(
  path: string,
  onPending?: PendingHandler,
  attempts = 8
): Promise<SnapshotEnvelope<T>> {
  const cacheKey = getSnapshotCacheKey(path, attempts)
  const cachedSnapshot = snapshotCache.get(cacheKey)
  if (cachedSnapshot && cachedSnapshot.expiresAt > Date.now()) {
    return cachedSnapshot.value as SnapshotEnvelope<T>
  }

  const inFlight = snapshotInFlight.get(cacheKey)
  if (inFlight) {
    if (onPending) {
      inFlight.subscribers.add(onPending)
    }
    return inFlight.promise as Promise<SnapshotEnvelope<T>>
  }

  const subscribers = new Set<PendingHandler>()
  if (onPending) {
    subscribers.add(onPending)
  }

  const promise = (async () => {
    try {
      for (let attempt = 0; attempt < attempts; attempt += 1) {
        const response = await api.dataFabricV2.get<SnapshotEnvelope<T> | PendingSnapshot>(path, {
          params: { include_meta: true },
          validateStatus: (status) => status === 200 || status === 202,
        })

        if (response.status === 200) {
          const readySnapshot = response.data as SnapshotEnvelope<T>
          snapshotCache.set(cacheKey, {
            expiresAt: Date.now() + SNAPSHOT_CACHE_TTL_MS,
            value: readySnapshot as SnapshotEnvelope<unknown>,
          })
          return readySnapshot
        }

        const pending = response.data as PendingSnapshot
        notifyPending(subscribers, pending, attempt)
        const retrySeconds = Math.min(Math.max(pending.suggested_retry_seconds ?? 2, 1), 10)
        await wait(retrySeconds * 1000)
      }

      throw new Error(`Snapshot did not become ready for ${path}`)
    } finally {
      snapshotInFlight.delete(cacheKey)
    }
  })()

  snapshotInFlight.set(cacheKey, { promise: promise as Promise<SnapshotEnvelope<unknown>>, subscribers })
  return promise
}

export function clearSnapshotState(): void {
  snapshotCache.clear()
  snapshotInFlight.clear()
}

export const api = {
  dataFabric: axios.create({ baseURL: API_URLS.dataFabric }),
  dataFabricV2: axios.create({ baseURL: API_URLS.dataFabricV2 }),
  researchClient: axios.create({ baseURL: API_URLS.research }),
  ml: axios.create({ baseURL: API_URLS.ml }),
  nlp: axios.create({ baseURL: API_URLS.nlp }),
  orchestrator: axios.create({ baseURL: API_URLS.orchestrator }),

  pollDataFabricV2: pollSnapshot,

  // Research/RAG API
  research: {
    // Documents
    uploadDocument: async (workspaceId: string, file: File, userId?: string) => {
      const formData = new FormData()
      formData.append("file", file)
      const response = await api.researchClient.post("/documents/upload", formData, {
        params: { workspace_id: workspaceId, user_id: userId },
        headers: { "Content-Type": "multipart/form-data" },
      })
      return response.data
    },

    listDocuments: async (workspaceId: string, limit = 50, offset = 0) => {
      const response = await api.researchClient.get("/documents", {
        params: { workspace_id: workspaceId, limit, offset },
      })
      return response.data
    },

    getDocument: async (documentId: string) => {
      const response = await api.researchClient.get(`/documents/${documentId}`)
      return response.data
    },

    getDocumentChunks: async (documentId: string) => {
      const response = await api.researchClient.get(`/documents/${documentId}/chunks`)
      return response.data
    },

    // Briefs
    createBrief: async (data: {
      workspace_id: string
      title: string
      thesis?: string
      status?: string
      linked_positions?: string[]
      linked_events?: string[]
      created_by?: string
    }) => {
      const response = await api.researchClient.post("/briefs", data)
      return response.data
    },

    listBriefs: async (
      workspaceId: string,
      options?: { status?: string; linked_position?: string; limit?: number; offset?: number }
    ) => {
      const response = await api.researchClient.get("/briefs", {
        params: { workspace_id: workspaceId, ...options },
      })
      return response.data
    },

    getBrief: async (briefId: string) => {
      const response = await api.researchClient.get(`/briefs/${briefId}`)
      return response.data
    },

    updateBrief: async (
      briefId: string,
      data: {
        title?: string
        thesis?: string
        status?: string
        linked_positions?: string[]
        linked_events?: string[]
      }
    ) => {
      const response = await api.researchClient.put(`/briefs/${briefId}`, data)
      return response.data
    },

    getBriefEvidence: async (briefId: string) => {
      const response = await api.researchClient.get(`/briefs/${briefId}/evidence`)
      return response.data
    },

    // Retrieval
    queryEvidence: async (data: {
      query: string
      workspace_id: string
      filters?: Record<string, any>
      top_k?: number
    }) => {
      const response = await api.researchClient.post("/retrieval/query", data)
      return response.data
    },

    // Evidence
    addEvidence: async (data: { brief_id: string; chunk_id: string; note?: string }) => {
      const response = await api.researchClient.post("/evidence", data)
      return response.data
    },

    getEvidence: async (evidenceId: string) => {
      const response = await api.researchClient.get(`/evidence/${evidenceId}`)
      return response.data
    },
  },

  streamOrchestrate: async (query: string, onEvent: (type: string, data: any) => void) => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    if (!reader) {
      return
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) {
          continue
        }
        const [eventLine, dataLine] = line.split("\n")
        const type = eventLine.replace("event: ", "").trim()
        const data = JSON.parse(dataLine.replace("data: ", "").trim())
        onEvent(type, data)
      }
    }
  },

  streamOrchestrateV3: async (
    query: string,
    onEvent: (type: string, data: any) => void,
    options?: { threadId?: string; userId?: string }
  ) => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v3/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        thread_id: options?.threadId,
        user_id: options?.userId,
      }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    if (!reader) {
      return
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) {
          continue
        }
        const [eventLine, dataLine] = line.split("\n")
        const type = eventLine.replace("event: ", "").trim()
        const data = JSON.parse(dataLine.replace("data: ", "").trim())
        onEvent(type, data)
      }
    }
  },

  streamOrchestrateV4: async (
    query: string,
    onEvent: (type: string, data: any) => void,
    options?: { threadId?: string; userId?: string; workspaceId?: string; roleLens?: string; responseModeHint?: string }
  ) => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v4/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        thread_id: options?.threadId,
        user_id: options?.userId,
        workspace_id: options?.workspaceId ?? "default",
        role_lens: options?.roleLens,
        response_mode_hint: options?.responseModeHint,
      }),
    })

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    if (!reader) {
      return
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) {
          continue
        }
        const [eventLine, dataLine] = line.split("\n")
        const type = eventLine.replace("event: ", "").trim()
        const data = JSON.parse(dataLine.replace("data: ", "").trim())
        onEvent(type, data)
      }
    }
  },

  /**
   * Resume a run that was interrupted at an HITL approval gate.
   *
   * @param runId    - Opaque run identifier returned by the orchestrator
   * @param threadId - Thread the run belongs to
   * @param decision - "approve" | "reject"
   * @param note     - Optional free-text note from the reviewer
   */
  resumeRun: async (
    runId: string,
    threadId: string,
    decision: "approve" | "reject",
    note?: string
  ): Promise<{ status: string; message?: string }> => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v4/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId, thread_id: threadId, decision, note }),
    })

    if (!response.ok) {
      throw new Error(`Resume failed: ${response.status} ${response.statusText}`)
    }

    return response.json() as Promise<{ status: string; message?: string }>
  },

  // --------------------------------------------------------------------------
  // V5 Orchestration (LangGraph-native)
  // --------------------------------------------------------------------------

  /**
   * Stream V5 orchestration with SSE events.
   * 
   * @param query - User query
   * @param onEvent - Callback for each SSE event
   * @param options - Optional params (threadId, userId, workspaceId, mode)
   */
  orchestrateV5Stream: async (
    query: string,
    onEvent: (type: string, data: any) => void,
    options?: {
      threadId?: string
      userId?: string
      workspaceId?: string
      mode?: string
    }
  ) => {
    console.log("V5 stream: starting request for query:", query)
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v5/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        thread_id: options?.threadId,
        user_id: options?.userId,
        workspace_id: options?.workspaceId ?? "default",
        mode: options?.mode,
      }),
    })

    console.log("V5 stream: response status:", response.status, response.statusText)

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`V5 stream failed: ${response.status} ${response.statusText} - ${errorText}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    if (!reader) {
      return
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n\n")
      buffer = lines.pop() || ""

      for (const line of lines) {
        if (!line.trim()) {
          continue
        }
        const [eventLine, dataLine] = line.split("\n")
        if (!eventLine || !dataLine) {
          continue
        }
        const type = eventLine.replace("event: ", "").trim()
        try {
          const data = JSON.parse(dataLine.replace("data: ", "").trim())
          try {
            onEvent(type, data)
          } catch (callbackError) {
            console.error("V5 stream event callback error:", callbackError)
          }
        } catch (parseError) {
          console.warn("Failed to parse SSE event:", line, parseError)
        }
      }
    }
    
    // Ensure we read any remaining buffer
    if (buffer.trim()) {
      console.log("V5 stream: remaining buffer:", buffer)
    }
  },

  /**
   * Execute V5 orchestration synchronously (non-streaming).
   */
  orchestrateV5: async (
    query: string,
    options?: {
      threadId?: string
      userId?: string
      workspaceId?: string
      mode?: string
    }
  ) => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v5`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        thread_id: options?.threadId,
        user_id: options?.userId,
        workspace_id: options?.workspaceId ?? "default",
        mode: options?.mode,
      }),
    })

    if (!response.ok) {
      throw new Error(`V5 orchestration failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Resume V5 orchestration from an approval decision.
   */
  resumeV5Thread: async (
    threadId: string,
    approvalId: string,
    approved: boolean,
    note?: string
  ) => {
    const response = await fetch(`${API_URLS.orchestrator}/orchestrate/v5/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: threadId,
        approval_id: approvalId,
        approved,
        note,
      }),
    })

    if (!response.ok) {
      throw new Error(`Resume failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  },

  /**
   * Get V5 thread state for reconnection/hydration.
   */
  getV5ThreadState: async (threadId: string) => {
    const response = await fetch(
      `${API_URLS.orchestrator}/orchestrate/v5/thread/${threadId}`
    )

    if (!response.ok) {
      if (response.status === 404) {
        return null
      }
      throw new Error(`Failed to get thread state: ${response.status}`)
    }

    return response.json()
  },

  // --------------------------------------------------------------------------
  // Decisions
  // --------------------------------------------------------------------------

  decisions: {
    create: async (data: {
      workspace_id: string
      thread_id?: string
      run_id?: string
      type: string
      inputs: Record<string, unknown>
      outputs?: Record<string, unknown>
      status?: string
      confidence_score?: number
      risk_band?: string
      linked_positions?: string[]
      linked_events?: string[]
      linked_briefs?: string[]
      created_by?: string
      note?: string
    }) => {
      const response = await api.orchestrator.post("/decisions", data)
      return response.data
    },

    list: async (params: {
      workspace_id: string
      type?: string
      status?: string
      limit?: number
      offset?: number
    }) => {
      const response = await api.orchestrator.get("/decisions", { params })
      return response.data
    },

    get: async (decisionId: string) => {
      const response = await api.orchestrator.get(`/decisions/${decisionId}`)
      return response.data
    },

    update: async (
      decisionId: string,
      data: {
        status?: string
        note?: string
        outputs?: Record<string, unknown>
      }
    ) => {
      const response = await api.orchestrator.put(`/decisions/${decisionId}`, data)
      return response.data
    },

    history: async (params: {
      workspace_id: string
      position?: string
      event?: string
      since?: string
      limit?: number
    }) => {
      const response = await api.orchestrator.get("/decisions/history/list", { params })
      return response.data
    },

    pending: async (workspaceId: string) => {
      const response = await api.orchestrator.get("/decisions/queue/pending", {
        params: { workspace_id: workspaceId },
      })
      return response.data
    },
  },

  signals: {
    getOverview: async (workspaceId: string, role?: string, focus?: string, limit = 20) => {
      const response = await api.orchestrator.get("/signals/overview", {
        params: { workspace_id: workspaceId, role: role || "pm", focus, limit },
      })
      return response.data
    },

    getAttention: async (workspaceId: string, role?: string, limit = 10) => {
      const response = await api.orchestrator.get("/signals/attention", {
        params: { workspace_id: workspaceId, role: role || "pm", limit },
      })
      return response.data
    },

    create: async (data: {
      workspace_id: string
      type: "risk" | "opportunity" | "event" | "market" | "research"
      title: string
      detail: string
      urgency?: number
      confidence?: number
      linked_positions?: string[]
      linked_events?: string[]
      linked_briefs?: string[]
    }) => {
      const response = await api.orchestrator.post("/signals", data)
      return response.data
    },
  },
}

export interface WorldState {
  interest_rate: number
  inflation: number
  liquidity_index: number
  geopolitical_risk: number
  volatility_index: number
  commodity_index: number
}

export interface CompanySnapshot {
  ticker: string
  name: string
  earnings_quality: number
  leverage_ratio: number
  free_cash_flow_stability: number
  fraud_score: number
  moat_score: number
}

export interface CountrySnapshot {
  country_code: string
  debt_gdp: number
  fx_reserves: number
  fiscal_deficit: number
  political_stability: number
  currency_volatility: number
}

export interface MarketBar {
  ticker: string
  asset_class: string
  timestamp: string
  open: string
  high: string
  low: string
  close: string
  volume: number
}

export interface MarketRegimeSnapshot {
  regime_label: string
  confidence: number
  factor_summary: string | Record<string, string>
}

export interface EventItem {
  title: string
  summary: string
  region: string
  category: string
  entities: string[]
  urgency: number
  importance: number
}

export interface EventCluster {
  cluster_id: string
  region: string
  category: string
  headline: string
  event_count: number
  importance: number
}

export interface EventPulse {
  scope: string
  headline: string
  event_count: number
  dominant_theme: string
  average_urgency: number
  average_importance: number
  highlights: string[]
  upcoming_events?: Array<{ title?: string; date?: string; type?: string; impact?: string }>
}

export interface SignalItem {
  signal_id: string
  type: "risk" | "opportunity" | "event" | "market" | "research"
  title: string
  detail: string
  urgency: number
  confidence: number
  freshness: "fresh" | "stale"
  linked_entities: {
    positions?: string[]
    events?: string[]
    briefs?: string[]
  }
  score: number
  created_at: string
}

export interface CompareMetricSnapshot {
  entity_type: string
  entity_id: string
  metric: string
  current: number
  average: number
  minimum: number
  maximum: number
  percentile_rank: number
  z_score: number
  series: number[]
}

export interface CompareEntitySnapshot {
  entity_type: string
  entity_id: string
  current: Record<string, number>
  previous: Record<string, number> | null
  deltas: Record<string, number>
}

export interface HistoricalRegimeSnapshot {
  current: MarketRegimeSnapshot
  analogs: Array<{
    regime_label: string
    confidence: number
    similarity: number
    as_of: string
    factor_summary: string | Record<string, string>
  }>
}

export interface AnomalySnapshot extends CompareMetricSnapshot {
  severity: "low" | "medium" | "high"
  explanation: string
}

export interface PortfolioPosition {
  ticker: string
  quantity: number
  average_cost: number
  asset_class: string
}

export interface PortfolioSnapshot {
  name: string
  benchmark: string
  positions: PortfolioPosition[]
  constraints: Record<string, unknown>
}

export interface PortfolioExposureSnapshot {
  name: string
  total_market_value: number
  asset_class_exposure: Record<string, number>
  top_positions: Array<{
    ticker: string
    quantity: number
    average_cost: number
    asset_class: string
    last_price: number
    market_value: number
    weight: number
  }>
}

export interface PortfolioRiskSnapshot {
  name: string
  estimated_daily_volatility: number
  value_at_risk_95: number
  concentration_risk: number
  regime: MarketRegimeSnapshot | null
  risk_flags: string[]
}

export interface PortfolioScenarioResult {
  scenario: string
  portfolio_name: string
  estimated_total_pnl_impact: number
  positions: Array<{
    ticker: string
    asset_class: string
    shock: number
    estimated_pnl_impact: number
  }>
}

export interface PortfolioRebalanceResult {
  portfolio_name: string
  suggestions: Array<{
    ticker: string
    current_weight: number
    target_weight: number
    action: string
  }>
  rationale: string
}

export interface DecisionQueueSnapshot {
  portfolio_name: string
  top_risks: Array<{ title: string; why: string }>
  top_opportunities: Array<{ title: string; why: string }>
  watchlist_changes: string[]
  recommended_actions: string[]
  regime: MarketRegimeSnapshot | null
}

export function formatRegimeFactorSummary(
  factorSummary: MarketRegimeSnapshot["factor_summary"]
): string {
  if (typeof factorSummary === "string") {
    return factorSummary
  }

  const entries = Object.entries(factorSummary)
  if (entries.length === 0) {
    return ""
  }

  return entries.map(([key, value]) => `${key}: ${value}`).join(" · ")
}

export interface PredictionRequest {
  features: number[]
  model?: string
}

export interface EvidenceBlock {
  title: string
  detail: string
}

export interface FinanceDecisionPacket {
  instrument: string
  action: string
  confidence: number
  score: number
  thesis: string
  entry_zone: string
  stop_loss: string
  take_profit: string
  max_holding_period: string
  position_size_pct: number
  capital_at_risk: number
  kill_switch_reasons: string[]
}

export interface FinanceAnalystSignal {
  analyst: string
  instrument: string
  signal_score: number
  confidence: number
  direction: string
  thesis: string
  evidence_ids: string[]
  citations: string[]
  freshness_ok: boolean
}

export interface FinanceRiskVerdict {
  allowed: boolean
  regime: string
  value_at_risk_95: number
  concentration_risk: number
  position_size_pct: number
  capital_at_risk: number
  kill_switch_reasons: string[]
  rationale: string
}

export interface FinanceProviderHealthItem {
  provider: string
  status: string
  freshness?: SnapshotMeta["freshness"] | null
  lag_seconds?: number | null
  detail?: string | null
  source_coverage?: number | null
}

export interface FinanceProviderHealthSummary {
  overall_status: string
  summary?: string | null
  checked_at?: string | null
  providers: FinanceProviderHealthItem[]
  notes?: string[]
}

export interface FinanceReplaySummary {
  as_of?: string | null
  action?: string | null
  confidence?: number | null
  realized_move?: number | null
  outcome_label?: string | null
  veto_reason?: string | null
  notes?: string[]
}

export interface AgentTrace {
  path?: string
  answer_mode?: string
  degrade_reason?: string | null
  delegate_runtime?: string
  mode?: string
  instrument?: string
  supervisor_plan?: {
    active_analysts?: string[]
    reasoning_mode?: string
    risk_posture?: string
    requires_debate?: boolean
    rationale?: string
  } | null
  feedback_summary?: {
    observations?: number
    avg_realized_move?: number
    veto_rate?: number
    last_action?: string | null
    last_confidence?: number | null
  } | null
  [key: string]: unknown
}

export interface FreshnessSummary {
  market_ready: boolean
  order_book_ready: boolean
  news_count: number
  social_count: number
  policy_count: number
  notes: string[]
  watch_items: string[]
  [key: string]: unknown
}

export interface AgentResponse {
  status?: string
  thread_id?: string
  run_id?: string
  approval_requests?: Array<{ approval_id: string; reason: string; required: boolean }>
  decision?: string
  recommendation: string
  confidence_score: number
  confidence_calibration?: string
  risk_band: string
  scenarios?: any[]
  scenario_tree?: any[]
  worst_case?: string
  intent?: string
  role?: string
  summary?: string
  key_findings?: string[]
  historical_context?: string[]
  portfolio_impact?: string[]
  recommended_actions?: string[]
  watch_items?: string[]
  data_quality?: string[]
  evidence_blocks?: EvidenceBlock[]
  specialist_views?: Array<{
    specialist: string
    title: string
    summary: string
    verdict?: string | null
    claims?: string[]
    concerns?: string[]
  }>
  decision_packet?: FinanceDecisionPacket
  analyst_signals?: FinanceAnalystSignal[]
  risk_verdict?: FinanceRiskVerdict
  freshness_summary?: FreshnessSummary
  provider_health?: FinanceProviderHealthSummary
  replay_summary?: FinanceReplaySummary
  degrade_reason?: string | null
  trace?: AgentTrace
}
