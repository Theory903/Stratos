"use client"

import { useMemo, useState } from "react"
import { CheckCircle2, Circle, Search, XCircle } from "lucide-react"

import { FlowCatalogSection } from "@/lib/server/flow-catalog"
import { cn } from "@/lib/utils"

const STORAGE_KEY = "stratos.flow-catalog.signoff"

type SignoffState = Record<string, "pass" | "fail">

export function FlowCatalogView({ data }: { data: FlowCatalogSection[] }) {
  const [query, setQuery] = useState("")
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [signoff, setSignoff] = useState<SignoffState>(() => {
    if (typeof window === "undefined") {
      return {}
    }
    try {
      return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}") as SignoffState
    } catch {
      return {}
    }
  })

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    return data
      .filter((section) => !activeCategory || section.cat === activeCategory)
      .map((section) => ({
        ...section,
        flows: section.flows.filter((flow) => {
          if (!normalized) {
            return true
          }
          const haystack = `${flow.id} ${flow.name} ${flow.steps.join(" ")} ${flow.edges.map((edge) => edge.join(" ")).join(" ")}`.toLowerCase()
          return haystack.includes(normalized)
        }),
      }))
      .filter((section) => section.flows.length > 0)
  }, [activeCategory, data, query])

  const visibleFlowCount = filtered.reduce((sum, section) => sum + section.flows.length, 0)
  const visibleEdgeCount = filtered.reduce(
    (sum, section) => sum + section.flows.reduce((inner, flow) => inner + flow.edges.length, 0),
    0
  )

  function updateSignoff(id: string, status: "pass" | "fail") {
    const next = { ...signoff, [id]: status }
    setSignoff(next)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Visible flows" value={String(visibleFlowCount)} />
        <StatCard label="Visible edges" value={String(visibleEdgeCount)} />
        <StatCard label="Categories" value={String(data.length)} />
        <StatCard label="Signed off" value={String(Object.keys(signoff).length)} />
      </div>

      <div className="flex flex-col gap-3 rounded-[1.35rem] border border-border/70 bg-white/75 p-4">
        <div className="flex items-center gap-3 rounded-2xl border border-border/70 bg-background/80 px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            placeholder="Search flows, edge cases, or states..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <FilterPill active={activeCategory === null} onClick={() => setActiveCategory(null)}>
            All
          </FilterPill>
          {data.map((section) => (
            <FilterPill
              key={section.cat}
              active={activeCategory === section.cat}
              onClick={() => setActiveCategory(section.cat)}
            >
              {section.cat}
            </FilterPill>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {filtered.map((section) => (
          <div key={section.cat} className="rounded-[1.35rem] border border-border/70 bg-white/75">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: section.color }} />
                <div>
                  <div className="text-sm font-semibold text-slate-950">{section.cat}</div>
                  <div className="text-xs text-muted-foreground">
                    {section.flows.length} flow(s) · {section.flows.reduce((sum, flow) => sum + flow.edges.length, 0)} edge case(s)
                  </div>
                </div>
              </div>
            </div>

            <div className="grid gap-3 border-t border-border/60 p-3">
              {section.flows.map((flow) => {
                const flowOpen = expanded[flow.id] ?? Boolean(query)
                return (
                  <div key={flow.id} className="rounded-2xl border border-border/70 bg-background/75">
                    <button
                      type="button"
                      className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                      onClick={() => setExpanded((current) => ({ ...current, [flow.id]: !flowOpen }))}
                    >
                      <div className="flex items-center gap-3">
                        <span className="rounded bg-primary/8 px-2 py-1 font-mono-ui text-[10px] uppercase tracking-[0.18em] text-primary">
                          {flow.id}
                        </span>
                        <span className="text-sm font-medium text-slate-950">{flow.name}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">{flowOpen ? "Hide" : "Show"}</div>
                    </button>

                    {flowOpen ? (
                      <div className="space-y-4 border-t border-border/60 px-4 py-4">
                        <div className="space-y-2">
                          <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-emerald-600">
                            Happy path
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            {flow.steps.map((step, index) => (
                              <div key={`${flow.id}-${step}-${index}`} className="flex items-center gap-2">
                                <span className="rounded-md border border-border/70 bg-white px-2 py-1 text-xs text-muted-foreground">
                                  {step}
                                </span>
                                {index < flow.steps.length - 1 ? <span className="text-xs text-muted-foreground">→</span> : null}
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-amber-600">
                            Edge cases
                          </div>
                          <div className="grid gap-2">
                            {flow.edges.map(([trigger, resolution]) => (
                              <div key={`${flow.id}-${trigger}`} className="grid gap-1 rounded-xl border border-border/70 bg-white/80 p-3 md:grid-cols-[220px_1fr]">
                                <div className="font-mono-ui text-[11px] text-red-600">{trigger}</div>
                                <div className="text-sm leading-6 text-muted-foreground">{resolution}</div>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            className={cn(
                              "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium",
                              signoff[flow.id] === "pass"
                                ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                                : "border-border/70 bg-white text-muted-foreground"
                            )}
                            onClick={() => updateSignoff(flow.id, "pass")}
                          >
                            <CheckCircle2 className="h-4 w-4" />
                            Pass
                          </button>
                          <button
                            type="button"
                            className={cn(
                              "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-medium",
                              signoff[flow.id] === "fail"
                                ? "border-red-200 bg-red-50 text-red-700"
                                : "border-border/70 bg-white text-muted-foreground"
                            )}
                            onClick={() => updateSignoff(flow.id, "fail")}
                          >
                            <XCircle className="h-4 w-4" />
                            Fail
                          </button>
                          {!signoff[flow.id] ? (
                            <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-white px-3 py-2 text-xs text-muted-foreground">
                              <Circle className="h-3.5 w-3.5" />
                              Not reviewed
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.2rem] border border-border/70 bg-white/75 p-4 text-center">
      <div className="font-display text-2xl font-black tracking-[-0.05em] text-slate-950">{value}</div>
      <div className="mt-1 font-mono-ui text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</div>
    </div>
  )
}

function FilterPill({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={cn(
        "rounded-full border px-3 py-1.5 text-xs transition-colors",
        active
          ? "border-primary/25 bg-primary/5 text-slate-950"
          : "border-border/70 bg-white text-muted-foreground"
      )}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

