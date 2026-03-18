"use client"
import type { AgentResponse, FinanceAnalystSignal, FinanceDecisionPacket, FinanceProviderHealthSummary, FinanceReplaySummary, FinanceRiskVerdict } from "@/lib/api"
import { cn } from "@/lib/utils"
import { MetricChip } from "./MetricChip"
import { StructuredList } from "./StructuredList"
import { FinanceKeyValue } from "./FinanceKeyValue"
import {
  decisionTone,
  decisionToneToMetricTone,
  directionTone,
  formatDurationSeconds,
  formatPercent,
  formatSignedNumber,
  formatTimestamp,
  healthStatusClassName,
  healthStatusTone,
  metricToneFromScore,
  readableEngineName,
  readableHealthStatus,
  readableToolName,
  roleLabel,
  modeLabel,
  summarizeProviderCounts,
  deriveProviderHealthStatus,
} from "./utils"

// ─── RunOverviewPanel ──────────────────────────────────────────────────────────

export function RunOverviewPanel({
  memo,
  context,
}: {
  memo: AgentResponse
  context?: { intent: string; role: string; mode?: string; engine?: string }
}) {
  const engine = readableEngineName(memo.trace?.delegate_runtime ?? context?.engine ?? memo.trace?.mode)
  const answerMode = memo.trace?.answer_mode
  const path = memo.trace?.path
  const routeTone =
    memo.decision_packet || memo.risk_verdict || memo.analyst_signals?.length
      ? "border-cyan-200 bg-cyan-50 text-cyan-900"
      : memo.trace?.delegate_runtime
        ? "border-violet-200 bg-violet-50 text-violet-900"
        : "border-slate-200 bg-slate-50 text-slate-900"

  if (!engine && !answerMode && !path && !context?.intent) {
    return null
  }

  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Run Overview
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">
            {engine ?? "Adaptive STRATOS runtime"}
          </div>
        </div>
        <span className={cn("rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]", routeTone)}>
          {memo.decision_packet || memo.risk_verdict ? "finance" : memo.trace?.delegate_runtime ? "delegated" : "graph"}
        </span>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Intent" value={context?.intent ?? memo.intent ?? "research"} tone="neutral" />
        <MetricChip label="Role" value={roleLabel(context?.role ?? memo.role)} tone="neutral" />
        <MetricChip label="Format" value={answerMode ? readableToolName(answerMode) : modeLabel(context?.mode)} tone="neutral" />
        <MetricChip label="Path" value={path ? readableToolName(path) : "standard"} tone="neutral" />
      </div>
    </div>
  )
}

// ─── FinanceCouncilView ────────────────────────────────────────────────────────

export function FinanceCouncilView({
  decisionPacket,
  analystSignals,
  riskVerdict,
  freshnessSummary,
  providerHealth,
  replaySummary,
  degradeReason,
  trace,
}: {
  decisionPacket?: FinanceDecisionPacket
  analystSignals?: FinanceAnalystSignal[]
  riskVerdict?: FinanceRiskVerdict
  freshnessSummary?: AgentResponse["freshness_summary"]
  providerHealth?: AgentResponse["provider_health"]
  replaySummary?: AgentResponse["replay_summary"]
  degradeReason?: string | null
  trace?: AgentResponse["trace"]
}) {
  return (
    <div className="space-y-3">
      <FinanceStatusPanel
        decisionPacket={decisionPacket}
        analystSignals={analystSignals}
        riskVerdict={riskVerdict}
        freshnessSummary={freshnessSummary}
        providerHealth={providerHealth}
        replaySummary={replaySummary}
        degradeReason={degradeReason}
      />
      {trace && <FinanceSupervisorPanel trace={trace} />}
      {decisionPacket && <FinanceDecisionPanel packet={decisionPacket} />}
      {riskVerdict && <FinanceRiskPanel verdict={riskVerdict} />}
      {freshnessSummary && <FinanceFreshnessPanel summary={freshnessSummary} />}
      {providerHealth && <FinanceProviderHealthPanel health={providerHealth} />}
      {replaySummary && <FinanceReplayPanel summary={replaySummary} />}
      {analystSignals && analystSignals.length > 0 && <FinanceSignalsPanel signals={analystSignals} />}
    </div>
  )
}

// ─── FinanceStatusPanel ────────────────────────────────────────────────────────

