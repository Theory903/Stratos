"use client"

import { startTransition, useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"

import { WorkspaceState } from "@/lib/app-state"
import { navItems } from "@/components/layout/dashboard-nav"
import { cn } from "@/lib/utils"

type PaletteItem = {
  id: string
  label: string
  detail: string
  action: () => void
}

const RECENT_STORAGE_KEY = "stratos.command-palette.recents"

function getDefaultItems(router: ReturnType<typeof useRouter>): PaletteItem[] {
  const defaultNavItems = navItems.map((item) => ({
    id: item.href,
    label: item.title,
    detail: item.summary,
    action: () => router.push(item.href),
  }))

  return [
    ...defaultNavItems,
    {
      id: "scenario",
      label: "Run oil scenario",
      detail: "Open Portfolio and configure scenario run.",
      action: () => router.push("/dashboard/portfolio?scenario=oil_sticky_india_btc"),
    },
    {
      id: "ask-agent",
      label: "Ask agent",
      detail: "Open Agent with a prefilled prompt.",
      action: () =>
        router.push(
          "/dashboard/agent?q=" +
            encodeURIComponent("What do oil, sticky inflation, and BTC sentiment mean for my portfolio?")
        ),
    },
  ]
}

export function DashboardCommandPalette({
  workspace,
  triggerLabel = "Search workspace",
  open: externalOpen,
  onOpenChange,
}: {
  workspace: WorkspaceState
  triggerLabel?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  const router = useRouter()
  const [internalOpen, setInternalOpen] = useState(false)
  const open = externalOpen ?? internalOpen
  const setOpen = onOpenChange ?? setInternalOpen
  const [query, setQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const baseItems = useMemo(() => getDefaultItems(router), [router])
  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      const stored =
        typeof window !== "undefined"
          ? (JSON.parse(window.localStorage.getItem(RECENT_STORAGE_KEY) || "[]") as string[])
          : []
      if (stored.length === 0) {
        return baseItems
      }
      return stored
        .map((id) => baseItems.find((item) => item.id === id))
        .filter((item): item is PaletteItem => Boolean(item))
        .concat(baseItems.filter((item) => !stored.includes(item.id)).slice(0, 4))
    }

    const dynamic: PaletteItem[] = []
    const upperQuery = query.trim().toUpperCase()
    if (/^[A-Z:]{2,12}$/.test(upperQuery)) {
      dynamic.push({
        id: `ticker-${upperQuery}`,
        label: `Open ${upperQuery}`,
        detail: "Jump directly to entity workspace.",
        action: () => router.push(`/dashboard/company/${encodeURIComponent(upperQuery)}`),
      })
    }
    if (/^[A-Za-z]{2,12}$/.test(query.trim()) && query.trim().length <= 5) {
      dynamic.push({
        id: `country-${query.trim().toUpperCase()}`,
        label: `Open country ${query.trim().toUpperCase()}`,
        detail: "Jump directly to country workspace.",
        action: () => router.push(`/dashboard/country/${encodeURIComponent(query.trim().toUpperCase())}`),
      })
    }
    if (normalized.startsWith("ask ")) {
      dynamic.push({
        id: "ask-query",
        label: "Ask agent",
        detail: query.trim().slice(4),
        action: () => router.push(`/dashboard/agent?q=${encodeURIComponent(query.trim().slice(4))}`),
      })
    }
    if (normalized.startsWith("run ")) {
      dynamic.push({
        id: "run-scenario",
        label: "Run scenario",
        detail: query.trim().slice(4),
        action: () =>
          router.push(`/dashboard/portfolio?scenario=${encodeURIComponent(query.trim().slice(4))}`),
      })
    }

    return [
      ...dynamic,
      ...baseItems.filter((item) => `${item.label} ${item.detail}`.toLowerCase().includes(normalized)),
    ].slice(0, 10)
  }, [baseItems, query, router])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setOpen(!open)
      }
      if (event.key === "Escape") {
        setOpen(false)
      }
    }

    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

  useEffect(() => {
    window.dispatchEvent(new CustomEvent("stratos-command-palette", { detail: { open } }))
    if (open) {
      setSelectedIndex(0)
      window.setTimeout(() => inputRef.current?.focus(), 0)
    } else {
      setQuery("")
    }
  }, [open])

  function commit(item: PaletteItem) {
    const stored =
      typeof window !== "undefined"
        ? (JSON.parse(window.localStorage.getItem(RECENT_STORAGE_KEY) || "[]") as string[])
        : []
    const next = [item.id, ...stored.filter((id) => id !== item.id)].slice(0, 8)
    if (typeof window !== "undefined") {
      window.localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(next))
    }
    item.action()
    setOpen(false)
  }

  return (
    <>
      {open ? (
        <div className="fixed inset-0 z-[100] bg-slate-950/45 p-4 backdrop-blur-sm" onClick={() => setOpen(false)}>
          <div
            className="mx-auto mt-[8svh] w-full max-w-2xl rounded-[1.5rem] border border-border/70 bg-white shadow-[0_30px_120px_-48px_rgba(15,23,42,0.5)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-border/60 px-4 py-3">
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault()
                    setSelectedIndex((current) => Math.min(current + 1, results.length - 1))
                  }
                  if (event.key === "ArrowUp") {
                    event.preventDefault()
                    setSelectedIndex((current) => Math.max(current - 1, 0))
                  }
                  if (event.key === "Enter" && results[selectedIndex]) {
                    event.preventDefault()
                    commit(results[selectedIndex])
                  }
                }}
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
                placeholder={`Jump across ${workspace.workspaceName}`}
              />
            </div>
            <div className="max-h-[60svh] overflow-y-auto p-2">
              {results.length === 0 ? (
                <div className="rounded-2xl px-3 py-5 text-sm text-muted-foreground">
                  No results. Try a page name, ticker, country, or <code>ask …</code>.
                </div>
              ) : (
                results.map((item, index) => (
                  <button
                    key={item.id}
                    type="button"
                    className={cn(
                      "grid w-full gap-1 rounded-2xl px-3 py-3 text-left transition-colors",
                      index === selectedIndex ? "bg-primary/6 text-slate-950" : "hover:bg-muted/40"
                    )}
                    onClick={() => commit(item)}
                  >
                    <span className="text-sm font-medium">{item.label}</span>
                    <span className="text-xs text-muted-foreground">{item.detail}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
