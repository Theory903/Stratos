"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { Activity, ArrowUpRight, Building2, Globe2, Loader2, ShieldCheck } from "lucide-react"

import {
  api,
  CompanySnapshot,
  CountrySnapshot,
  formatRegimeFactorSummary,
  MarketRegimeSnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
  WorldState,
} from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type OverviewState = {
  company: SnapshotEnvelope<CompanySnapshot> | null
  country: SnapshotEnvelope<CountrySnapshot> | null
  regime: SnapshotEnvelope<MarketRegimeSnapshot> | null
  world: SnapshotEnvelope<WorldState> | null
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true)
  const [overview, setOverview] = useState<OverviewState>({
    company: null,
    country: null,
    regime: null,
    world: null,
  })
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})

  useEffect(() => {
    let active = true

    async function loadOverview() {
      try {
        const [world, regime, company, country] = await Promise.all([
          api.pollDataFabricV2<WorldState>("/world-state", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, world: snapshot }))
            })
          }),
          api.pollDataFabricV2<MarketRegimeSnapshot>("/market/regime", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, regime: snapshot }))
            })
          }),
          api.pollDataFabricV2<CompanySnapshot>("/company/AAPL", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, company: snapshot }))
            })
          }),
          api.pollDataFabricV2<CountrySnapshot>("/country/IND", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, country: snapshot }))
            })
          }),
        ])

        if (!active) return
        startTransition(() => {
          setOverview({ world, regime, company, country })
          setPending({})
        })
      } catch (error) {
        console.error("Failed to load overview snapshots", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadOverview()
    return () => {
      active = false
    }
  }, [])

  const pendingItems = Object.values(pending)
  const world = overview.world?.data
  const regime = overview.regime?.data
  const company = overview.company?.data
  const country = overview.country?.data

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold tracking-tight">Decision Console</h2>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Snapshot-first overview of macro state, regime pressure, flagship company quality, and
            India sovereign risk. Every card below reads from STRATOS internal data, not live
            third-party APIs.
          </p>
        </div>
      </div>

      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing internal snapshots for{" "}
            {pendingItems.map((item) => item.entity_id).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Macro Pressure"
          icon={Globe2}
          value={
            world
              ? `${(world.inflation * 100).toFixed(2)}% CPI / ${(world.interest_rate * 100).toFixed(2)}% rates`
              : "Snapshot pending"
          }
          detail={
            world
              ? `Liquidity ${world.liquidity_index.toFixed(2)} · Volatility ${world.volatility_index.toFixed(2)}`
              : "Waiting for world-state snapshot"
          }
          freshness={overview.world?.meta.freshness}
        />
        <MetricCard
          title="Market Regime"
          icon={Activity}
          value={regime ? regime.regime_label : "Snapshot pending"}
          detail={
            regime
              ? `${(regime.confidence * 100).toFixed(0)}% confidence · ${formatRegimeFactorSummary(
                  regime.factor_summary
                )}`
              : "Waiting for market regime snapshot"
          }
          freshness={overview.regime?.meta.freshness}
        />
        <MetricCard
          title="Tracked Company"
          icon={Building2}
          value={company ? `${company.ticker} · ${company.name}` : "Snapshot pending"}
          detail={
            company
              ? `Moat ${company.moat_score.toFixed(2)} · Fraud ${company.fraud_score.toFixed(2)}`
              : "Waiting for company feature snapshot"
          }
          freshness={overview.company?.meta.freshness}
          href={company ? `/dashboard/company/${company.ticker}` : undefined}
        />
        <MetricCard
          title="India Sovereign"
          icon={ShieldCheck}
          value={country ? `${country.country_code} profile ready` : "Snapshot pending"}
          detail={
            country
              ? `Debt/GDP ${country.debt_gdp.toFixed(2)} · FX reserves ${country.fx_reserves.toFixed(2)}`
              : "Waiting for country feature snapshot"
          }
          freshness={overview.country?.meta.freshness}
          href={country ? `/dashboard/country/${country.country_code}` : undefined}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Priority Reads</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <InsightPanel
              title="Macro heatmap"
              eyebrow={overview.world?.meta.freshness}
              summary={
                world
                  ? world.inflation > 0.03
                    ? "Inflation is still running above a comfortable range. Treat duration and richly valued growth with more caution."
                    : "Inflation is contained enough to keep policy pressure from dominating every decision."
                  : "Awaiting stored macro snapshot."
              }
              bullets={[
                world ? `Geopolitical risk ${world.geopolitical_risk.toFixed(2)}` : "World state pending",
                world ? `Commodity index ${world.commodity_index.toFixed(2)}` : "No commodity reading yet",
              ]}
            />
            <InsightPanel
              title="Company quality checkpoint"
              eyebrow={overview.company?.meta.freshness}
              summary={
                company
                  ? `${company.name} currently scores ${company.earnings_quality.toFixed(2)} on earnings quality with leverage at ${company.leverage_ratio.toFixed(2)}.`
                  : "Awaiting stored company snapshot."
              }
              bullets={[
                company
                  ? `Free cash flow stability ${company.free_cash_flow_stability.toFixed(2)}`
                  : "Feature build pending",
                company ? `Moat score ${company.moat_score.toFixed(2)}` : "No moat signal yet",
              ]}
            />
            <InsightPanel
              title="India watch"
              eyebrow={overview.country?.meta.freshness}
              summary={
                country
                  ? `Political stability ${country.political_stability.toFixed(2)} with currency volatility ${country.currency_volatility.toFixed(2)}.`
                  : "Awaiting stored India snapshot."
              }
              bullets={[
                country ? `Fiscal deficit ${country.fiscal_deficit.toFixed(2)}` : "Country feature build pending",
                country ? `FX reserves ${country.fx_reserves.toFixed(2)}` : "No reserve snapshot yet",
              ]}
            />
            <InsightPanel
              title="Action framing"
              eyebrow={overview.regime?.meta.freshness}
              summary={
                regime
                  ? `Use the ${regime.regime_label} regime as the default frame for portfolio and policy decisions.`
                  : "Awaiting stored regime snapshot."
              }
              bullets={[
                "Use the Macro tab for top-down risk context",
                "Use Portfolio to inspect tracked market bars and price pressure",
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Operator Checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <ChecklistRow
              title="Macro snapshot"
              value={world ? "Ready" : loading ? "Building" : "Unavailable"}
            />
            <ChecklistRow
              title="Regime snapshot"
              value={regime ? "Ready" : loading ? "Building" : "Unavailable"}
            />
            <ChecklistRow
              title="Company features"
              value={company ? "Ready" : loading ? "Building" : "Unavailable"}
            />
            <ChecklistRow
              title="Country features"
              value={country ? "Ready" : loading ? "Building" : "Unavailable"}
            />

            <div className="rounded-lg border bg-muted/40 p-4">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <ArrowUpRight className="h-4 w-4" />
                Next best route
              </div>
              <p className="text-muted-foreground">
                Ask the agent for a decision memo once the four core snapshots are ready. That keeps
                orchestration grounded in internal data instead of ad hoc live fetches.
              </p>
            </div>
          </CardContent>
        </Card>
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
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="space-y-1">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          {freshness && (
            <span className="inline-flex rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
              {freshness}
            </span>
          )}
        </div>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-xl font-semibold leading-tight">{value}</div>
        <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  )

  if (!href) {
    return content
  }

  return (
    <Link className="block transition-transform hover:-translate-y-0.5" href={href}>
      {content}
    </Link>
  )
}

function InsightPanel({
  title,
  eyebrow,
  summary,
  bullets,
}: {
  title: string
  eyebrow?: string
  summary: string
  bullets: string[]
}) {
  return (
    <div className="rounded-xl border p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="font-medium">{title}</div>
        {eyebrow && <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</div>}
      </div>
      <p className="text-sm text-muted-foreground">{summary}</p>
      <div className="mt-3 space-y-2 text-sm">
        {bullets.map((bullet) => (
          <div key={bullet} className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-foreground/50" />
            <span>{bullet}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChecklistRow({ title, value }: { title: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b pb-2 last:border-b-0 last:pb-0">
      <span className="text-muted-foreground">{title}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
