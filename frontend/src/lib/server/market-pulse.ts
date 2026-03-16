import "server-only"

import { HOME_PULSE_CONFIG, PulseItem } from "@/lib/app-state"

type MarketBar = {
  close: string
  timestamp: string
}

type MarketResponse =
  | {
      data?: MarketBar[]
      meta?: { freshness?: "fresh" | "stale" }
    }
  | MarketBar[]

const DATA_FABRIC_V2 =
  (process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000").replace(/\/+$/, "") + "/api/v2"

type MarketPulseMode = "initial" | "fresh"

function formatValue(raw: number, symbol: string): string {
  if (symbol === "MACRO:US10Y") {
    return `${raw.toFixed(2)}%`
  }
  if (symbol === "X:XAUUSD" || symbol === "CMD:CRUDE") {
    return raw.toFixed(1)
  }
  if (raw >= 1000) {
    return raw.toLocaleString(undefined, { maximumFractionDigits: 0 })
  }
  return raw.toFixed(2)
}

function parseBars(payload: MarketResponse): {
  bars: MarketBar[]
  freshness: "fresh" | "stale"
} {
  if (Array.isArray(payload)) {
    return { bars: payload, freshness: "fresh" }
  }

  return {
    bars: payload.data ?? [],
    freshness: payload.meta?.freshness ?? "stale",
  }
}

export async function getMarketPulseItems(mode: MarketPulseMode = "initial"): Promise<PulseItem[]> {
  const requests = HOME_PULSE_CONFIG.map(async (config) => {
    const url = `${DATA_FABRIC_V2}/market/${encodeURIComponent(config.symbol)}?limit=2&include_meta=true`
    try {
      const response = await fetch(url, {
        ...(mode === "fresh" ? { cache: "no-store" as const } : { next: { revalidate: 120 } }),
      })
      if (!response.ok) {
        throw new Error(`Market request failed: ${response.status}`)
      }

      const payload = (await response.json()) as MarketResponse
      const { bars, freshness } = parseBars(payload)
      if (bars.length < 2) {
        throw new Error("Not enough bars")
      }

      const latest = Number.parseFloat(bars[bars.length - 1].close)
      const prior = Number.parseFloat(bars[bars.length - 2].close)
      const change = prior === 0 ? 0 : ((latest - prior) / prior) * 100

      return {
        label: config.label,
        symbol: config.symbol,
        value: formatValue(latest, config.symbol),
        change,
        freshness,
        timestamp: bars[bars.length - 1].timestamp,
      } satisfies PulseItem
    } catch {
      return {
        label: config.label,
        symbol: config.symbol,
        value: config.fallbackValue,
        change: config.fallbackChange,
        freshness: "stale",
        timestamp: null,
      } satisfies PulseItem
    }
  })

  return Promise.all(requests)
}
