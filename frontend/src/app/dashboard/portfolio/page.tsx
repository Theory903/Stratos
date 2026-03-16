"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { Activity, ArrowUpRight, Bitcoin, CandlestickChart, Loader2 } from "lucide-react"

import {
  api,
  formatRegimeFactorSummary,
  MarketBar,
  MarketRegimeSnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type PortfolioState = {
  btc: SnapshotEnvelope<MarketBar[]> | null
  equity: SnapshotEnvelope<MarketBar[]> | null
  regime: SnapshotEnvelope<MarketRegimeSnapshot> | null
}

export default function PortfolioPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [portfolio, setPortfolio] = useState<PortfolioState>({
    btc: null,
    equity: null,
    regime: null,
  })

  useEffect(() => {
    let active = true

    async function loadPortfolio() {
      try {
        const [equity, btc, regime] = await Promise.all([
          api.pollDataFabricV2<MarketBar[]>("/market/AAPL?limit=30", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, equity: snapshot }))
            })
          }),
          api.pollDataFabricV2<MarketBar[]>("/market/X:BTCUSD?limit=30", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, btc: snapshot }))
            })
          }),
          api.pollDataFabricV2<MarketRegimeSnapshot>("/market/regime", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, regime: snapshot }))
            })
          }),
        ])

        if (!active) return
        startTransition(() => {
          setPortfolio({ equity, btc, regime })
          setPending({})
        })
      } catch (error) {
        console.error("Failed to load portfolio snapshots", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadPortfolio()
    return () => {
      active = false
    }
  }, [])

  const equitySeries = portfolio.equity?.data ?? []
  const btcSeries = portfolio.btc?.data ?? []
  const regime = portfolio.regime?.data
  const pendingItems = Object.values(pending)

  return (
    <div className="flex flex-col gap-6">
      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight">Portfolio Intelligence</h2>
        <p className="max-w-3xl text-sm text-muted-foreground">
          This page is no longer a static placeholder. It reads internal market snapshots and regime
          state so you can reason about portfolio pressure before running the agent.
        </p>
      </div>

      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Refreshing stored market snapshots for {pendingItems.map((item) => item.entity_id).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <SummaryCard
          title="Tracked Equity"
          icon={CandlestickChart}
          symbol="AAPL"
          data={equitySeries}
          freshness={portfolio.equity?.meta.freshness}
          href="/dashboard/company/AAPL"
        />
        <SummaryCard
          title="Tracked Crypto"
          icon={Bitcoin}
          symbol="X:BTCUSD"
          data={btcSeries}
          freshness={portfolio.btc?.meta.freshness}
        />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" /> Regime overlay
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="text-2xl font-semibold">
                {regime ? regime.regime_label : loading ? "Building..." : "Unavailable"}
              </div>
              <div className="text-sm text-muted-foreground">
                {regime
                  ? `${(regime.confidence * 100).toFixed(0)}% confidence`
                  : "Waiting for market regime snapshot"}
              </div>
            </div>
            <div className="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground">
              {regime
                ? formatRegimeFactorSummary(regime.factor_summary)
                : "Use this card as the portfolio gate: if the regime is stale or missing, your agent memo should wait for a fresh internal rebuild."}
            </div>
            {portfolio.regime?.meta.freshness && (
              <span className="inline-flex rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                {portfolio.regime.meta.freshness}
              </span>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SeriesPanel
          title="AAPL last 5 bars"
          bars={equitySeries.slice(0, 5)}
          fallback={loading ? "Building AAPL market snapshot..." : "No AAPL bars stored yet."}
        />
        <SeriesPanel
          title="BTCUSD last 5 bars"
          bars={btcSeries.slice(0, 5)}
          fallback={loading ? "Building BTC market snapshot..." : "No BTC bars stored yet."}
        />
      </div>
    </div>
  )
}

function SummaryCard({
  title,
  icon: Icon,
  symbol,
  data,
  freshness,
  href,
}: {
  title: string
  icon: typeof Activity
  symbol: string
  data: MarketBar[]
  freshness?: string
  href?: string
}) {
  const latest = data[0]
  const oldest = data[data.length - 1]
  const latestClose = latest ? Number(latest.close) : null
  const oldestClose = oldest ? Number(oldest.close) : null
  const absoluteMove =
    latestClose !== null && oldestClose !== null ? latestClose - oldestClose : null
  const relativeMove =
    absoluteMove !== null && oldestClose ? (absoluteMove / oldestClose) * 100 : null

  const content = (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="text-sm text-muted-foreground">{symbol}</div>
          <div className="text-2xl font-semibold">
            {latestClose !== null ? latestClose.toFixed(2) : "Snapshot pending"}
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
          <span>
            {relativeMove !== null ? `${relativeMove.toFixed(2)}% over stored window` : "No return window yet"}
          </span>
        </div>
        <div className="text-sm text-muted-foreground">
          {absoluteMove !== null ? `Move ${absoluteMove.toFixed(2)}` : "Awaiting stored bar history"}
        </div>
        {freshness && (
          <span className="inline-flex rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
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
    <Link className="block transition-transform hover:-translate-y-0.5" href={href}>
      {content}
    </Link>
  )
}

function SeriesPanel({
  title,
  bars,
  fallback,
}: {
  title: string
  bars: MarketBar[]
  fallback: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {bars.length === 0 ? (
          <div className="text-sm text-muted-foreground">{fallback}</div>
        ) : (
          <div className="space-y-3">
            {bars.map((bar) => (
              <div key={`${bar.ticker}-${bar.timestamp}`} className="flex items-center justify-between border-b pb-3 last:border-b-0 last:pb-0">
                <div>
                  <div className="font-medium">{new Date(bar.timestamp).toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">
                    O {Number(bar.open).toFixed(2)} · H {Number(bar.high).toFixed(2)} · L {Number(bar.low).toFixed(2)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-medium">{Number(bar.close).toFixed(2)}</div>
                  <div className="text-xs text-muted-foreground">Vol {bar.volume.toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
