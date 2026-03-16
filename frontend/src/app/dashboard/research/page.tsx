"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { Building2, FileSearch, Loader2, ShieldCheck } from "lucide-react"

import {
  api,
  CompareEntitySnapshot,
  CompareMetricSnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type ResearchState = {
  companyCompare: SnapshotEnvelope<CompareEntitySnapshot> | null
  companyFraud: SnapshotEnvelope<CompareMetricSnapshot> | null
  countryCompare: SnapshotEnvelope<CompareEntitySnapshot> | null
}

export default function ResearchPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [state, setState] = useState<ResearchState>({
    companyCompare: null,
    companyFraud: null,
    countryCompare: null,
  })

  useEffect(() => {
    let active = true

    async function loadResearch() {
      try {
        const request = <T,>(path: string, key: string) =>
          api.pollDataFabricV2<T>(path, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, [key]: snapshot }))
            })
          })

        const [companyCompare, companyFraud, countryCompare] = await Promise.all([
          request<CompareEntitySnapshot>("/compare/entity?entity_type=company&entity_id=AAPL", "companyCompare"),
          request<CompareMetricSnapshot>("/compare/metric?entity_type=company&entity_id=AAPL&metric=fraud_score", "companyFraud"),
          request<CompareEntitySnapshot>("/compare/entity?entity_type=country&entity_id=IND", "countryCompare"),
        ])

        if (!active) return
        setState({ companyCompare, companyFraud, countryCompare })
        setPending({})
      } catch (error) {
        console.error("Failed to load research views", error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadResearch()
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="flex flex-col gap-4">
      {Object.values(pending).length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Preparing compare views.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-3">
        <ResearchCard
          icon={Building2}
          title="AAPL quality delta"
          href="/dashboard/company/AAPL"
          items={state.companyCompare?.data.deltas ?? {}}
        />
        <MetricCard
          icon={FileSearch}
          title="AAPL fraud score context"
          snapshot={state.companyFraud}
          fallback={loading ? "Building compare metric..." : "No metric snapshot available."}
        />
        <ResearchCard
          icon={ShieldCheck}
          title="India sovereign delta"
          href="/dashboard/country/IND"
          items={state.countryCompare?.data.deltas ?? {}}
        />
      </div>
    </div>
  )
}

function ResearchCard({
  icon: Icon,
  title,
  href,
  items,
}: {
  icon: typeof Building2
  title: string
  href: string
  items: Record<string, number>
}) {
  const content = (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {Object.keys(items).length > 0 ? (
          <div className="space-y-3 text-sm">
            {Object.entries(items).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-muted-foreground">{key}</span>
                <span>{value.toFixed(3)}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">Awaiting compare snapshot.</div>
        )}
      </CardContent>
    </Card>
  )

  return (
    <Link className="block transition-transform hover:-translate-y-0.5" href={href}>
      {content}
    </Link>
  )
}

function MetricCard({
  icon: Icon,
  title,
  snapshot,
  fallback,
}: {
  icon: typeof FileSearch
  title: string
  snapshot: SnapshotEnvelope<CompareMetricSnapshot> | null
  fallback: string
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icon className="h-5 w-5" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {snapshot?.data ? (
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Current</span>
              <span>{snapshot.data.current.toFixed(3)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Average</span>
              <span>{snapshot.data.average.toFixed(3)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Percentile</span>
              <span>{(snapshot.data.percentile_rank * 100).toFixed(0)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Z-score</span>
              <span>{snapshot.data.z_score.toFixed(2)}</span>
            </div>
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">{fallback}</div>
        )}
      </CardContent>
    </Card>
  )
}
