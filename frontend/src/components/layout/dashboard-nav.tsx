"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
    BarChart3,
    Globe,
    LayoutDashboard,
    MessageSquare,
    PieChart,
    Settings,
    ShieldAlert
} from "lucide-react"

import { cn } from "@/lib/utils"

const navItems = [
    {
        title: "Overview",
        href: "/dashboard",
        icon: LayoutDashboard,
    },
    {
        title: "Macro",
        href: "/dashboard/macro",
        icon: Globe,
    },
    {
        title: "Portfolio",
        href: "/dashboard/portfolio",
        icon: PieChart,
    },
    {
        title: "Agent",
        href: "/dashboard/agent",
        icon: MessageSquare,
    },
    {
        title: "Risk & Policy",
        href: "/dashboard/policy",
        icon: ShieldAlert,
    },
    {
        title: "Settings",
        href: "/dashboard/settings",
        icon: Settings,
    },
]

export function DashboardNav() {
    const pathname = usePathname()

    return (
        <nav className="grid items-start gap-2">
            {navItems.map((item, index) => {
                const Icon = item.icon
                return (
                    <Link
                        key={index}
                        href={item.href}
                    >
                        <span
                            className={cn(
                                "group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground",
                                pathname === item.href ? "bg-accent text-accent-foreground" : "transparent"
                            )}
                        >
                            <Icon className="mr-2 h-4 w-4" />
                            <span>{item.title}</span>
                        </span>
                    </Link>
                )
            })}
        </nav>
    )
}
