"use client"

import Link from "next/link"
import { useParams } from "next/navigation"
import { startTransition, useEffect, useState } from "react"
import { ArrowLeft, Globe2, Landmark, Loader2, ShieldCheck, Waves } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  api,
  CountrySnapshot,
  PendingSnapshot,
  SnapshotEnvelope,
  WorldState,
} from "@/lib/api"

type CountryWorkspaceState = {
  country: SnapshotEnvelope<CountrySnapshot> | null
  policy: SnapshotEnvelope<any[]> | null
  world: SnapshotEnvelope<WorldState> | null
}

export default function CountryWorkspacePage() {
  const params = useParams<{ code: string }>()
  const code = String(params.code || "").toUpperCase()

  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<Record<string, PendingSnapshot>>({})
  const [workspace, setWorkspace] = useState<CountryWorkspaceState>({
    country: null,
    policy: null,
    world: null,
  })

  useEffect(() => {
    let active = true

    async function loadWorkspace() {
      try {
        const searchTerm = code === "IND" ? "India" : code
        const [country, world, policy] = await Promise.all([
          api.pollDataFabricV2<CountrySnapshot>(`/country/${code}`, (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, country: snapshot }))
            })
          }),
          api.pollDataFabricV2<WorldState>("/world-state", (snapshot) => {
            if (!active) return
            startTransition(() => {
              setPending((current) => ({ ...current, world: snapshot }))
            })
          }),
          api.pollDataFabricV2<any[]>(
            `/policy/search?q=${encodeURIComponent(searchTerm)}&scope=global`,
            (snapshot) => {
              if (!active) return
              startTransition(() => {
                setPending((current) => ({ ...current, policy: snapshot }))
              })
            }
          ),
        ])

        if (!active) return
        startTransition(() => {
          setWorkspace({ country, world, policy })
          setPending({})
        })
      } catch (error) {
        console.error(`Failed to load country workspace for ${code}`, error)
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    if (code) {
      loadWorkspace()
    }
    return () => {
      active = false
    }
  }, [code])

  const country = workspace.country?.data
  const world = workspace.world?.data
  const policyEvents = workspace.policy?.data ?? []
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
        <h2 className="text-3xl font-bold tracking-tight">{code} Sovereign Workspace</h2>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Country analysis combines sovereign feature snapshots with global macro context and stored
          policy search results.
        </p>
      </div>

      {pendingItems.length > 0 && (
        <Card className="border-dashed">
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Building internal country artifacts for {pendingItems.map((item) => item.entity_type).join(", ")}.
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 xl:grid-cols-4">
        <CountryMetric
          title="Debt burden"
          icon={Landmark}
          value={country ? country.debt_gdp.toFixed(2) : "Pending"}
          detail="Debt/GDP snapshot"
          freshness={workspace.country?.meta.freshness}
        />
        <CountryMetric
          title="FX reserves"
          icon={ShieldCheck}
          value={country ? country.fx_reserves.toFixed(2) : "Pending"}
          detail="Reserve buffer"
          freshness={workspace.country?.meta.freshness}
        />
        <CountryMetric
          title="Political stability"
          icon={Globe2}
          value={country ? country.political_stability.toFixed(2) : "Pending"}
          detail="Higher tends to mean lower sovereign fragility"
          freshness={workspace.country?.meta.freshness}
        />
        <CountryMetric
          title="Currency volatility"
          icon={Waves}
          value={country ? country.currency_volatility.toFixed(2) : "Pending"}
          detail="FX stress proxy"
          freshness={workspace.country?.meta.freshness}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Country posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border p-4 text-sm text-muted-foreground">
              {country
                ? `Fiscal deficit is ${country.fiscal_deficit.toFixed(2)} while political stability is ${country.political_stability.toFixed(2)}. Use this as the base sovereign read before reacting to single headlines.`
                : loading
                  ? "Building sovereign feature snapshot..."
                  : "No sovereign snapshot stored yet."}
            </div>
            <div className="rounded-lg border p-4 text-sm text-muted-foreground">
              {world
                ? `Global overlay: inflation ${(world.inflation * 100).toFixed(2)}%, rates ${(world.interest_rate * 100).toFixed(2)}%, volatility ${world.volatility_index.toFixed(2)}.`
                : "World-state overlay is not ready yet."}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Policy search results</CardTitle>
          </CardHeader>
          <CardContent>
            {policyEvents.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {loading ? "Searching stored policy documents..." : "No stored policy events matched this country yet."}
              </div>
            ) : (
              <div className="space-y-3">
                {policyEvents.slice(0, 6).map((event, index) => (
                  <div key={`${event.title ?? "policy"}-${index}`} className="border-b pb-3 last:border-b-0 last:pb-0">
                    <div className="font-medium">{event.title ?? event.form ?? "Policy event"}</div>
                    <div className="mt-1 text-sm text-muted-foreground">
                      {event.summary ?? event.filing_date ?? "Stored policy result"}
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

function CountryMetric({
  title,
  icon: Icon,
  value,
  detail,
  freshness,
}: {
  title: string
  icon: typeof Landmark
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
