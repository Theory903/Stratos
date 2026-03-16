"use client"

import { startTransition, useEffect, useState } from "react"

import { MarketPulseStrip } from "@/components/layout/market-pulse-strip"
import { PulseItem } from "@/lib/app-state"

const POLL_INTERVAL_MS = 60_000

export function LiveHomePulse({ initialItems }: { initialItems: PulseItem[] }) {
  const [items, setItems] = useState(initialItems)

  useEffect(() => {
    let active = true

    async function refreshPulse() {
      try {
        const response = await fetch("/api/market/pulse", {
          method: "GET",
          cache: "no-store",
        })
        if (!response.ok) {
          return
        }

        const payload = (await response.json()) as { items?: PulseItem[] }
        const nextItems = payload.items
        if (!active || !nextItems || nextItems.length === 0) {
          return
        }

        startTransition(() => {
          setItems(nextItems)
        })
      } catch {
        // Keep the last good strip state on any transient error.
      }
    }

    const intervalId = window.setInterval(refreshPulse, POLL_INTERVAL_MS)
    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [])

  return <MarketPulseStrip items={items} variant="dark" />
}