function FinanceStatusPanel({
  decisionPacket,
  analystSignals,
  riskVerdict,
  freshnessSummary,
  providerHealth,
  replaySummary,
  degradeReason,
}: {
  decisionPacket?: FinanceDecisionPacket
  analystSignals?: FinanceAnalystSignal[]
  riskVerdict?: FinanceRiskVerdict
  freshnessSummary?: AgentResponse["freshness_summary"]
  providerHealth?: FinanceProviderHealthSummary
  replaySummary?: FinanceReplaySummary
  degradeReason?: string | null
}) {
  const action = decisionPacket?.action ?? (riskVerdict?.allowed === false ? "NO_TRADE" : "REVIEW")
  const healthStatus = providerHealth?.overall_status ?? deriveProviderHealthStatus(freshnessSummary, analystSignals)
  const providerCounts = summarizeProviderCounts(providerHealth)
  const analystFreshness = analystSignals?.filter((signal) => !signal.freshness_ok).length ?? 0
  const noTradeReason =
    action === "NO_TRADE"
      ? riskVerdict?.kill_switch_reasons[0] ?? decisionPacket?.kill_switch_reasons[0] ?? "The council vetoed trade entry."
      : null

  if (
    !decisionPacket &&
    !riskVerdict &&
    !freshnessSummary &&
    !providerHealth &&
    !replaySummary &&
    !degradeReason &&
    !(analystSignals && analystSignals.length > 0)
  ) {
    return null
  }

  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Finance Status
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">
            {action === "NO_TRADE" ? "Trade gated" : `${action} posture`}
          </div>
        </div>
        <div
          className={cn(
            "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
            decisionTone(action)
          )}
        >
          {action}
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Action" value={action} tone={decisionToneToMetricTone(action)} />
        <MetricChip
          label="Risk Gate"
          value={riskVerdict ? (riskVerdict.allowed ? "Approved" : "Vetoed") : "Pending"}
          tone={riskVerdict ? (riskVerdict.allowed ? "positive" : "caution") : "neutral"}
          detail={riskVerdict?.regime ? `Regime ${riskVerdict.regime}` : undefined}
        />
        <MetricChip
          label="Provider Health"
          value={readableHealthStatus(healthStatus)}
          tone={healthStatusTone(healthStatus)}
          detail={
            providerCounts.total > 0
              ? `${providerCounts.degraded + providerCounts.down}/${providerCounts.total} degraded`
              : analystFreshness > 0
                ? `${analystFreshness} analyst feeds degraded`
                : undefined
          }
        />
        <MetricChip
          label="Replay"
          value={replaySummary?.outcome_label ?? replaySummary?.action ?? "Live only"}
          tone={replaySummary?.veto_reason ? "caution" : "neutral"}
          detail={replaySummary?.as_of ? formatTimestamp(replaySummary.as_of) : undefined}
        />
      </div>
      <div className="mt-3 space-y-2">
        {noTradeReason && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {noTradeReason}
          </div>
        )}
        {degradeReason && (
          <div className="rounded-lg border border-amber-200 bg-amber-50/80 px-3 py-2 text-sm text-amber-900">
            {degradeReason}
          </div>
        )}
        {providerHealth?.summary && healthStatusTone(healthStatus) !== "positive" && (
          <div className="rounded-lg border border-border/60 bg-white/80 px-3 py-2 text-sm text-slate-700">
            {providerHealth.summary}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── FinanceDecisionPanel ──────────────────────────────────────────────────────

function FinanceDecisionPanel({ packet }: { packet: FinanceDecisionPacket }) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Decision Packet
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">
            {packet.action} {packet.instrument}
          </div>
        </div>
        <div
          className={cn(
            "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
            decisionTone(packet.action)
          )}
        >
          {packet.action}
        </div>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip
          label="Score"
          value={formatSignedNumber(packet.score)}
          tone={metricToneFromScore(packet.score)}
        />
        <MetricChip
          label="Confidence"
          value={formatPercent(packet.confidence, 0)}
          tone={metricToneFromScore(packet.confidence - 0.5)}
        />
        <MetricChip
          label="Position Size"
          value={formatPercent(packet.position_size_pct)}
          tone={packet.position_size_pct > 0 ? "neutral" : "caution"}
        />
        <MetricChip
          label="Capital At Risk"
          value={formatPercent(packet.capital_at_risk)}
          tone={packet.capital_at_risk > 0 ? "neutral" : "caution"}
        />
      </div>
      <div className="mt-3 rounded-lg border border-border/60 bg-white/80 p-3 text-sm leading-6 text-slate-700">
        {packet.thesis}
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        <FinanceKeyValue label="Entry Zone" value={packet.entry_zone} />
        <FinanceKeyValue label="Max Holding Period" value={packet.max_holding_period} />
        <FinanceKeyValue label="Stop Loss" value={packet.stop_loss} />
        <FinanceKeyValue label="Take Profit" value={packet.take_profit} />
      </div>
      {packet.kill_switch_reasons.length > 0 && (
        <div className="mt-3 space-y-2">
          {packet.kill_switch_reasons.map((reason) => (
            <div
              key={reason}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              {reason}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── FinanceSupervisorPanel ────────────────────────────────────────────────────

function FinanceSupervisorPanel({ trace }: { trace: NonNullable<AgentResponse["trace"]> }) {
  const supervisor = trace.supervisor_plan
  const feedback = trace.feedback_summary

  if (!supervisor && !feedback) {
    return null
  }

  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Supervisor Plan
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">
            {supervisor?.reasoning_mode ? readableToolName(supervisor.reasoning_mode) : "Adaptive selection"}
          </div>
        </div>
        {supervisor?.risk_posture && (
          <span className="rounded-full border border-border/60 bg-background px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {supervisor.risk_posture}
          </span>
        )}
      </div>
      {supervisor && (
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          <MetricChip
            label="Analysts"
            value={String(supervisor.active_analysts?.length ?? 0)}
            tone={(supervisor.active_analysts?.length ?? 0) > 0 ? "positive" : "neutral"}
            detail={supervisor.requires_debate ? "debate enabled" : "debate skipped"}
          />
          <MetricChip
            label="Reasoning"
            value={readableToolName(supervisor.reasoning_mode ?? "balanced")}
            tone="neutral"
          />
          <MetricChip
            label="Risk Posture"
            value={readableToolName(supervisor.risk_posture ?? "normal")}
            tone={supervisor.risk_posture === "defensive" ? "caution" : "neutral"}
          />
          <MetricChip
            label="Feedback"
            value={feedback?.observations ? `${feedback.observations} runs` : "Cold start"}
            tone={feedback?.observations ? "neutral" : "caution"}
            detail={
              typeof feedback?.veto_rate === "number"
                ? `${Math.round(feedback.veto_rate * 100)}% veto rate`
                : undefined
            }
          />
        </div>
      )}
      {supervisor?.rationale && (
        <div className="mt-3 rounded-lg border border-border/60 bg-white/80 p-3 text-sm leading-6 text-slate-700">
          {supervisor.rationale}
        </div>
      )}
      {supervisor?.active_analysts && supervisor.active_analysts.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {supervisor.active_analysts.map((analyst) => (
            <span
              key={analyst}
              className="rounded-full border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground"
            >
              {analyst}
            </span>
          ))}
        </div>
      )}
      {feedback && feedback.observations ? (
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <MetricChip
            label="Avg Move"
            value={typeof feedback.avg_realized_move === "number" ? formatPercent(feedback.avg_realized_move) : "n/a"}
            tone={typeof feedback.avg_realized_move === "number" ? metricToneFromScore(feedback.avg_realized_move) : "neutral"}
          />
          <MetricChip
            label="Last Action"
            value={feedback.last_action ?? "n/a"}
            tone={feedback.last_action === "BUY" ? "positive" : feedback.last_action === "NO_TRADE" ? "caution" : "neutral"}
          />
          <MetricChip
            label="Last Confidence"
            value={typeof feedback.last_confidence === "number" ? formatPercent(feedback.last_confidence, 0) : "n/a"}
            tone={typeof feedback.last_confidence === "number" ? metricToneFromScore(feedback.last_confidence - 0.5) : "neutral"}
          />
        </div>
      ) : null}
    </div>
  )
}

// ─── FinanceRiskPanel ──────────────────────────────────────────────────────────

function FinanceRiskPanel({ verdict }: { verdict: FinanceRiskVerdict }) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Risk Verdict
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">{verdict.allowed ? "Approved" : "Vetoed"}</div>
        </div>
        <span
          className={cn(
            "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
            verdict.allowed
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-amber-200 bg-amber-50 text-amber-900"
          )}
        >
          {verdict.regime || "unknown regime"}
        </span>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip
          label="VaR 95"
          value={formatPercent(verdict.value_at_risk_95)}
          tone={verdict.value_at_risk_95 <= 0.02 ? "positive" : verdict.value_at_risk_95 <= 0.05 ? "neutral" : "caution"}
        />
        <MetricChip
          label="Concentration"
          value={formatPercent(verdict.concentration_risk)}
          tone={verdict.concentration_risk <= 0.2 ? "positive" : verdict.concentration_risk <= 0.4 ? "neutral" : "caution"}
        />
        <MetricChip
          label="Sizing"
          value={formatPercent(verdict.position_size_pct)}
          tone={verdict.allowed ? "neutral" : "caution"}
        />
        <MetricChip
          label="Capital At Risk"
          value={formatPercent(verdict.capital_at_risk)}
          tone={verdict.allowed ? "neutral" : "caution"}
        />
      </div>
      <div className="mt-3 rounded-lg border border-border/60 bg-white/80 p-3 text-sm leading-6 text-slate-700">
        {verdict.rationale}
      </div>
      {verdict.kill_switch_reasons.length > 0 && (
        <StructuredList title="Kill Switch Reasons" items={verdict.kill_switch_reasons} tone="muted" />
      )}
    </div>
  )
}

// ─── FinanceFreshnessPanel ─────────────────────────────────────────────────────

function FinanceFreshnessPanel({
  summary,
}: {
  summary: NonNullable<AgentResponse["freshness_summary"]>
}) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        Feed Freshness
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-5">
        <MetricChip
          label="Council"
          value={summary.market_ready && summary.order_book_ready ? "Ready" : "Degraded"}
          tone={summary.market_ready && summary.order_book_ready ? "positive" : "caution"}
        />
        <MetricChip
          label="Market"
          value={summary.market_ready ? "Ready" : "Missing"}
          tone={summary.market_ready ? "positive" : "caution"}
        />
        <MetricChip
          label="Order Book"
          value={summary.order_book_ready ? "Ready" : "Missing"}
          tone={summary.order_book_ready ? "positive" : "caution"}
        />
        <MetricChip label="News" value={String(summary.news_count)} tone={summary.news_count > 0 ? "positive" : "neutral"} />
        <MetricChip
          label="Social"
          value={String(summary.social_count)}
          tone={summary.social_count > 0 ? "positive" : "neutral"}
        />
        <MetricChip
          label="Policy"
          value={String(summary.policy_count)}
          tone={summary.policy_count > 0 ? "positive" : "neutral"}
        />
      </div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {summary.notes.length > 0 && <StructuredList title="Freshness Notes" items={summary.notes} tone="muted" />}
        {summary.watch_items.length > 0 && <StructuredList title="Live Feeds" items={summary.watch_items} />}
      </div>
    </div>
  )
}

// ─── FinanceProviderHealthPanel ────────────────────────────────────────────────

function FinanceProviderHealthPanel({ health }: { health: FinanceProviderHealthSummary }) {
  const counts = summarizeProviderCounts(health)
  const maxLagSeconds = health.providers.reduce((current, provider) => {
    if (typeof provider.lag_seconds !== "number") {
      return current
    }
    return Math.max(current, provider.lag_seconds)
  }, 0)

  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Provider Health
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">{readableHealthStatus(health.overall_status)}</div>
        </div>
        <span
          className={cn(
            "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
            healthStatusClassName(health.overall_status)
          )}
        >
          {health.overall_status}
        </span>
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Providers" value={String(counts.total)} tone="neutral" />
        <MetricChip
          label="Degraded"
          value={String(counts.degraded + counts.down)}
          tone={counts.degraded + counts.down > 0 ? "caution" : "positive"}
        />
        <MetricChip
          label="Healthy"
          value={String(counts.healthy)}
          tone={counts.healthy > 0 ? "positive" : "neutral"}
        />
        <MetricChip
          label="Max Lag"
          value={maxLagSeconds > 0 ? formatDurationSeconds(maxLagSeconds) : "None"}
          tone={maxLagSeconds > 300 ? "caution" : "neutral"}
          detail={health.checked_at ? formatTimestamp(health.checked_at) : undefined}
        />
      </div>
      {health.summary && (
        <div className="mt-3 rounded-lg border border-border/60 bg-white/80 p-3 text-sm leading-6 text-slate-700">
          {health.summary}
        </div>
      )}
      {health.providers.length > 0 && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {health.providers.map((provider) => (
            <div key={provider.provider} className="rounded-lg border border-border/60 bg-white/80 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="text-sm font-medium text-slate-900">{provider.provider}</div>
                <span
                  className={cn(
                    "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                    healthStatusClassName(provider.status)
                  )}
                >
                  {provider.status}
                </span>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <MetricChip
                  label="Freshness"
                  value={provider.freshness ?? "unknown"}
                  tone={provider.freshness === "fresh" ? "positive" : provider.freshness ? "caution" : "neutral"}
                />
                <MetricChip
                  label="Lag"
                  value={typeof provider.lag_seconds === "number" ? formatDurationSeconds(provider.lag_seconds) : "n/a"}
                  tone={typeof provider.lag_seconds === "number" && provider.lag_seconds > 300 ? "caution" : "neutral"}
                  detail={
                    typeof provider.source_coverage === "number"
                      ? `${Math.round(provider.source_coverage * 100)}% coverage`
                      : undefined
                  }
                />
              </div>
              {provider.detail && <div className="mt-3 text-sm leading-6 text-slate-700">{provider.detail}</div>}
            </div>
          ))}
        </div>
      )}
      {health.notes && health.notes.length > 0 && <StructuredList title="Provider Notes" items={health.notes} tone="muted" />}
    </div>
  )
}

