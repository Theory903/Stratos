"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import {
  Activity,
  CandlestickChart,
  Globe2,
  Loader2,
  Radar,
  ShieldAlert,
} from "lucide-react"

import {
  api,
  DecisionQueueSnapshot,
  EventPulse,
  HistoricalRegimeSnapshot,
  MarketRegimeSnapshot,
  PendingSnapshot,
  PortfolioRiskSnapshot,
  SnapshotEnvelope,
  WorldState,
  formatRegimeFactorSummary,
} from "@/lib/api"
import { ActionCluster, SegmentedControl } from "@/components/dashboard/shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type CommandCenterState = {
  decisionQueue: SnapshotEnvelope<DecisionQueueSnapshot> | null
  eventPulse: SnapshotEnvelope<EventPulse> | null
  portfolioRisk: SnapshotEnvelope<PortfolioRiskSnapshot> | null
  regimeHistory: SnapshotEnvelope<HistoricalRegimeSnapshot> | null
  regime: SnapshotEnvelope<MarketRegimeSnapshot> | null
  world: SnapshotEnvelope<WorldState> | null
}

const emptyState: CommandCenterState = {
  decisionQueue: null,
  eventPulse: null,
  portfolioRisk: null,
  regimeHistory: null,
  regime: null,
  world: null,
}

