"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  Bell,
  FileSearch,
  LayoutDashboard,
  MessageSquare,
  PieChart,
  Presentation,
  Settings,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { WorkspaceRole } from "@/lib/app-state"

export type DashboardNavItem = {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  summary: string
  roleWeight: Record<WorkspaceRole, number>
  badge?: number
}

export const navItems: DashboardNavItem[] = [
  {
    title: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    summary: "Command center",
    roleWeight: { pm: 1, analyst: 1, cfo: 1, ceo: 1 },
  },
  {
    title: "Portfolio",
    href: "/dashboard/portfolio",
    icon: PieChart,
    summary: "Holdings, risk, actions",
    roleWeight: { pm: 2, analyst: 4, cfo: 2, ceo: 3 },
  },
  {
    title: "Agent",
    href: "/dashboard/agent",
    icon: MessageSquare,
    summary: "Runs, approvals, history",
    roleWeight: { pm: 3, analyst: 5, cfo: 4, ceo: 4 },
  },
  {
    title: "Markets",
    href: "/dashboard/markets",
    icon: BarChart3,
    summary: "Bars, regime, movers",
    roleWeight: { pm: 4, analyst: 2, cfo: 3, ceo: 2 },
  },
  {
    title: "Events",
    href: "/dashboard/events",
    icon: Bell,
    summary: "Pulse, calendars",
    roleWeight: { pm: 5, analyst: 3, cfo: 4, ceo: 3 },
  },
  {
    title: "Research",
    href: "/dashboard/research",
    icon: FileSearch,
    summary: "Briefs, docs, evidence",
    roleWeight: { pm: 6, analyst: 1, cfo: 5, ceo: 4 },
  },
  {
    title: "Studio",
    href: "/dashboard/studio",
    icon: Presentation,
    summary: "Workflows, prompts, power",
    roleWeight: { pm: 7, analyst: 7, cfo: 6, ceo: 5 },
  },
  {
    title: "Settings",
    href: "/dashboard/settings",
    icon: Settings,
    summary: "User, workspace, system",
    roleWeight: { pm: 8, analyst: 8, cfo: 7, ceo: 6 },
  },
]

export function findActiveDashboardItem(pathname: string): DashboardNavItem {
  return (
    navItems.find((item) =>
      item.href === "/dashboard"
        ? pathname === item.href
        : pathname === item.href || pathname.startsWith(`${item.href}/`)
    ) ?? navItems[0]
  )
}

function isNavItemActive(pathname: string, href: string) {
  return href === "/dashboard" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`)
}

export function getNavEmphasis(role: WorkspaceRole): "primary" | "secondary" | "tertiary" {
  return role === "pm" || role === "analyst" ? "primary" : role === "cfo" ? "secondary" : "tertiary"
}

export function DashboardNav({ collapsed = false, role = "pm" }: { collapsed?: boolean; role?: WorkspaceRole }) {
  const pathname = usePathname() ?? "/dashboard"

  const sortedItems = [...navItems].sort((a, b) => {
    return (a.roleWeight[role] ?? 10) - (b.roleWeight[role] ?? 10)
  })

  const getItemStyle = (weight: number) => {
    const emphasis = weight <= 2 ? "primary" : weight <= 4 ? "secondary" : "tertiary"
    return {
      emphasis,
      isPrimary: emphasis === "primary",
      isSecondary: emphasis === "secondary",
    }
  }

  return (
    <nav className="space-y-0.5" aria-label="Dashboard navigation">
      {sortedItems.map((item) => {
        const Icon = item.icon
        const active = isNavItemActive(pathname, item.href)
        const { isPrimary, isSecondary } = getItemStyle(item.roleWeight[role])

        return (
          <Link
            key={item.href}
            href={item.href}
            title={collapsed ? item.title : undefined}
          >
            <div
              className={cn(
                "group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs transition-colors duration-150",
                collapsed && "justify-center px-0",
                active
                  ? "bg-white/[0.08] text-white"
                  : isPrimary
                  ? "text-white/70 hover:bg-white/[0.05] hover:text-white/90"
                  : isSecondary
                  ? "text-white/40 hover:bg-white/[0.05] hover:text-white/60"
                  : "text-white/30 hover:bg-white/[0.05] hover:text-white/50"
              )}
            >
              <Icon className={cn("h-3.5 w-3.5 shrink-0", active && "text-white/80")} />
              {!collapsed && (
                <div className="flex flex-1 items-center gap-2">
                  <span className={cn("flex-1 truncate", isPrimary && "font-medium")}>{item.title}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className={cn(
                      "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                      active ? "bg-white/20" : "bg-white/10"
                    )}>
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </div>
          </Link>
        )
      })}
    </nav>
  )
}

export function DashboardMobileNav({ role = "pm" }: { role?: WorkspaceRole }) {
  const pathname = usePathname() ?? "/dashboard"

  const sortedItems = [...navItems].sort((a, b) => {
    return (a.roleWeight[role] ?? 10) - (b.roleWeight[role] ?? 10)
  })

  return (
    <div className="quiet-scroll overflow-x-auto">
      <div className="flex min-w-max gap-1">
        {sortedItems.map((item) => {
          const Icon = item.icon
          const active = isNavItemActive(pathname, item.href)
          const { isPrimary } = getItemStyle(item.roleWeight[role])

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors",
                active
                  ? "border-black/20 bg-black/[0.06] text-black"
                  : "border-transparent text-black/40 hover:bg-black/[0.03] hover:text-black/60"
              )}
            >
              <Icon className="h-3 w-3" />
              <span className={cn(isPrimary && "font-medium")}>{item.title}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}

function getItemStyle(weight: number) {
  const emphasis = weight <= 2 ? "primary" : weight <= 4 ? "secondary" : "tertiary"
  return {
    isPrimary: emphasis === "primary",
    isSecondary: emphasis === "secondary",
  }
}