// ─── FinanceReplayPanel ────────────────────────────────────────────────────────

function FinanceReplayPanel({ summary }: { summary: FinanceReplaySummary }) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Replay Snapshot
          </div>
          <div className="mt-1 text-sm font-semibold text-slate-950">{summary.outcome_label ?? summary.action ?? "Historical check"}</div>
        </div>
        {summary.as_of && (
          <span className="rounded-full border border-border/60 bg-background px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {formatTimestamp(summary.as_of)}
          </span>
        )}
      </div>
      <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
        <MetricChip label="Replay Action" value={summary.action ?? "n/a"} tone="neutral" />
        <MetricChip
          label="Replay Confidence"
          value={typeof summary.confidence === "number" ? formatPercent(summary.confidence, 0) : "n/a"}
          tone={typeof summary.confidence === "number" ? metricToneFromScore(summary.confidence - 0.5) : "neutral"}
        />
        <MetricChip
          label="Realized Move"
          value={typeof summary.realized_move === "number" ? formatPercent(summary.realized_move) : "n/a"}
          tone={typeof summary.realized_move === "number" ? metricToneFromScore(summary.realized_move) : "neutral"}
        />
        <MetricChip
          label="Veto"
          value={summary.veto_reason ? "Triggered" : "Clear"}
          tone={summary.veto_reason ? "caution" : "positive"}
        />
      </div>
      {summary.veto_reason && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {summary.veto_reason}
        </div>
      )}
      {summary.notes && summary.notes.length > 0 && <StructuredList title="Replay Notes" items={summary.notes} tone="muted" />}
    </div>
  )
}

