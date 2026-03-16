"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { Loader2, Radar, ShieldAlert, Sparkles, Wallet } from "lucide-react"

import {
  api,
  DecisionQueueSnapshot,
  PendingSnapshot,
  PortfolioExposureSnapshot,
  PortfolioRebalanceResult,
  PortfolioRiskSnapshot,
  PortfolioScenarioResult,
  PortfolioSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { ActionCluster, SegmentedControl } from "@/components/dashboard/shell"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const SAMPLE_PORTFOLIO: PortfolioSnapshot = {
  name: "primary",
  benchmark: "SPY",
  constraints: {
    max_single_name_weight: 0.6,
    max_crypto_weight: 0.35,
  },
  positions: [
    { ticker: "AAPL", quantity: 120, average_cost: 188, asset_class: "equity" },
    { ticker: "X:BTCUSD", quantity: 0.8, average_cost: 68000, asset_class: "crypto" },
  ],
}

type PortfolioWorkspaceState = {
  decisionQueue: SnapshotEnvelope<DecisionQueueSnapshot> | null
  exposures: SnapshotEnvelope<PortfolioExposureSnapshot> | null
  portfolio: SnapshotEnvelope<PortfolioSnapshot> | null
  risk: SnapshotEnvelope<PortfolioRiskSnapshot> | null
}

type PortfolioView = "book" | "risk" | "scenario" | "rebalance"

export default function PortfolioPage() {
  const [loading, setLoading] = useState(true)
  const [missingPortfolio, setMissingPortfolio] = useState(false)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [workspace, setWorkspace] = useState<PortfolioWorkspaceState>({
    decisionQueue: null,
    exposures: null,
    portfolio: null,
    risk: null,
  })
  const [scenario, setScenario] = useState<PortfolioScenarioResult | null>(null)
  const [rebalance, setRebalance] = useState<PortfolioRebalanceResult | null>(null)
  const [actionLoading, setActionLoading] = useState<"sample" | "scenario" | "rebalance" | null>(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [activeView, setActiveView] = useState<PortfolioView>("book")

  useEffect(() => {
    let active = true

    async function loadWorkspace() {
      try {
        const portfolioResponse = await api.dataFabricV2.get<SnapshotEnvelope<PortfolioSnapshot> | PendingSnapshot>(
          "/portfolio",
          {
            params: { name: "primary", include_meta: true },
            validateStatus: (status) => status === 200 || status === 202,
          }
        )

        if (!active) return
        if (portfolioResponse.status === 202) {
          startTransition(() => {
            setMissingPortfolio(true)
            setWorkspace({
              decisionQueue: null,
              exposures: null,
              portfolio: null,
              risk: null,
            })
            setPending({})
          })
          return
        }

        const portfolio = portfolioResponse.data as SnapshotEnvelope<PortfolioSnapshot>
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const [exposures, risk, decisionQueue] = await Promise.all([
          request<PortfolioExposureSnapshot>("/portfolio/exposures?name=primary", "exposures"),
          request<PortfolioRiskSnapshot>("/portfolio/risk?name=primary", "risk"),
          request<DecisionQueueSnapshot>("/decision/queue?name=primary", "decisionQueue"),
        ])

        if (!active) return
        startTransition(() => {
          setMissingPortfolio(false)
          setWorkspace({ portfolio, exposures, risk, decisionQueue })
          setPending({})
        })
      } catch (error) {
        console.error("Failed to load portfolio workspace", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadWorkspace()
    return () => {
      active = false
    }
  }, [reloadKey])

  const pendingItems = Object.values(pending)
  const portfolio = workspace.portfolio?.data
  const exposures = workspace.exposures?.data
  const risk = workspace.risk?.data
  const decisionQueue = workspace.decisionQueue?.data

  async function loadSamplePortfolio() {
    setActionLoading("sample")
    try {
      await api.dataFabricV2.post("/portfolio/positions", SAMPLE_PORTFOLIO)
      startTransition(() => {
        setReloadKey((current) => current + 1)
      })
    } catch (error) {
      console.error("Failed to load sample portfolio", error)
    } finally {
      setActionLoading(null)
    }
  }

  async function runScenario() {
    setActionLoading("scenario")
    try {
      const response = await api.dataFabricV2.post<{ status: string; scenario: PortfolioScenarioResult }>(
        "/portfolio/scenario",
        {
          name: "primary",
          scenario: "oil_sticky_india_btc",
        }
      )
      setScenario(response.data.scenario)
    } catch (error) {
      console.error("Failed to run scenario", error)
    } finally {
      setActionLoading(null)
    }
  }

  async function runRebalance() {
    setActionLoading("rebalance")
    try {
      const response = await api.dataFabricV2.post<{ status: string; rebalance: PortfolioRebalanceResult }>(
        "/portfolio/rebalance?name=primary"
      )
      setRebalance(response.data.rebalance)
    } catch (error) {
      console.error("Failed to compute rebalance", error)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {missingPortfolio && (
        <Card className="border-dashed">
          <CardContent className="flex flex-col gap-3 pt-6 text-sm text-muted-foreground">
            <div>No portfolio yet. STRATOS will not create one for you.</div>
            <div className="flex flex-wrap gap-3">
              <Button disabled={actionLoading !== null} onClick={loadSamplePortfolio}>
                {actionLoading === "sample" ? "Loading..." : "Load sample PM book"}
              </Button>
            </div>
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

      <div className="grid gap-4 lg:grid-cols-4">
        <StatCard
          icon={Wallet}
          title="Positions"
          value={portfolio ? String(portfolio.positions.length) : loading ? "Building" : "Unavailable"}
          detail={portfolio ? `Benchmark ${portfolio.benchmark}` : "Awaiting portfolio snapshot"}
          freshness={workspace.portfolio?.meta.freshness}
        />
        <StatCard
          icon={Radar}
          title="Total Market Value"
          value={
            exposures
              ? exposures.total_market_value.toLocaleString(undefined, {
                  maximumFractionDigits: 0,
                })
              : loading
                ? "Building"
                : "Unavailable"
          }
          detail={exposures ? "Internal mark-to-snapshot value" : "Awaiting exposure view"}
          freshness={workspace.exposures?.meta.freshness}
        />
        <StatCard
          icon={ShieldAlert}
          title="Portfolio VaR"
          value={
            risk
              ? `${(risk.value_at_risk_95 * 100).toFixed(2)}%`
              : loading
                ? "Building"
                : "Unavailable"
          }
          detail={risk ? `Daily vol ${(risk.estimated_daily_volatility * 100).toFixed(2)}%` : "Awaiting risk view"}
          freshness={workspace.risk?.meta.freshness}
        />
        <StatCard
          icon={Sparkles}
          title="Action Queue"
          value={
            decisionQueue
              ? `${decisionQueue.recommended_actions.length} actions`
              : loading
                ? "Building"
                : "Unavailable"
          }
          detail={
            decisionQueue
              ? `${decisionQueue.top_risks.length} risks · ${decisionQueue.top_opportunities.length} opportunities`
              : "Awaiting decision queue"
          }
          freshness={workspace.decisionQueue?.meta.freshness}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card className="min-h-[420px]">
          <CardHeader className="gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle>Workspace</CardTitle>
            <SegmentedControl
              value={activeView}
              onChange={setActiveView}
              items={[
                { label: "Book", value: "book" },
                { label: "Risk", value: "risk" },
                { label: "Scenario", value: "scenario" },
                { label: "Rebalance", value: "rebalance" },
              ]}
            />
          </CardHeader>
          <CardContent className="content-auto">
            {activeView === "book" && (
              <>
                {exposures?.top_positions?.length ? (
                  <div className="quiet-scroll max-h-[340px] space-y-3 overflow-y-auto pr-1">
                    {exposures.top_positions.map((position) => (
                      <div
                        key={position.ticker}
                        className="flex items-center justify-between rounded-lg border bg-muted/20 p-3"
                      >
                        <div>
                          <div className="font-medium">{position.ticker}</div>
                          <div className="text-xs text-muted-foreground">
                            {position.asset_class} · qty {position.quantity} · last {position.last_price.toFixed(2)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">
                            {position.market_value.toLocaleString(undefined, {
                              maximumFractionDigits: 0,
                            })}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {(position.weight * 100).toFixed(1)}% weight
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">
                    {loading ? "Building holdings view..." : "No positions yet."}
                  </div>
                )}
              </>
            )}

            {activeView === "risk" && (
              <div className="space-y-3">
                {risk?.risk_flags?.length ? (
                  risk.risk_flags.map((flag) => (
                    <div key={flag} className="rounded-lg border bg-muted/20 p-3 text-sm">
                      {flag}
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-muted-foreground">
                    {loading ? "Building risk flags..." : "No risk flags yet."}
                  </div>
                )}
                {risk?.regime && (
                  <div className="rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
                    Regime {risk.regime.regime_label} · {(risk.regime.confidence * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            )}

            {activeView === "scenario" && (
              <div className="space-y-3">
                <div className="flex justify-end">
                  <Button disabled={actionLoading !== null || !portfolio} onClick={runScenario} size="sm">
                    {actionLoading === "scenario" ? "Running..." : "Run scenario"}
                  </Button>
                </div>
                {scenario ? (
                  <div className="space-y-3">
                    <div className="text-sm text-muted-foreground">
                      Impact{" "}
                      <span className="font-medium text-foreground">
                        {scenario.estimated_total_pnl_impact.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}
                      </span>
                    </div>
                    <div className="quiet-scroll max-h-[280px] space-y-3 overflow-y-auto pr-1">
                      {scenario.positions.map((position) => (
                        <div key={position.ticker} className="rounded-lg border bg-muted/20 p-3 text-sm">
                          {position.ticker} · shock {(position.shock * 100).toFixed(1)}% · impact{" "}
                          {position.estimated_pnl_impact.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Run the flagship shock.</div>
                )}
              </div>
            )}

            {activeView === "rebalance" && (
              <div className="space-y-3">
                <div className="flex justify-end">
                  <Button
                    disabled={actionLoading !== null || !portfolio}
                    onClick={runRebalance}
                    variant="outline"
                    size="sm"
                  >
                    {actionLoading === "rebalance" ? "Working..." : "Suggest rebalance"}
                  </Button>
                </div>
                {rebalance ? (
                  <div className="space-y-3">
                    <div className="text-sm text-muted-foreground">{rebalance.rationale}</div>
                    <div className="quiet-scroll max-h-[280px] space-y-3 overflow-y-auto pr-1">
                      {rebalance.suggestions.map((suggestion) => (
                        <div
                          key={suggestion.ticker}
                          className="flex items-center justify-between rounded-lg border bg-muted/20 p-3 text-sm"
                        >
                          <span>{suggestion.ticker}</span>
                          <span className="text-muted-foreground">
                            {(suggestion.current_weight * 100).toFixed(1)}% →{" "}
                            {(suggestion.target_weight * 100).toFixed(1)}% · {suggestion.action}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-muted-foreground">Generate sizing guidance.</div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-4 xl:sticky xl:top-24 xl:self-start">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle>Action Queue</CardTitle>
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard/agent">Send</Link>
              </Button>
            </CardHeader>
            <CardContent className="grid gap-3">
              <QueueBlock
                title="Top risks"
                items={decisionQueue?.top_risks.map((item) => `${item.title} · ${item.why}`) ?? []}
              />
              <QueueBlock
                title="Top opportunities"
                items={
                  decisionQueue?.top_opportunities.map((item) => `${item.title} · ${item.why}`) ?? []
                }
              />
              <QueueBlock
                title="Recommended actions"
                items={decisionQueue?.recommended_actions ?? []}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Next</CardTitle>
            </CardHeader>
            <CardContent>
              <ActionCluster
                items={[
                  { href: "/dashboard/events", label: "Check events", tone: "outline" },
                  { href: "/dashboard/agent", label: "Write memo" },
                ]}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  title,
  value,
  detail,
  freshness,
}: {
  icon: typeof Wallet
  title: string
  value: string
  detail: string
  freshness?: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-xl font-semibold tracking-[-0.04em]">{value}</div>
        <div className="text-xs leading-5 text-muted-foreground">{detail}</div>
        {freshness && (
          <span className="inline-flex rounded-full border border-border/80 bg-white/75 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            {freshness}
          </span>
        )}
      </CardContent>
    </Card>
  )
}

function QueueBlock({ title, items }: { title: string; items: string[] }) {
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
        <div className="text-sm text-muted-foreground">No items queued yet.</div>
      )}
    </div>
  )
}
