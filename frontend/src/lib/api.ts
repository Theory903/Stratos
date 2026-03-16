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
  ml: axios.create({ baseURL: API_URLS.ml }),
  nlp: axios.create({ baseURL: API_URLS.nlp }),
  orchestrator: axios.create({ baseURL: API_URLS.orchestrator }),

  pollDataFabricV2: pollSnapshot,

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

export interface AgentResponse {
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
  evidence_blocks?: Array<{ title: string; detail: string }>
}
