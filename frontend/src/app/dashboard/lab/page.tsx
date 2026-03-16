"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { AlertTriangle, Loader2, Orbit } from "lucide-react"

import {
  AnomalySnapshot,
  api,
  HistoricalRegimeSnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type LabState = {
  anomaly: SnapshotEnvelope<AnomalySnapshot> | null
  history: SnapshotEnvelope<HistoricalRegimeSnapshot> | null
}

export default function LabPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<LabState>({ anomaly: null, history: null })

  useEffect(() => {
    let active = true

    async function loadLab() {
      try {
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const [anomaly, history] = await Promise.all([
          request<AnomalySnapshot>("/anomalies/X:BTCUSD?entity_type=market&metric=close", "anomaly"),
          request<HistoricalRegimeSnapshot>("/history/similar-regimes", "history"),
        ])

        if (!active) return
        setState({ anomaly, history })
        setPending({})
      } catch (error) {
        console.error("Failed to load lab", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadLab()
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Link
          href="/dashboard/lab/flows"
          className="rounded-full border border-border/70 bg-white/80 px-3 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-white"
        >
          Open flow QA map
        </Link>
      </div>
      {Object.values(pending).length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Building anomaly and analog views.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              BTC anomaly lens
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {state.anomaly?.data ? (
              <>
                <div className="text-lg font-semibold capitalize">{state.anomaly.data.severity}</div>
                <div className="text-sm text-muted-foreground">{state.anomaly.data.explanation}</div>
                <div className="grid gap-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Current</span>
                    <span>{state.anomaly.data.current.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Average</span>
                    <span>{state.anomaly.data.average.toFixed(2)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Z-score</span>
                    <span>{state.anomaly.data.z_score.toFixed(2)}</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building anomaly view..." : "No anomaly snapshot available."}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Orbit className="h-5 w-5" />
              Regime analogs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {state.history?.data.analogs?.length ? (
              state.history.data.analogs.slice(0, 4).map((analog) => (
                <div key={`${analog.regime_label}-${analog.as_of}`} className="rounded-lg border bg-muted/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{analog.regime_label}</div>
                    <span className="text-xs text-muted-foreground">
                      {(analog.similarity * 100).toFixed(0)}% similar
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {new Date(analog.as_of).toLocaleDateString()}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building analog set..." : "No analogs available."}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
