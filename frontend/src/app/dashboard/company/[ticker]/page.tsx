"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { startTransition, useEffect, useState } from "react"
import { ArrowLeft, Building2, FileText, Loader2, Newspaper, ShieldAlert } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  api,
  CompanySnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
} from "@/lib/api"

type CompanyWorkspaceState = {
  company: SnapshotEnvelope<CompanySnapshot> | null
  filings: SnapshotEnvelope<any[]> | null
  news: SnapshotEnvelope<any[]> | null
}

export default function CompanyWorkspacePage() {
  const params = useParams<{ ticker: string }>()
  const ticker = String(params.ticker || "").toUpperCase()

  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [workspace, setWorkspace] = useState<CompanyWorkspaceState>({
    company: null,
    filings: null,
    news: null,
  })

  useEffect(() => {
    let active = true

    async function loadWorkspace() {
      try {
        const [company, filings, news] = await Promise.all([
          api.pollDataFabricV2<CompanySnapshot>(`/company/${ticker}`, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, company: snapshot }))
            })
          }),
          api.pollDataFabricV2<any[]>(`/company/${ticker}/filings`, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, filings: snapshot }))
            })
          }),
          api.pollDataFabricV2<any[]>(`/company/${ticker}/news`, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, news: snapshot }))
            })
          }),
        ])

        if (!active) return
        startTransition(() => {
          setWorkspace({ company, filings, news })
          setPending({})
        })
      } catch (error) {
        console.error(`Failed to load company workspace for ${ticker}`, error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    if (ticker) {
      loadWorkspace()
    }
    return () => {
      active = false
    }
  }, [ticker])

  const company = workspace.company?.data
  const filings = workspace.filings?.data ?? []
  const news = workspace.news?.data ?? []
  const pendingItems = Object.values(pending)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Decision Console
        </Link>
      </div>

      <div className="space-y-1">
        <h2 className="text-3xl font-bold tracking-tight">{ticker} Company Workspace</h2>
        <p className="max-w-3xl text-sm text-muted-foreground">
          This view keeps company analysis inside the internal STRATOS snapshot graph: feature
          scores, stored filings, and stored news/event context.
        </p>
      </div>

      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Building internal company artifacts for {pendingItems.map((item) => item.entity_type).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-4">
        <MetricTile
          title="Company"
          icon={Building2}
          value={company ? company.name : loading ? "Building..." : "Unavailable"}
          detail={company ? company.ticker : "No company snapshot stored yet"}
          freshness={workspace.company?.meta.freshness}
        />
        <MetricTile
          title="Quality"
          icon={ShieldAlert}
          value={company ? company.earnings_quality.toFixed(2) : "Pending"}
          detail={company ? `Moat ${company.moat_score.toFixed(2)}` : "Awaiting feature snapshot"}
          freshness={workspace.company?.meta.freshness}
        />
        <MetricTile
          title="Leverage"
          icon={FileText}
          value={company ? company.leverage_ratio.toFixed(2) : "Pending"}
          detail={
            company
              ? `FCF stability ${company.free_cash_flow_stability.toFixed(2)}`
              : "Awaiting accounting-derived features"
          }
          freshness={workspace.company?.meta.freshness}
        />
        <MetricTile
          title="Risk"
          icon={Newspaper}
          value={company ? company.fraud_score.toFixed(2) : "Pending"}
          detail={
            company
              ? "Lower is better in this provisional scoring model"
              : "Awaiting fraud/risk snapshot"
          }
          freshness={workspace.company?.meta.freshness}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Filings timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {filings.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building filings snapshot..." : "No filings are stored yet for this ticker."}
              </div>
            ) : (
              <div className="space-y-3">
                {filings.slice(0, 6).map((filing, index) => (
                  <div
                    key={`${filing.accession_number ?? filing.form ?? "filing"}-${index}`}
                    className="rounded-lg border p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="font-medium">{filing.form ?? "Filing"}</div>
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        {filing.filing_date ?? "Stored"}
                      </div>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      {filing.primary_document ?? filing.accession_number ?? "Stored filing metadata"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>News and catalyst watch</CardTitle>
          </CardHeader>
          <CardContent>
            {news.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {loading ? "Building company news snapshot..." : "No company news is stored yet for this ticker."}
              </div>
            ) : (
              <div className="space-y-3">
                {news.slice(0, 6).map((item, index) => (
                  <div key={`${item.title ?? "news"}-${index}`} className="border-b pb-3 last:border-b-0 last:pb-0">
                    <div className="font-medium">{item.title ?? "Stored news event"}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {item.summary ?? item.published_at ?? "Internal event snapshot"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function MetricTile({
  title,
  icon: Icon,
  value,
  detail,
  freshness,
}: {
  title: string
  icon: typeof Building2
  value: string
  detail: string
  freshness?: string
}) {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
        {freshness && (
          <span className="inline-flex w-fit rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
            {freshness}
          </span>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-xl font-semibold">{value}</div>
        <div className="mt-2 text-sm text-muted-foreground">{detail}</div>
      </CardContent>
    </Card>
  )
}
