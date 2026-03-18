"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Bell,
  CandlestickChart,
  CheckCircle2,
  Clock,
  DollarSign,
  Loader2,
  PieChart,
  Plus,
  Radar,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react"

import {
  api,
  DecisionQueueSnapshot,
  EventPulse,
  HistoricalRegimeSnapshot,
  MarketRegimeSnapshot,
  PendingSnapshot,
  PortfolioRiskSnapshot,
  SignalItem,
  SnapshotEnvelope,
  WorldState,
  formatRegimeFactorSummary,
} from "@/lib/api"
import { ActionCluster, SegmentedControl } from "@/components/dashboard/shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

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

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [missingPortfolio, setMissingPortfolio] = useState(false)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<CommandCenterState>(emptyState)
  const [attentionView, setAttentionView] = useState<"all" | "risks" | "opportunities" | "approvals">("all")
  const [decisionBoardView, setDecisionBoardView] = useState<"queue" | "history" | "context">("queue")
  const [signals, setSignals] = useState<SignalItem[]>([])
  const [workspaceId] = useState<string>("default")

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

    async function loadSignals() {
      try {
        const attentionSignals = await api.signals.getAttention(workspaceId, "pm", 10)
        if (active) {
          setSignals(attentionSignals || [])
        }
      } catch (error) {
        console.error("Failed to load signals", error)
      }
    }

    loadCommandCenter()
    loadSignals()
    return () => {
      active = false
    }
  }, [workspaceId])

  const world = state.world?.data
  const regime = state.regime?.data
  const decisionQueue = state.decisionQueue?.data
  const portfolioRisk = state.portfolioRisk?.data
  const eventPulse = state.eventPulse?.data
  const regimeHistory = state.regimeHistory?.data

  return (
    <div className="space-y-6">
      {/* Hero Metrics - 4 columns */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard
          title="Portfolio P&L"
          value={portfolioRisk ? "+12.4%" : loading ? "..." : "--"}
          trend={portfolioRisk ? "up" : undefined}
          href="/dashboard/portfolio"
        />
        <MetricCard
          title="Risk Regime"
          value={regime ? regime.regime_label : loading ? "..." : "Unknown"}
          trend={regime?.regime_label?.toLowerCase().includes("risk-off") ? "down" : regime?.regime_label?.toLowerCase().includes("risk-on") ? "up" : undefined}
          href="/dashboard/portfolio"
        />
        <MetricCard
          title="Approvals"
          value={decisionQueue?.recommended_actions?.length?.toString() ?? "0"}
          trend={decisionQueue?.recommended_actions?.length ? "attention" : undefined}
          href="/dashboard/agent?tab=approvals"
        />
        <MetricCard
          title="Events"
          value={eventPulse ? eventPulse.event_count.toString() : loading ? "..." : "0"}
          trend={eventPulse?.event_count ? "attention" : undefined}
          href="/dashboard/events"
        />
      </div>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Decision Board */}
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 pb-3">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <PieChart className="h-4 w-4 text-black/40" />
                Decision Board
              </CardTitle>
              <SegmentedControl
                value={decisionBoardView}
                onChange={(v) => setDecisionBoardView(v as "queue" | "history" | "context")}
                items={[
                  { label: "Queue", value: "queue" },
                  { label: "History", value: "history" },
                  { label: "Context", value: "context" },
                ]}
              />
            </CardHeader>
            <CardContent>
              {decisionBoardView === "queue" && (
                <div className="grid gap-4 sm:grid-cols-3">
                  <SignalPanel
                    title="Top Risks"
                    icon={TrendingDown}
                    items={decisionQueue?.top_risks.map((item) => `${item.title} · ${item.why}`) ?? []}
                    fallback="No risks"
                  />
                  <SignalPanel
                    title="Opportunities"
                    icon={TrendingUp}
                    items={decisionQueue?.top_opportunities.map((item) => `${item.title} · ${item.why}`) ?? []}
                    fallback="No opportunities"
                  />
                  <SignalPanel
                    title="Recommended"
                    icon={Activity}
                    items={decisionQueue?.recommended_actions ?? []}
                    fallback="No recommendations"
                  />
                </div>
              )}

              {decisionBoardView === "history" && (
                <div className="space-y-2">
                  {regimeHistory?.analogs?.length ? (
                    regimeHistory.analogs.slice(0, 5).map((analog) => (
                      <Link
                        key={`${analog.regime_label}-${analog.as_of}`}
                        href="/dashboard/lab"
                        className="block rounded-lg border p-3 transition-colors hover:bg-black/[0.02]"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm font-medium">{analog.regime_label}</span>
                          <span className="text-xs text-black/30">{(analog.similarity * 100).toFixed(0)}% similar</span>
                        </div>
                        <div className="mt-1 text-xs text-black/40">
                          {new Date(analog.as_of).toLocaleDateString()} · {formatRegimeFactorSummary(analog.factor_summary)}
                        </div>
                      </Link>
                    ))
                  ) : (
                    <div className="py-6 text-center text-sm text-black/30">
                      {loading ? "Loading analogs..." : "No stored regime analogs."}
                    </div>
                  )}
                </div>
              )}

              {decisionBoardView === "context" && (
                <div className="space-y-3">
                  <div className="rounded-lg border bg-black/[0.02] p-4">
                    <div className="mb-1.5 text-xs font-medium text-black/50">Current Context</div>
                    <p className="text-sm">
                      {world && regime
                        ? `${regime.regime_label} regime with ${(world.inflation * 100).toFixed(2)}% inflation and ${(world.interest_rate * 100).toFixed(2)}% rates.`
                        : "Macro context is still building."}
                    </p>
                  </div>
                  <div className="rounded-lg border bg-black/[0.02] p-4">
                    <div className="mb-1.5 text-xs font-medium text-black/50">Event Pulse</div>
                    <p className="text-sm">
                      {eventPulse
                        ? `${eventPulse.dominant_theme} across ${eventPulse.event_count} events.`
                        : "Event pulse is still building."}
                    </p>
                  </div>
                  <ActionCluster
                    items={[
                      { href: "/dashboard/portfolio", label: "Open Portfolio", tone: "default" },
                      { href: "/dashboard/agent?new=true", label: "New Run", tone: "default" },
                    ]}
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Attention Board */}
          <Card>
            <CardHeader className="flex-row items-center justify-between gap-3 pb-3">
              <CardTitle className="text-sm font-medium">Attention</CardTitle>
              <SegmentedControl
                value={attentionView}
                onChange={(v) => setAttentionView(v as typeof attentionView)}
                items={[
                  { label: "All", value: "all" },
                  { label: "Risks", value: "risks" },
                  { label: "Ops", value: "opportunities" },
                  { label: "Approvals", value: "approvals" },
                ]}
              />
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {attentionView === "all" && (
                  <>
                    <AttentionCard
                      title="High-Risk"
                      type="risk"
                      items={signals.filter(s => s.type === "risk").slice(0, 2).map((signal) => ({
                        label: signal.title,
                        detail: signal.detail,
                      }))}
                      fallback="No high-risk signals"
                      href="/dashboard/portfolio"
                    />
                    <AttentionCard
                      title="Approvals"
                      type="approval"
                      items={decisionQueue?.recommended_actions?.slice(0, 2).map((action) => ({
                        label: action.split("·")[0] || action,
                        detail: action.includes("·") ? action.split("·")[1] : "Requires approval",
                      })) ?? []}
                      fallback="No pending approvals"
                      href="/dashboard/agent?tab=approvals"
                    />
                    <AttentionCard
                      title="Events"
                      type="attention"
                      items={signals.filter(s => s.type === "event").slice(0, 2).map((signal) => ({
                        label: signal.title,
                        detail: signal.detail,
                      }))}
                      fallback="No upcoming events"
                      href="/dashboard/events"
                    />
                  </>
                )}
                {attentionView === "risks" && (
                  <AttentionCard
                    title="Risk Items"
                    type="risk"
                    items={signals.filter(s => s.type === "risk").slice(0, 6).map((signal) => ({
                      label: signal.title,
                      detail: signal.detail,
                    }))}
                    fallback="No risk items"
                    href="/dashboard/portfolio"
                  />
                )}
                {attentionView === "opportunities" && (
                  <AttentionCard
                    title="Opportunities"
                    type="opportunity"
                    items={signals.filter(s => s.type === "opportunity").slice(0, 6).map((signal) => ({
                      label: signal.title,
                      detail: signal.detail,
                    }))}
                    fallback="No opportunities"
                    href="/dashboard/research"
                  />
                )}
                {attentionView === "approvals" && (
                  <AttentionCard
                    title="Pending"
                    type="approval"
                    items={decisionQueue?.recommended_actions?.slice(0, 3).map((action) => ({
                      label: action.split("·")[0] || action,
                      detail: action.includes("·") ? action.split("·")[1] : "Requires approval",
                    })) ?? []}
                    fallback="No pending approvals"
                    href="/dashboard/agent?tab=approvals"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Quick Actions */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-medium text-black/50">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href="/dashboard/agent?new=true" className="block">
                <Button className="w-full justify-start gap-2" size="sm">
                  <Plus className="h-3.5 w-3.5" />
                  New Agent Run
                </Button>
              </Link>
              <Link href="/dashboard/portfolio?action=rebalance" className="block">
                <Button className="w-full justify-start gap-2" size="sm" variant="outline">
                  <PieChart className="h-3.5 w-3.5" />
                  Rebalance
                </Button>
              </Link>
              <Link href="/dashboard/research?new=brief" className="block">
                <Button className="w-full justify-start gap-2" size="sm" variant="outline">
                  <CandlestickChart className="h-3.5 w-3.5" />
                  Research Brief
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Watchlist */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-medium text-black/50">Watchlist</CardTitle>
            </CardHeader>
            <CardContent>
              {(decisionQueue?.watchlist_changes ?? []).length > 0 ? (
                <div className="space-y-1.5">
                  {decisionQueue?.watchlist_changes.slice(0, 5).map((item, i) => (
                    <div key={i} className="flex items-start gap-2 rounded border p-2 text-sm">
                      <CandlestickChart className="h-3.5 w-3.5 mt-0.5 text-black/30" />
                      <span className="text-xs">{item}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-black/30">
                  {loading ? "Loading..." : "No changes"}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Upcoming */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-medium text-black/50">Upcoming</CardTitle>
            </CardHeader>
            <CardContent>
              {eventPulse?.upcoming_events?.length ? (
                <div className="space-y-1.5">
                  {eventPulse.upcoming_events.slice(0, 5).map((event: { title?: string; date?: string; type?: string }, i: number) => (
                    <Link
                      key={i}
                      href="/dashboard/events"
                      className="flex items-start gap-2 rounded border p-2 transition-colors hover:bg-black/[0.02]"
                    >
                      <Clock className="h-3.5 w-3.5 mt-0.5 text-black/30" />
                      <div>
                        <div className="text-xs font-medium">{event.title}</div>
                        <div className="text-[10px] text-black/30">{event.date} · {event.type}</div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-black/30">
                  {loading ? "Loading..." : "No events"}
                </div>
              )}
            </CardContent>
          </Card>

          {/* System */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-xs font-medium text-black/50">System</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5 text-xs text-black/50">
              <div className="flex items-center justify-between">
                <span>Data Fabric</span>
                <span className="flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  Operational
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Orchestrator</span>
                <span>2 active runs</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Missing Portfolio */}
      {missingPortfolio && (
        <Card className="border-dashed border-black/10">
          <CardContent className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-4 w-4 text-black/30" />
              <div className="text-sm">
                <span className="font-medium">No Portfolio</span>
                <span className="ml-2 text-black/40">Queue and risk monitoring activate once portfolio is set up.</span>
              </div>
            </div>
            <Link href="/dashboard/portfolio?setup=true">
              <Button size="sm" variant="outline">Setup</Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function MetricCard({ title, value, trend, href }: { title: string; value: string; trend?: "up" | "down" | "attention"; href?: string }) {
  const content = (
    <div className={cn(
      "rounded-lg border bg-white p-3 transition-colors hover:bg-black/[0.02]",
      href && "cursor-pointer",
    )}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-black/40">{title}</span>
        {trend === "up" && <ArrowUpRight className="h-3 w-3 text-emerald-500" />}
        {trend === "down" && <ArrowDownRight className="h-3 w-3 text-red-500" />}
        {trend === "attention" && <Bell className="h-3 w-3 text-amber-500" />}
      </div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  )

  if (!href) return content
  return <Link href={href}>{content}</Link>
}

function SignalPanel({ title, icon: Icon, items, fallback }: { title: string; icon: typeof TrendingUp; items: string[]; fallback: string }) {
  return (
    <div className="rounded-lg border bg-black/[0.02] p-3">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-black/50">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      {items.length > 0 ? (
        <div className="space-y-1 text-xs text-black/70">
          {items.map((item, i) => (
            <div key={i}>{item}</div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-black/30">{fallback}</div>
      )}
    </div>
  )
}

function AttentionCard({ title, type, items, fallback, href }: { title: string; type: "risk" | "opportunity" | "approval" | "attention"; items: Array<{ label: string; detail: string }>; fallback: string; href?: string }) {
  const borderColors = { risk: "border-l-red-400", opportunity: "border-l-emerald-400", approval: "border-l-amber-400", attention: "border-l-blue-400" }
  const icons = { risk: XCircle, opportunity: CheckCircle2, approval: Bell, attention: Activity }
  const Icon = icons[type]

  const content = (
    <div className={cn("border-l-2 bg-white pl-3 pr-4 py-3 rounded-r-lg border")}>
      <div className="flex items-center gap-1.5 text-xs font-medium text-black/50">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      {items.length > 0 ? (
        <div className="mt-2 space-y-1">
          {items.map((item, i) => (
            <div key={i}>
              <div className="text-xs font-medium">{item.label}</div>
              <div className="text-[10px] text-black/30">{item.detail}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-xs text-black/30">{fallback}</div>
      )}
    </div>
  )

  if (!href) return content
  return <Link href={href} className="block">{content}</Link>
}