// ─── FinanceSignalsPanel ───────────────────────────────────────────────────────

function FinanceSignalsPanel({ signals }: { signals: FinanceAnalystSignal[] }) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        Analyst Signals
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {signals.map((signal) => (
          <div key={signal.analyst} className="rounded-lg border border-border/60 bg-white/80 p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-slate-900">{signal.analyst}</div>
                <div className="mt-1 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {signal.instrument}
                </div>
              </div>
              <div
                className={cn(
                  "rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em]",
                  directionTone(signal.direction)
                )}
              >
                {signal.direction}
              </div>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              <MetricChip
                label="Signal"
                value={formatSignedNumber(signal.signal_score)}
                tone={metricToneFromScore(signal.signal_score)}
              />
              <MetricChip
                label="Confidence"
                value={formatPercent(signal.confidence, 0)}
                tone={metricToneFromScore(signal.confidence - 0.5)}
                detail={signal.freshness_ok ? "Fresh" : "Degraded"}
              />
            </div>
            <div className="mt-3 text-sm leading-6 text-slate-700">{signal.thesis}</div>
            {signal.citations.length > 0 && (
              <div className="mt-3 space-y-1">
                {signal.citations.slice(0, 3).map((citation) => (
                  <div key={citation} className="text-xs leading-5 text-muted-foreground">
                    {citation}
                  </div>
                ))}
              </div>
            )}
            {signal.evidence_ids.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {signal.evidence_ids.slice(0, 3).map((evidenceId) => (
                  <span
                    key={evidenceId}
                    className="rounded-full border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground"
                  >
                    {evidenceId}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