type CommandBoardView = "queue" | "history" | "context"

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [missingPortfolio, setMissingPortfolio] = useState(false)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<CommandCenterState>(emptyState)
  const [boardView, setBoardView] = useState<CommandBoardView>("queue")

  useEffect(() => {
    let active = true

    async function loadCommandCenter() {
      try {
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const portfolioResponse = await api.dataFabricV2.get<unknown>("/portfolio", {
          params: { name: "primary", include_meta: true },
          validateStatus: (status) => status === 200 || status === 202,
        })

        const hasPortfolio = portfolioResponse.status === 200
        const [world, regime, eventPulse, regimeHistory, decisionQueue, portfolioRisk] =
          await Promise.all([
            request<WorldState>("/world-state", "world"),
            request<MarketRegimeSnapshot>("/market/regime", "regime"),
            request<EventPulse>("/events/pulse/global", "eventPulse"),
            request<HistoricalRegimeSnapshot>("/history/similar-regimes", "regimeHistory"),
            hasPortfolio
              ? request<DecisionQueueSnapshot>("/decision/queue?name=primary", "decisionQueue")
              : Promise.resolve(null),
            hasPortfolio
              ? request<PortfolioRiskSnapshot>("/portfolio/risk?name=primary", "portfolioRisk")
              : Promise.resolve(null),
          ])

        if (!active) return
        startTransition(() => {
          setMissingPortfolio(!hasPortfolio)
          setState({
            world,
            regime,
            eventPulse,
            regimeHistory,
            decisionQueue,
            portfolioRisk,
          })
          setPending({})
        })
      } catch (error) {
        console.error("Failed to load command center snapshots", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadCommandCenter()
    return () => {
      active = false
    }
  }, [])

  const pendingItems = Object.values(pending)
  const world = state.world?.data
  const regime = state.regime?.data
  const decisionQueue = state.decisionQueue?.data
  const portfolioRisk = state.portfolioRisk?.data
  const eventPulse = state.eventPulse?.data
  const regimeHistory = state.regimeHistory?.data

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {missingPortfolio && (
        <Card className="border-dashed">
          <CardContent className="pt-6 text-sm text-muted-foreground">
            No portfolio yet. Queue and risk stay inactive until a book is configured.
          </CardContent>
        </Card>
      )}

      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing {pendingItems.map((item) => item.entity_type).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Macro Pressure"
          icon={Globe2}
          value={
            world
              ? `${(world.inflation * 100).toFixed(2)}% CPI · ${(world.interest_rate * 100).toFixed(2)}% rates`
              : loading
                ? "Building"
                : "Unavailable"
          }
          detail={
            world
              ? `Liquidity ${world.liquidity_index.toFixed(2)} · VIX proxy ${world.volatility_index.toFixed(2)}`
              : "Awaiting world-state snapshot"
          }
          freshness={state.world?.meta.freshness}
        />
        <MetricCard
          title="Risk Regime"
          icon={Activity}
          value={regime ? regime.regime_label : loading ? "Building" : "Unavailable"}
          detail={
            regime
              ? `${(regime.confidence * 100).toFixed(0)}% confidence · ${formatRegimeFactorSummary(
                  regime.factor_summary
                )}`
              : "Awaiting market regime snapshot"
          }
          freshness={state.regime?.meta.freshness}
        />
        <MetricCard
          title="Event Pulse"
          icon={Radar}
          value={eventPulse ? eventPulse.headline : loading ? "Building" : "Unavailable"}
          detail={
            eventPulse
              ? `${eventPulse.event_count} events · dominant theme ${eventPulse.dominant_theme}`
              : "Awaiting event pulse"
          }
          freshness={state.eventPulse?.meta.freshness}
          href="/dashboard/events"
        />
        <MetricCard
          title="Portfolio Risk"
          icon={ShieldAlert}
          value={
            portfolioRisk
              ? `VaR ${(portfolioRisk.value_at_risk_95 * 100).toFixed(2)}%`
              : loading
                ? "Building"
                : "Unavailable"
          }
          detail={
            portfolioRisk
              ? `Daily vol ${(portfolioRisk.estimated_daily_volatility * 100).toFixed(2)}% · concentration ${(portfolioRisk.concentration_risk * 100).toFixed(0)}%`
              : "Awaiting risk posture"
          }
          freshness={state.portfolioRisk?.meta.freshness}
          href="/dashboard/portfolio"
        />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="min-h-[360px]">
          <CardHeader className="gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle>Decision Board</CardTitle>
            <SegmentedControl
              value={boardView}
              onChange={setBoardView}
              items={[
                { label: "Queue", value: "queue" },
                { label: "History", value: "history" },
                { label: "Context", value: "context" },
              ]}
            />
          </CardHeader>
          <CardContent className="content-auto">
            {boardView === "queue" && (
              <div className="grid gap-3 md:grid-cols-3">
                <SignalPanel
                  title="Top risks"
                  items={decisionQueue?.top_risks.map((item) => `${item.title} · ${item.why}`) ?? []}
                  fallback="No internal risk queue yet."
                />
                <SignalPanel
                  title="Top opportunities"
                  items={
                    decisionQueue?.top_opportunities.map((item) => `${item.title} · ${item.why}`) ?? []
                  }
                  fallback="No opportunity ranking yet."
                />
                <SignalPanel
                  title="Recommended actions"
                  items={decisionQueue?.recommended_actions ?? []}
                  fallback="No recommended actions yet."
                />
              </div>
            )}

            {boardView === "history" && (
              <div className="quiet-scroll max-h-[320px] space-y-3 overflow-y-auto pr-1">
                {regimeHistory?.analogs?.length ? (
                  regimeHistory.analogs.slice(0, 4).map((analog) => (
                    <div
                      key={`${analog.regime_label}-${analog.as_of}`}
                      className="rounded-lg border bg-muted/25 p-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{analog.regime_label}</div>
                        <span className="text-xs text-muted-foreground">
                          {(analog.similarity * 100).toFixed(0)}% similar
                        </span>
                      </div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        {new Date(analog.as_of).toLocaleDateString()} ·{" "}
                        {formatRegimeFactorSummary(analog.factor_summary)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">
                    {loading ? "Building historical analogs..." : "No stored regime analogs yet."}
                  </div>
                )}
              </div>
            )}

            {boardView === "context" && (
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="rounded-lg border bg-muted/20 p-3">
                  {world && regime
                    ? `${regime.regime_label} with ${(world.inflation * 100).toFixed(2)}% inflation and ${(world.interest_rate * 100).toFixed(2)}% policy rates.`
                    : "Macro and regime context is still building."}
                </div>
                <div className="rounded-lg border bg-muted/20 p-3">
                  {eventPulse
                    ? `${eventPulse.dominant_theme} is the dominant pulse across ${eventPulse.event_count} internal events.`
                    : "Event pulse is still building."}
                </div>
                <ActionCluster
                  items={[
                    { href: "/dashboard/portfolio", label: "Open portfolio", tone: "outline" },
                    { href: "/dashboard/agent", label: "Open agent", tone: "outline" },
                  ]}
                />
              </div>
            )}
          </CardContent>
        </Card>

        <div className="min-w-0 space-y-4 xl:sticky xl:top-24 xl:self-start">
          <Card>
            <CardHeader>
              <CardTitle>Watchlist</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {(decisionQueue?.watchlist_changes ?? []).length > 0 ? (
                decisionQueue?.watchlist_changes.slice(0, 4).map((item) => (
                  <div
                    key={item}
                    className="flex items-start gap-3 rounded-lg border bg-muted/20 p-3 text-sm"
                  >
                    <CandlestickChart className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <span>{item}</span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? "Building watchlist changes..." : "No watchlist changes queued yet."}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next</CardTitle>
            </CardHeader>
            <CardContent>
              <ActionCluster
                items={[
                  { href: "/dashboard/portfolio", label: "Stress the book" },
                  { href: "/dashboard/agent", label: "Write memo", tone: "outline" },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function MetricCard({
  title,
  icon: Icon,
  value,
  detail,
  freshness,
  href,
}: {
  title: string
  icon: typeof Globe2
  value: string
  detail: string
  freshness?: string
  href?: string
}) {
  const content = (
    <Card className="h-full overflow-hidden">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="break-words text-xl font-semibold tracking-[-0.03em]">{value}</div>
        <div className="break-words text-xs leading-5 text-muted-foreground">{detail}</div>
        {freshness && (
          <span className="inline-flex rounded-full border border-border/80 bg-white/75 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            {freshness}
          </span>
        )}
      </CardContent>
    </Card>
  )

  if (!href) {
    return content
  }

  return (
    <Link className="block transition-transform duration-200 motion-reduce:transition-none hover:-translate-y-0.5" href={href}>
      {content}
    </Link>
  )
}

function SignalPanel({
  title,
  items,
  fallback,
}: {
  title: string
  items: string[]
  fallback: string
}) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </div>
      {items.length > 0 ? (
        <div className="space-y-2 text-sm">
          {items.map((item) => (
            <div key={item}>{item}</div>
          ))}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">{fallback}</div>
      )}
    </div>
  )
}
