"use client"

import { StatusPill } from "@/components/dashboard/shell"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bell, KeyRound, SlidersHorizontal, UserRoundCog, Workflow } from "lucide-react"

type SettingsCard = {
    title: string
    icon: React.ComponentType<{ className?: string }>
    lines: readonly string[]
    blockTitle?: string
    blockItems?: readonly string[]
    footnote?: string
}

export default function SettingsPage() {
    const cards: readonly SettingsCard[] = [
        {
            title: "Mode",
            icon: UserRoundCog,
            lines: ["Primary: PM / Analyst", "Later: CFO, CEO"],
            blockTitle: "Shared signals",
            blockItems: ["Freshness", "Confidence", "Why it matters", "Action"],
        },
        {
            title: "Defaults",
            icon: SlidersHorizontal,
            lines: ["Portfolio: primary", "Benchmark: SPY"],
            footnote: "Later: watchlists, alerts, scenario packs",
        },
        {
            title: "Alerts",
            icon: Bell,
            lines: ["Macro pressure", "Concentration", "Event urgency"],
        },
        {
            title: "Access",
            icon: KeyRound,
            lines: ["Auth lands here first.", "Portfolio state and decision logs are first."],
        },
        {
            title: "Focus",
            icon: Workflow,
            lines: ["Ship for PM / Analyst first.", "Extend to CFO and CEO later."],
            blockTitle: "One engine",
            blockItems: ["One backend", "One event model", "One agent", "Multiple roles"],
        },
    ] as const

    return (
        <div className="flex flex-col gap-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {cards.map((card) => {
                    const Icon = card.icon

                    return (
                        <Card key={card.title}>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Icon className="h-5 w-5" /> {card.title}
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3 text-sm text-muted-foreground">
                                <div className="space-y-1.5">
                                    {card.lines.map((line) => (
                                        <div key={line}>{line}</div>
                                    ))}
                                </div>

                                {card.blockTitle && card.blockItems ? (
                                    <div className="rounded-md border bg-muted/20 p-3">
                                        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-900">
                                            {card.blockTitle}
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {card.blockItems.map((item) => (
                                                <StatusPill key={item} tone="muted">
                                                    {item}
                                                </StatusPill>
                                            ))}
                                        </div>
                                    </div>
                                ) : null}

                                {card.footnote ? <div>{card.footnote}</div> : null}
                            </CardContent>
                        </Card>
                    )
                })}
            </div>
        </div>
    )
}
