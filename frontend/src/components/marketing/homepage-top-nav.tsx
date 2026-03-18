"use client"

import Link from "next/link"
import { startTransition, useEffect, useMemo, useRef, useState } from "react"
import { ArrowRight, Command, LogOut, Search, Sparkles } from "lucide-react"

import { DEMO_MODE_ENABLED } from "@/lib/runtime-flags"
import { cn } from "@/lib/utils"

type QuickAction = {
  id: string
  label: string
  detail: string
  href?: string
  onSelect?: () => void
}

export function HomepageTopNav({
  homeHref = "/",
  authenticated = false,
  workspaceHref = "/dashboard",
  userLabel,
}: {
  homeHref?: string
  authenticated?: boolean
  workspaceHref?: string
  userLabel?: string | null
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const actions = useMemo<QuickAction[]>(
    () => {
      const base: QuickAction[] = [
        authenticated
          ? {
              id: "workspace",
              label: "Open workspace",
              detail: "Resume your saved workspace shell and latest dashboard surface.",
              href: workspaceHref,
            }
          : {
              id: "start",
              label: "Start workspace",
              detail: "Create a real STRATOS workspace and continue to onboarding.",
              href: "/auth/signin?return_url=/onboarding/workspace",
            },
        authenticated
          ? {
              id: "logout",
              label: "Log out",
              detail: "End your active local session and return to the public home surface.",
              href: "/api/auth/logout",
            }
          : {
              id: "signin",
              label: "Log in",
              detail: "Resume your workspace, onboarding draft, or latest shell state.",
              href: "/auth/signin",
            },
        {
          id: "pulse",
          label: "Jump to live pulse",
          detail: "See India-first market context in the compact pulse strip.",
          onSelect: () => document.getElementById("pulse")?.scrollIntoView({ behavior: "smooth", block: "start" }),
        },
        {
          id: "workflows",
          label: "Jump to workflows",
          detail: "See Command Center, Portfolio OS, and Decision Agent.",
          onSelect: () => document.getElementById("workflows")?.scrollIntoView({ behavior: "smooth", block: "start" }),
        },
        {
          id: "roles",
          label: "Jump to role lenses",
          detail: "Review PM, Analyst, CFO, and CEO modes.",
          onSelect: () => document.getElementById("roles")?.scrollIntoView({ behavior: "smooth", block: "start" }),
        },
      ]

      if (DEMO_MODE_ENABLED) {
        base.splice(1, 0, {
          id: "demo",
          label: "Try sample workspace",
          detail: "Open the PM demo workspace with sample portfolio data.",
          href: "/api/demo",
        })
      }

      return base
    },
    [authenticated, workspaceHref]
  )

  const filteredActions = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return actions
    }

    return actions.filter((action) =>
      `${action.label} ${action.detail}`.toLowerCase().includes(normalized)
    )
  }, [actions, query])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setOpen((current) => !current)
      }
      if (event.key === "Escape") {
        setOpen(false)
      }
    }

    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  useEffect(() => {
    if (!open) {
      setQuery("")
      return
    }

    setSelectedIndex(0)
    const timeoutId = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => window.clearTimeout(timeoutId)
  }, [open])

  function handleSelect(action: QuickAction) {
    if (action.onSelect) {
      startTransition(() => {
        action.onSelect?.()
      })
    }
    setOpen(false)
  }

  return (
    <>
      <nav className="sticky top-0 z-50 border-b border-slate-800/80 bg-[#06080d]/88 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-[1240px] items-center justify-between gap-3 px-4 py-3 lg:px-8">
          <Link href={homeHref} className="group flex min-w-0 items-center gap-3">
            <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-white/12 bg-[linear-gradient(135deg,rgba(26,140,255,0.95),rgba(0,212,180,0.78))] shadow-[0_12px_28px_-16px_rgba(26,140,255,0.85)]">
              <span className="font-display text-sm font-black text-white">S</span>
              <span className="absolute inset-0 rounded-2xl ring-1 ring-white/12" />
            </div>
            <div className="min-w-0">
              <div className="truncate font-display text-lg font-black tracking-[-0.05em] text-slate-50">
                STRATOS
              </div>
              <div className="truncate font-mono-ui text-[10px] uppercase tracking-[0.22em] text-slate-500 transition-colors group-hover:text-slate-400">
                Decision workspace
              </div>
            </div>
          </Link>

          <div className="flex min-w-0 items-center justify-end gap-2 sm:gap-3">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="inline-flex shrink-0 items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-xs text-slate-300 transition-colors hover:border-slate-700 hover:text-white"
              aria-label="Open quick actions"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden md:inline">{authenticated ? "Search workspace" : "Search product"}</span>
              <span className="rounded-lg border border-slate-700 bg-slate-900 px-1.5 py-0.5 font-mono-ui text-[10px] text-slate-500">
                ⌘K
              </span>
            </button>

            {authenticated ? (
              <>
                <div className="hidden rounded-2xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-xs text-slate-300 sm:block">
                  {userLabel || "Signed in"}
                </div>
                <Link
                  href="/api/auth/logout"
                  className="hidden rounded-2xl px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-slate-900 hover:text-slate-100 sm:inline-flex"
                >
                  <span className="inline-flex items-center gap-2">
                    <LogOut className="h-3.5 w-3.5" />
                    Log out
                  </span>
                </Link>
              </>
            ) : (
              <Link
                href="/auth/signin"
                className="hidden rounded-2xl px-3 py-2 text-sm font-medium text-slate-400 transition-colors hover:bg-slate-900 hover:text-slate-100 sm:inline-flex"
              >
                Log in
              </Link>
            )}

            <Link
              href={authenticated ? workspaceHref : "/auth/signin?return_url=/onboarding/workspace"}
              className="inline-flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-950 transition-all hover:-translate-y-0.5 hover:bg-white"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{authenticated ? "Open workspace" : "Start workspace"}</span>
              <span className="sm:hidden">{authenticated ? "Open" : "Start"}</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {open ? (
        <div className="fixed inset-0 z-[90] bg-slate-950/50 p-4 backdrop-blur-md" onClick={() => setOpen(false)}>
          <div
            className="mx-auto mt-[10svh] w-full max-w-2xl overflow-hidden rounded-[1.75rem] border border-slate-800 bg-[#0a101a] shadow-[0_36px_120px_-48px_rgba(0,0,0,0.85)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-slate-800 px-4 py-3">
              <Command className="h-4 w-4 text-slate-500" />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault()
                    setSelectedIndex((current) => Math.min(current + 1, filteredActions.length - 1))
                  }
                  if (event.key === "ArrowUp") {
                    event.preventDefault()
                    setSelectedIndex((current) => Math.max(current - 1, 0))
                  }
                  if (event.key === "Enter" && filteredActions[selectedIndex]) {
                    event.preventDefault()
                    handleSelect(filteredActions[selectedIndex])
                  }
                }}
                className="w-full bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
                placeholder={
                  authenticated
                    ? "Open workspace, log out, or jump to a section"
                    : DEMO_MODE_ENABLED
                      ? "Jump to workspace setup, demo, or a section on this page"
                      : "Jump to workspace setup or a section on this page"
                }
              />
            </div>

            <div className="max-h-[60svh] overflow-y-auto p-2">
              {filteredActions.length === 0 ? (
                <div className="rounded-2xl px-3 py-5 text-sm text-slate-500">
                  No matching actions. Try “start”, “roles”, or “pulse”.
                </div>
              ) : (
                filteredActions.map((action, index) => {
                  const content = (
                    <span
                      className={cn(
                        "grid w-full gap-1 rounded-2xl px-3 py-3 text-left transition-colors",
                        index === selectedIndex ? "bg-slate-900 text-slate-50" : "hover:bg-slate-900/70"
                      )}
                    >
                      <span className="text-sm font-medium">{action.label}</span>
                      <span className="text-xs text-slate-500">{action.detail}</span>
                    </span>
                  )

                  if (action.href) {
                    return (
                      <Link key={action.id} href={action.href} onClick={() => setOpen(false)}>
                        {content}
                      </Link>
                    )
                  }

                  return (
                    <button key={action.id} type="button" onClick={() => handleSelect(action)} className="w-full">
                      {content}
                    </button>
                  )
                })
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  )
}
