import type { AgentResponse, FinanceAnalystSignal, FinanceProviderHealthSummary } from "@/lib/api"
import { roleLenses, responseModes } from "./constants"
import type { RoleLens, ResponseMode } from "./types"

// ─── Label helpers ────────────────────────────────────────────────────────────

export function readableToolName(toolName: string) {
  return toolName
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export function readableEngineName(value?: string) {
  if (!value) {
    return "STRATOS runtime"
  }
  const normalized = value.toLowerCase()
  if (normalized === "langchain_v3" || normalized === "adaptive_agent") {
    return "LangChain adaptive agent"
  }
  if (normalized === "finance_council") {
    return "Finance council"
  }
  if (normalized === "v4_graph") {
    return "V4 graph runtime"
  }
  return readableToolName(normalized)
}

export function readableNodeName(nodeName: string) {
  const mapping: Record<string, string> = {
    intake_router: "routing",
    context_builder: "context load",
    freshness_adjudicator: "freshness check",
    execution_planner: "execution plan",
    sufficiency_gate_1: "early stop check",
    retrieval_gate: "retrieval gate",
    retrieval_planner: "retrieval plan",
    retriever: "source retrieval",
    reranker: "source rerank",
    retrieval_judge: "grounding judge",
    specialist_admission_gate: "specialist gate",
    macro_subgraph: "macro view",
    portfolio_subgraph: "portfolio manager",
    events_subgraph: "event pulse",
    research_subgraph: "quality research",
    risk_subgraph: "risk judge",
    claim_auditor: "claim audit",
    response_controller: "response control",
    approval_gate: "approval check",
    renderer: "answer render",
    output_packager: "output package",
  }
  return mapping[nodeName] ?? readableToolName(nodeName)
}

export function roleLabel(value?: string) {
  return roleLenses.find((lens) => lens.id === value)?.label ?? (value ? readableToolName(value) : "General LLM")
}

export function modeLabel(value?: string) {
  return responseModes.find((mode) => mode.id === value)?.label ?? (value ? readableToolName(value) : "Direct")
}

export function isRoleLens(value: string | null): value is RoleLens {
  return roleLenses.some((lens) => lens.id === value)
}

export function isResponseMode(value: string | null): value is ResponseMode {
  return responseModes.some((mode) => mode.id === value)
}

// ─── Formatting helpers ───────────────────────────────────────────────────────

export function formatPercent(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`
}

export function formatSignedNumber(value: number) {
  return value >= 0 ? `+${value.toFixed(2)}` : value.toFixed(2)
}

export function formatDurationSeconds(value: number) {
  if (value < 60) {
    return `${Math.round(value)}s`
  }
  if (value < 3600) {
    return `${Math.round(value / 60)}m`
  }
  return `${Math.round(value / 3600)}h`
}

export function formatTimestamp(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return parsed.toLocaleString()
}

// ─── Tone helpers ─────────────────────────────────────────────────────────────

export function metricToneFromScore(value: number): "positive" | "neutral" | "caution" {
  if (value >= 0.1) {
    return "positive"
  }
  if (value <= -0.1) {
    return "caution"
  }
  return "neutral"
}

export function directionTone(direction: string) {
  if (direction === "bullish") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900"
  }
  if (direction === "bearish") {
    return "border-amber-200 bg-amber-50 text-amber-900"
  }
  return "border-slate-200 bg-slate-50 text-slate-900"
}

export function decisionTone(action: string) {
  if (action === "BUY") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900"
  }
  if (action === "SELL" || action === "NO_TRADE") {
    return "border-amber-200 bg-amber-50 text-amber-900"
  }
  return "border-slate-200 bg-slate-50 text-slate-900"
}

export function decisionToneToMetricTone(action: string): "positive" | "neutral" | "caution" {
  if (action === "BUY") {
    return "positive"
  }
  if (action === "SELL" || action === "NO_TRADE") {
    return "caution"
  }
  return "neutral"
}

export function healthStatusClassName(status: string) {
  const normalized = status.toLowerCase()
  if (normalized === "healthy" || normalized === "ready") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900"
  }
  if (
    normalized === "degraded" ||
    normalized === "stale" ||
    normalized === "lagging" ||
    normalized === "down" ||
    normalized === "offline"
  ) {
    return "border-amber-200 bg-amber-50 text-amber-900"
  }
  return "border-slate-200 bg-slate-50 text-slate-900"
}

export function healthStatusTone(status: string): "positive" | "neutral" | "caution" {
  const normalized = status.toLowerCase()
  if (normalized === "healthy" || normalized === "ready") {
    return "positive"
  }
  if (
    normalized === "degraded" ||
    normalized === "stale" ||
    normalized === "lagging" ||
    normalized === "down" ||
    normalized === "offline"
  ) {
    return "caution"
  }
  return "neutral"
}

export function readableHealthStatus(status: string) {
  const normalized = status.toLowerCase()
  if (normalized === "healthy" || normalized === "ready") {
    return "Healthy"
  }
  if (normalized === "degraded" || normalized === "stale" || normalized === "lagging") {
    return "Degraded"
  }
  if (normalized === "down" || normalized === "offline") {
    return "Down"
  }
  return readableToolName(normalized)
}

// ─── Domain logic helpers ─────────────────────────────────────────────────────

export function hasFinancePayload(memo: AgentResponse) {
  return Boolean(
    memo.decision_packet ||
      memo.risk_verdict ||
      (memo.analyst_signals && memo.analyst_signals.length > 0) ||
      memo.freshness_summary ||
      memo.provider_health ||
      memo.replay_summary
  )
}

export function summarizeFinanceCouncilPayload(
  instrument: string | undefined,
  signalCount: number,
  freshnessSummary?: AgentResponse["freshness_summary"],
  providerHealth?: AgentResponse["provider_health"]
) {
  const readiness = freshnessSummary?.market_ready ? "market ready" : "market gated"
  const health = providerHealth?.overall_status ? `, ${providerHealth.overall_status} feeds` : ""
  return `${instrument ?? "Instrument"} council: ${signalCount} signals, ${readiness}${health}`
}

export function deriveProviderHealthStatus(
  freshnessSummary?: AgentResponse["freshness_summary"],
  analystSignals?: FinanceAnalystSignal[]
): string {
  if (freshnessSummary && (!freshnessSummary.market_ready || !freshnessSummary.order_book_ready)) {
    return "degraded"
  }

  if (analystSignals?.some((signal) => !signal.freshness_ok)) {
    return "degraded"
  }

  if (freshnessSummary || (analystSignals && analystSignals.length > 0)) {
    return "healthy"
  }

  return "unknown"
}

export function summarizeProviderCounts(health?: FinanceProviderHealthSummary) {
  const providers = health?.providers ?? []
  return providers.reduce(
    (counts, provider) => {
      const status = provider.status.toLowerCase()
      counts.total += 1
      if (status === "healthy" || status === "ready") {
        counts.healthy += 1
      } else if (status === "down" || status === "offline") {
        counts.down += 1
      } else if (status === "degraded" || status === "stale" || status === "lagging") {
        counts.degraded += 1
      } else {
        counts.unknown += 1
      }
      return counts
    },
    { total: 0, healthy: 0, degraded: 0, down: 0, unknown: 0 }
  )
}

// ─── Stream / metadata helpers ────────────────────────────────────────────────

export function pushMetadata(existing: string[] | undefined, next: string) {
  const items = [...(existing ?? []), next]
  return items.slice(-4)
}

export function isDisplayableMetadata(item: string) {
  const lower = item.toLowerCase()
  if (lower === "run pending" || lower.startsWith("route set by")) return false
  return item.trim().length > 0
}

export function summarizeToolText(value?: string) {
  if (!value) {
    return "No additional output."
  }
  return value.length > 280 ? `${value.slice(0, 277)}...` : value
}

export function summarizeStreamPayload(type: string, data: any) {
  if (type === "budget_update") {
    const policy = data?.policy ?? {}
    return `Budget: ${policy.max_specialist_count ?? 0} specialists, ${policy.max_external_calls ?? 0} external calls`
  }

  if (type === "node_started") {
    const node = data?.node
    if (typeof node === "string") {
      return `Running ${readableNodeName(node)}`
    }
  }

  if (type === "confidence_update") {
    const freshness = data?.freshness
    if (freshness) {
      return freshness.freshness_debt ? "Freshness debt detected" : "Internal data is fresh enough"
    }
    const renderContract = data?.render_contract
    if (renderContract?.answer_mode) {
      return `Answer mode: ${renderContract.answer_mode}`
    }
  }

  if (type === "termination_reason") {
    return `Stopped because: ${data?.termination ?? "graph completed"}`
  }

  if (type === "claim_audit_summary") {
    const count = Array.isArray(data?.claims) ? data.claims.length : 0
    return `Audited ${count} claim${count === 1 ? "" : "s"}`
  }

  if (type === "tool_result" || type === "source_found") {
    if (data?.title) {
      return data.title
    }
    if (data?.detail) {
      return String(data.detail)
    }
  }

  return typeof data === "string" ? data : "Progress updated"
}
