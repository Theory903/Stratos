"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  BarChart3,
  FileSearch,
  FlaskConical,
  Globe,
  LayoutDashboard,
  MessageSquare,
  PieChart,
  Presentation,
  Settings,
} from "lucide-react"

import { cn } from "@/lib/utils"

export type DashboardNavItem = {
  title: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  summary: string
}

type DashboardSection = {
  title: string
  items: DashboardNavItem[]
}

export const dashboardSections: DashboardSection[] = [
  {
    title: "Operate",
    items: [
      {
        title: "Command",
        href: "/dashboard",
        icon: LayoutDashboard,
        summary: "Posture and queue.",
      },
      {
        title: "Portfolio",
        href: "/dashboard/portfolio",
        icon: PieChart,
        summary: "Book, risk, action.",
      },
      {
        title: "Agent",
        href: "/dashboard/agent",
        icon: MessageSquare,
        summary: "Ask, run, memo.",
      },
    ],
  },
  {
    title: "Intelligence",
    items: [
      {
        title: "Markets",
        href: "/dashboard/markets",
        icon: BarChart3,
        summary: "Bars and regime.",
      },
      {
        title: "Events",
        href: "/dashboard/events",
        icon: Globe,
        summary: "Pulse and clusters.",
      },
      {
        title: "Research",
        href: "/dashboard/research",
        icon: FileSearch,
        summary: "Compare and drill down.",
      },
    ],
  },
  {
    title: "Explore",
    items: [
      {
        title: "Lab",
        href: "/dashboard/lab",
        icon: FlaskConical,
        summary: "Analogs and anomalies.",
      },
      {
        title: "Studio",
        href: "/dashboard/studio",
        icon: Presentation,
        summary: "Export surface.",
      },
      {
        title: "Settings",
        href: "/dashboard/settings",
        icon: Settings,
        summary: "Role and defaults.",
      },
    ],
  },
] as const

const flatNavItems: DashboardNavItem[] = dashboardSections.flatMap((section) => section.items)

export function findActiveDashboardItem(pathname: string): DashboardNavItem {
  return (
    flatNavItems.find((item) =>
      item.href === "/dashboard"
        ? pathname === item.href
        : pathname === item.href || pathname.startsWith(`${item.href}/`)
    ) ?? flatNavItems[0]
  )
}

function isNavItemActive(pathname: string, href: string) {
  return href === "/dashboard" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`)
}

export function DashboardNav({ collapsed = false }: { collapsed?: boolean }) {
  const pathname = usePathname() ?? "/dashboard"

  return (
    <nav className="grid items-start gap-5" aria-label="Dashboard navigation">
      {dashboardSections.map((section) => (
        <div key={section.title} className="space-y-2">
          {!collapsed ? (
            <div className="font-mono-ui px-3 text-[11px] uppercase tracking-[0.24em] text-slate-400">
              {section.title}
            </div>
          ) : (
            <div className="mx-auto h-px w-8 bg-white/10" />
          )}
          <div className="space-y-1">
            {section.items.map((item) => {
              const Icon = item.icon
              const active = isNavItemActive(pathname, item.href)
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  title={collapsed ? item.title : undefined}
                >
                  <span
                    className={cn(
                      "group flex items-center rounded-2xl border text-sm transition-[background-color,border-color,transform,color] duration-200 motion-reduce:transition-none",
                      collapsed ? "justify-center px-0 py-3" : "justify-between px-3 py-3",
                      active
                        ? "border-cyan-300/25 bg-white/12 text-white"
                        : "border-transparent text-slate-300 hover:border-white/8 hover:bg-white/6 hover:text-white"
                    )}
                  >
                    <span className={cn("flex items-center", collapsed ? "justify-center" : "gap-3")}>
                      <span
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-2xl border transition-colors duration-200 motion-reduce:transition-none",
                          active
                            ? "border-white/10 bg-white/10 text-cyan-100"
                            : "border-white/0 bg-transparent text-slate-300 group-hover:border-white/10 group-hover:bg-white/8 group-hover:text-white"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </span>
                      {!collapsed && <span className="font-medium">{item.title}</span>}
                    </span>
                    {!collapsed && (
                      <span
                        className={cn(
                          "h-2 w-2 rounded-full transition-opacity duration-200 motion-reduce:transition-none",
                          active ? "bg-cyan-300 opacity-100" : "bg-slate-500 opacity-0 group-hover:opacity-100"
                        )}
                      />
                    )}
                  </span>
                </Link>
              )
            })}
          </div>
        </div>
      ))}
    </nav>
  )
}

export function DashboardMobileNav() {
  const pathname = usePathname() ?? "/dashboard"

  return (
    <div className="quiet-scroll overflow-x-auto">
      <div className="flex min-w-max gap-2">
        {flatNavItems.map((item) => {
          const Icon = item.icon
          const active = isNavItemActive(pathname, item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-[background-color,border-color,color] duration-200 motion-reduce:transition-none",
                active
                  ? "border-cyan-300/50 bg-cyan-50 text-slate-950"
                  : "border-border/70 bg-white/75 text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span>{item.title}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
