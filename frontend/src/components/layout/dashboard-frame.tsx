"use client"

import Link from "next/link"
import { startTransition, useEffect, useState } from "react"
import { Bell, ChevronDown, LayoutDashboard, PanelLeft, PieChart, Settings, Sparkles, User } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"

import {
  DashboardMobileNav,
  DashboardNav,
  findActiveDashboardItem,
} from "@/components/layout/dashboard-nav"
import { DashboardCommandPalette } from "@/components/layout/dashboard-command-palette"
import { HandoffProvider } from "@/lib/handoff-context"
import { AppSession, PulseItem, WorkspaceState, WorkspaceRole } from "@/lib/app-state"
import { cn } from "@/lib/utils"

const NAV_STORAGE_KEY = "stratos.dashboard.nav-collapsed"

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  pm: "PM",
  analyst: "Analyst",
  cfo: "CFO",
  ceo: "CEO",
}

const ROLE_DESCRIPTIONS: Record<WorkspaceRole, string> = {
  pm: "Portfolio Manager",
  analyst: "Research Analyst",
  cfo: "Chief Financial Officer",
  ceo: "Chief Executive Officer",
}

const ROLE_ICONS: Record<WorkspaceRole, React.ComponentType<{ className?: string }>> = {
  pm: PieChart,
  analyst: LayoutDashboard,
  cfo: Settings,
  ceo: Sparkles,
}

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
  const router = useRouter()
  const activeItem = findActiveDashboardItem(pathname)
  const [collapsed, setCollapsed] = useState(false)
  const [hydrated, setHydrated] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [currentRole, setCurrentRole] = useState<WorkspaceRole>(workspace.role)

  useEffect(() => {
    setHydrated(true)
    const storedValue = window.localStorage.getItem(NAV_STORAGE_KEY)
    setCollapsed(storedValue === "1")
  }, [])

  useEffect(() => {
    if (!hydrated) return
    window.localStorage.setItem(NAV_STORAGE_KEY, collapsed ? "1" : "0")
  }, [collapsed, hydrated])

  useEffect(() => {
    startTransition(() => {
      fetch("/api/workspace", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace: { lastPath: pathname } }),
      }).catch(() => null)
    })
  }, [pathname])

  const handleRoleSwitch = async (newRole: WorkspaceRole) => {
    setCurrentRole(newRole)
    setRoleOpen(false)

    try {
      await fetch("/api/workspace", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workspace: { role: newRole } }),
      })
      router.refresh()
    } catch (error) {
      console.error("Failed to switch role:", error)
    }
  }

  const RoleIcon = ROLE_ICONS[currentRole]

  return (
    <HandoffProvider>
      <div className="flex h-screen overflow-hidden bg-white">
        {/* Sidebar */}
        <aside
          className={cn(
            "flex flex-col border-r border-black/5 bg-[#111] transition-all duration-200",
            collapsed ? "w-14" : "w-[200px]"
          )}
        >
          {/* Brand */}
          <div className={cn("flex items-center gap-3 px-4 py-5", collapsed && "justify-center px-0")}>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white">
              <Sparkles className="h-3.5 w-3.5 text-black" />
            </div>
            {!collapsed && (
              <span className="font-mono text-[11px] font-semibold tracking-[0.2em] text-white/90">
                STRATOS
              </span>
            )}
          </div>

          {/* Toggle */}
          <div className={cn("px-2 pb-3", collapsed && "px-0 flex justify-center")}>
            <button
              onClick={() => setCollapsed((c) => !c)}
              className="flex h-8 w-full items-center gap-2 rounded-md px-2 text-white/50 transition-colors hover:bg-white/5 hover:text-white/80"
              title={collapsed ? "Expand" : "Collapse"}
            >
              <PanelLeft className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="text-xs">Collapse</span>}
            </button>
          </div>

          {/* Nav */}
          <div className="flex-1 overflow-y-auto px-2">
            <DashboardNav collapsed={collapsed} role={currentRole} />
          </div>

          {/* Role indicator */}
          {!collapsed && (
            <div className="border-t border-white/10 px-3 py-2">
              <button
                onClick={() => setRoleOpen(!roleOpen)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-white/60 transition-colors hover:bg-white/5 hover:text-white/80"
              >
                <RoleIcon className="h-3.5 w-3.5" />
                <span className="flex-1 text-left">{ROLE_LABELS[currentRole]}</span>
                <ChevronDown className={cn("h-3 w-3 transition-transform", roleOpen && "rotate-180")} />
              </button>
            </div>
          )}

          {/* Bottom */}
          <div className="border-t border-white/10 px-2 py-3" />
        </aside>

        {/* Main */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <header className="flex h-12 shrink-0 items-center justify-between gap-4 border-b border-black/5 px-6">
            <div className="flex items-center gap-6">
              <h1 className="text-sm font-medium text-black">
                {activeItem?.title ?? "Dashboard"}
              </h1>
              {activeItem?.summary && (
                <span className="text-xs text-black/30">{activeItem.summary}</span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {/* Role Switcher */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setRoleOpen(!roleOpen)}
                  className="flex h-8 items-center gap-2 rounded-md border border-black/10 px-3 text-xs font-medium text-black/70 transition-colors hover:border-black/20 hover:bg-black/[0.03]"
                >
                  <RoleIcon className="h-3 w-3" />
                  <span>{ROLE_LABELS[currentRole]}</span>
                  <ChevronDown className={cn("h-3 w-3 text-black/30", roleOpen && "rotate-180")} />
                </button>

                {roleOpen && (
                  <div className="absolute top-full right-0 mt-1 w-56 rounded-lg border border-black/10 bg-white py-1 shadow-sm z-50">
                    <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-black/40">
                      Switch Role
                    </div>
                    {(Object.keys(ROLE_LABELS) as WorkspaceRole[]).map((role) => {
                      const Icon = ROLE_ICONS[role]
                      const isActive = currentRole === role
                      return (
                        <button
                          key={role}
                          type="button"
                          className={cn(
                            "flex w-full items-start gap-2.5 px-3 py-2 text-xs transition-colors",
                            isActive
                              ? "bg-black/[0.05] text-black"
                              : "text-black/60 hover:bg-black/[0.03] hover:text-black/80"
                          )}
                          onClick={() => handleRoleSwitch(role)}
                        >
                          <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          <div className="flex-1 text-left">
                            <div className={cn("font-medium", isActive && "text-black")}>
                              {ROLE_LABELS[role]}
                            </div>
                            <div className="text-[10px] text-black/40">
                              {ROLE_DESCRIPTIONS[role]}
                            </div>
                          </div>
                          {isActive && (
                            <div className="mt-1 h-1.5 w-1.5 rounded-full bg-black/40" />
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Notifications */}
              <button className="relative flex h-8 w-8 items-center justify-center rounded-md text-black/40 transition-colors hover:bg-black/[0.03] hover:text-black/70">
                <Bell className="h-3.5 w-3.5" />
                {/* TODO: Show notification badge */}
              </button>

              {/* Avatar */}
              <button className="flex h-8 w-8 items-center justify-center rounded-md bg-black/[0.07] text-xs font-medium text-black/60 transition-colors hover:bg-black/[0.1]">
                {session.name?.charAt(0) || "U"}
              </button>
            </div>
          </header>

          {/* Mobile Nav */}
          <div className="border-b border-black/5 bg-white/50 px-4 py-2 lg:hidden">
            <DashboardMobileNav role={currentRole} />
          </div>

          {/* Content */}
          <main className="flex-1 overflow-auto p-6">
            {children}
          </main>
        </div>
      </div>

      {/* Command Palette */}
      <DashboardCommandPalette
        open={searchOpen}
        onOpenChange={setSearchOpen}
        workspace={workspace}
      />

      {/* Click outside */}
      {roleOpen && (
        <div className="fixed inset-0 z-40" onClick={() => setRoleOpen(false)} />
      )}
    </HandoffProvider>
  )
}
