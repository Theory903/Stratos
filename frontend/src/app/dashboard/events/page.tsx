"use client"

import { startTransition, useEffect, useState } from "react"
import { Loader2, Newspaper, Radar, Sparkles } from "lucide-react"

import {
  api,
  EventCluster,
  EventItem,
  EventPulse,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { StatusPill } from "@/components/dashboard/shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type EventsState = {
  clusters: SnapshotEnvelope<EventCluster[]> | null
  feed: SnapshotEnvelope<EventItem[]> | null
  pulse: SnapshotEnvelope<EventPulse> | null
}

export default function EventsPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<EventsState>({ clusters: null, feed: null, pulse: null })

  useEffect(() => {
    let active = true

    async function loadEvents() {
      try {
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const [pulse, feed, clusters] = await Promise.all([
          request<EventPulse>("/events/pulse/global", "pulse"),
          request<EventItem[]>("/events/feed?scope=global", "feed"),
          request<EventCluster[]>("/events/clusters?scope=global", "clusters"),
        ])

        if (!active) return
        setState({ pulse, feed, clusters })
        setPending({})
      } catch (error) {
        console.error("Failed to load events", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadEvents()
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
            Preparing {pendingItems.map((item) => item.entity_type).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Radar className="h-5 w-5" />
              Event Pulse
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-xl font-semibold">
              {state.pulse?.data.headline ?? (loading ? "Building" : "Unavailable")}
            </div>
            <div className="text-sm text-muted-foreground">
              {state.pulse?.data
                ? `${state.pulse.data.event_count} events · dominant theme ${state.pulse.data.dominant_theme}`
                : "Awaiting pulse snapshot"}
            </div>
            {state.pulse?.meta.freshness && (
              <StatusPill tone="muted">{state.pulse.meta.freshness}</StatusPill>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              Urgency
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-xl font-semibold">
              {state.pulse?.data
                ? `${(state.pulse.data.average_urgency * 100).toFixed(0)}%`
                : loading
                  ? "Building"
                  : "Unavailable"}
            </div>
            <div className="text-sm text-muted-foreground">
              Average urgency across clustered internal events.
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Newspaper className="h-5 w-5" />
              Importance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="text-xl font-semibold">
              {state.pulse?.data
                ? `${(state.pulse.data.average_importance * 100).toFixed(0)}%`
                : loading
                  ? "Building"
                  : "Unavailable"}
            </div>
            <div className="text-sm text-muted-foreground">
              Average importance across the current event pulse.
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Event Feed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(state.feed?.data ?? []).length > 0 ? (
              state.feed?.data.map((item) => (
                <div key={`${item.title}-${item.region}`} className="rounded-lg border bg-muted/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="font-medium">{item.title}</div>
                    <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      {item.region}
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-muted-foreground">{item.summary}</div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {item.category} · urgency {(item.urgency * 100).toFixed(0)}% · importance{" "}
                    {(item.importance * 100).toFixed(0)}%
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building event feed..." : "No event feed available yet."}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Clusters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(state.clusters?.data ?? []).length > 0 ? (
              state.clusters?.data.map((cluster) => (
                <div key={cluster.cluster_id} className="rounded-lg border bg-muted/20 p-3">
                  <div className="font-medium">{cluster.headline}</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {cluster.region} · {cluster.category}
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground">
                    {cluster.event_count} events · importance {(cluster.importance * 100).toFixed(0)}%
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building event clusters..." : "No clusters available yet."}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
