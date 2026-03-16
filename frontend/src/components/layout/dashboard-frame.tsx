"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { LogOut, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import { usePathname } from "next/navigation"

import {
  DashboardMobileNav,
  DashboardNav,
  findActiveDashboardItem,
} from "@/components/layout/dashboard-nav"
import { DashboardCommandPalette } from "@/components/layout/dashboard-command-palette"
import { MarketPulseStrip } from "@/components/layout/market-pulse-strip"
import { Button } from "@/components/ui/button"
import { AppSession, PulseItem, WorkspaceState } from "@/lib/app-state"
import { cn } from "@/lib/utils"

const NAV_STORAGE_KEY = "stratos.dashboard.nav-collapsed"

export function DashboardFrame({
  session,
  workspace,
  pulse,
  children,
}: {
  session: AppSession
  workspace: WorkspaceState
  pulse: PulseItem[]
  children: React.ReactNode
}) {
  const pathname = usePathname() ?? "/dashboard"
  const activeItem = findActiveDashboardItem(pathname)
  const [collapsed, setCollapsed] = useState(false)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    setHydrated(true)
    const storedValue = window.localStorage.getItem(NAV_STORAGE_KEY)
    setCollapsed(storedValue === "1")
  }, [])

  useEffect(() => {
    if (!hydrated) {
      return
    }

    window.localStorage.setItem(NAV_STORAGE_KEY, collapsed ? "1" : "0")
  }, [collapsed, hydrated])

  useEffect(() => {
    startTransition(() => {
      fetch("/api/workspace", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace: {
            lastPath: pathname,
          },
        }),
      }).catch(() => null)
    })
  }, [pathname])

  async function handleLogout() {
    window.location.href = "/api/auth/logout"
  }

  return (
    <div className="relative min-h-screen overflow-x-clip">
      <div className="pointer-events-none absolute inset-0 grid-wash opacity-40" />
      <div
        className={cn(
          "relative mx-auto grid min-h-screen w-full max-w-[1760px] min-w-0 xl:grid-cols-[276px_minmax(0,1fr)]",
          collapsed && "xl:grid-cols-[96px_1fr]"
        )}
      >
        <aside
          className={cn(
            "hidden border-r border-slate-900/8 bg-[linear-gradient(180deg,#0f172a_0%,#111827_100%)] text-white xl:sticky xl:top-0 xl:flex xl:h-screen xl:flex-col xl:overflow-hidden xl:transition-[padding,width] xl:duration-200 xl:motion-reduce:transition-none",
            collapsed ? "px-4 py-4" : "px-4 py-5"
          )}
        >
          <div className={cn("flex items-start", collapsed && "justify-center")}>
            <Link
              href="/dashboard"
              className={cn(
                "inline-flex items-center rounded-2xl border border-white/10 bg-white/8 font-mono-ui text-xs uppercase tracking-[0.24em] text-cyan-50 transition-colors duration-200 hover:bg-white/12",
                collapsed ? "justify-center px-3 py-3" : "gap-3 px-3 py-2.5"
              )}
            >
              <span className="text-cyan-200">S</span>
              {!collapsed && <span>STRATOS</span>}
            </Link>
          </div>
          <div className={cn("mt-5 flex-1 pr-1", collapsed && "pr-0")}>
            <DashboardNav collapsed={collapsed} />
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-col">
          <header className="sticky top-0 z-30 border-b border-border/60 bg-background/72 backdrop-blur-xl">
            <div className="mx-auto flex w-full max-w-[1460px] min-w-0 flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-8">
              <div className="min-w-0 flex flex-1 items-center gap-3">
                <div className="hidden xl:block">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    className="rounded-xl border-border/70 bg-white/80 shadow-none"
                    onClick={() => setCollapsed((current) => !current)}
                    aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
                  >
                    {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
                  </Button>
                </div>

                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <h1 className="truncate text-[15px] font-semibold tracking-[-0.03em] text-slate-950 sm:text-base">
                      {activeItem?.title ?? "Command"}
                    </h1>
                    {activeItem?.summary && (
                      <p className="hidden truncate text-sm text-muted-foreground xl:block">
                        {activeItem.summary}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex w-full min-w-0 items-center justify-end gap-2 sm:w-auto sm:flex-wrap xl:flex-nowrap">
                <DashboardCommandPalette workspace={workspace} />
                <Link
                  href="/home"
                  className="hidden rounded-xl border border-border/70 bg-white/80 px-3 py-2 text-xs font-medium text-muted-foreground transition-colors hover:border-border hover:text-slate-950 sm:inline-flex"
                >
                  Public home
                </Link>
                <div className="hidden max-w-[220px] rounded-xl border border-border/70 bg-white/75 px-3 py-2 text-right xl:block">
                  <div className="font-mono-ui text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                    {workspace.workspaceName}
                  </div>
                  <div className="truncate text-xs font-medium text-slate-950">
                    {session.name} · {workspace.role.toUpperCase()}
                  </div>
                </div>
                <Button type="button" variant="outline" size="icon" onClick={handleLogout} aria-label="Log out">
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="border-t border-border/50 bg-white/45 px-4 py-2.5 lg:px-8 xl:hidden">
              <div className="mx-auto w-full max-w-[1460px]">
                <DashboardMobileNav />
              </div>
            </div>
          </header>

          <div className="mx-auto mt-4 flex w-full max-w-[1460px] min-w-0 flex-col gap-3 px-4 lg:px-8">
            <MarketPulseStrip items={pulse} compact variant="light" />
            {(workspace.sampleMode || workspace.demoMode) && (
              <div className="rounded-[1rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Sample data · Not your real portfolio. Saved decisions and exports retain the sample label.
              </div>
            )}
          </div>

          <main className="mx-auto flex w-full max-w-[1460px] min-w-0 flex-1 flex-col gap-4 px-4 py-4 lg:px-8 lg:py-5">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}
