"use client"

import { startTransition, useEffect, useState } from "react"
import { Activity, Bitcoin, CandlestickChart, Loader2 } from "lucide-react"

import {
  api,
  formatRegimeFactorSummary,
  MarketBar,
  MarketRegimeSnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { StatusPill } from "@/components/dashboard/shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type MarketsState = {
  btc: SnapshotEnvelope<MarketBar[]> | null
  equity: SnapshotEnvelope<MarketBar[]> | null
  regime: SnapshotEnvelope<MarketRegimeSnapshot> | null
}

export default function MarketsPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<MarketsState>({ btc: null, equity: null, regime: null })

  useEffect(() => {
    let active = true

    async function loadMarkets() {
      try {
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const [equity, btc, regime] = await Promise.all([
          request<MarketBar[]>("/market/AAPL?limit=20", "equity"),
          request<MarketBar[]>("/market/X:BTCUSD?limit=20", "btc"),
          request<MarketRegimeSnapshot>("/market/regime", "regime"),
        ])

        if (!active) return
        setState({ equity, btc, regime })
        setPending({})
      } catch (error) {
        console.error("Failed to load markets", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadMarkets()
    return () => {
      active = false
    }
  }, [])

  const pendingItems = Object.values(pending)

  return (
    <div className="flex flex-col gap-4">
      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Refreshing {pendingItems.map((item) => item.entity_id).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <SeriesSummary
          icon={CandlestickChart}
          title="AAPL"
          bars={state.equity?.data ?? []}
          freshness={state.equity?.meta.freshness}
        />
        <SeriesSummary
          icon={Bitcoin}
          title="BTCUSD"
          bars={state.btc?.data ?? []}
          freshness={state.btc?.meta.freshness}
        />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Regime Overlay
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-2xl font-semibold">
              {state.regime?.data.regime_label ?? (loading ? "Building" : "Unavailable")}
            </div>
            <div className="text-sm text-muted-foreground">
              {state.regime?.data
                ? `${(state.regime.data.confidence * 100).toFixed(0)}% confidence · ${formatRegimeFactorSummary(
                    state.regime.data.factor_summary
                  )}`
                : "Awaiting regime overlay"}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SeriesPanel
          title="AAPL stored bars"
          bars={state.equity?.data.slice(0, 8) ?? []}
          fallback={loading ? "Building AAPL bars..." : "No AAPL bars stored yet."}
        />
        <SeriesPanel
          title="BTC stored bars"
          bars={state.btc?.data.slice(0, 8) ?? []}
          fallback={loading ? "Building BTC bars..." : "No BTC bars stored yet."}
        />
      </div>
    </div>
  )
}

function SeriesSummary({
  icon: Icon,
  title,
  bars,
  freshness,
}: {
  icon: typeof CandlestickChart
  title: string
  bars: MarketBar[]
  freshness?: string
}) {
  const latest = bars[0]
  const oldest = bars[bars.length - 1]
  const latestClose = latest ? Number(latest.close) : null
  const oldestClose = oldest ? Number(oldest.close) : null
  const relativeMove =
    latestClose !== null && oldestClose ? ((latestClose - oldestClose) / oldestClose) * 100 : null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="text-2xl font-semibold">
          {latestClose !== null ? latestClose.toFixed(2) : "Unavailable"}
        </div>
        <div className="text-sm text-muted-foreground">
          {relativeMove !== null ? `${relativeMove.toFixed(2)}% over stored window` : "No return window yet"}
        </div>
        {freshness && <StatusPill tone="muted">{freshness}</StatusPill>}
      </CardContent>
    </Card>
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
              <div
                key={`${bar.ticker}-${bar.timestamp}`}
                className="flex items-center justify-between rounded-lg border bg-muted/20 p-3"
              >
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
