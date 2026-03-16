"use client"

import { startTransition, useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ShieldAlert, Landmark, Scale } from "lucide-react"
import { api, PendingSnapshot } from "@/lib/api"

export default function PolicyPage() {
    const [events, setEvents] = useState<any[]>([])
    const [pending, setPending] = useState<PendingSnapshot | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let active = true
        async function loadPolicy() {
            try {
                const snapshot = await api.pollDataFabricV2<any[]>("/policy/events", (pendingState) => {
                    if (!active) return
                    startTransition(() => setPending(pendingState))
                })
                if (!active) return
                startTransition(() => {
                    setEvents(snapshot.data)
                    setPending(null)
                })
            } catch (error) {
                console.error("Failed to load policy events", error)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }
        loadPolicy()
        return () => {
            active = false
        }
    }, [])

    return (
        <div className="flex flex-col gap-6">
            <h2 className="text-3xl font-bold tracking-tight">Risk & Policy</h2>

            {loading && (
                <Card className="border-dashed">
                    <CardContent className="pt-6 text-sm text-muted-foreground">
                        {pending
                            ? `Preparing internal policy snapshot for ${pending.entity_id}...`
                            : "Loading policy snapshot..."}
                    </CardContent>
                </Card>
            )}

            <div className="grid gap-6 md:grid-cols-3">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ShieldAlert className="h-5 w-5" /> Regulatory Watch
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                        Monitoring active policy and compliance developments across tracked markets.
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Landmark className="h-5 w-5" /> Central Bank Signals
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                        Scenario models for rates, liquidity, and sovereign balance-sheet changes land here.
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Scale className="h-5 w-5" /> Policy Simulation
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground">
                        Wiring this page into orchestrator policy tools is the next backend integration step.
                    </CardContent>
                </Card>
            </div>

            {!loading && events.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Latest Internal Policy Events</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {events.slice(0, 5).map((event, index) => (
                            <div key={`${event.title ?? "policy"}-${index}`} className="border-b pb-3 last:border-b-0">
                                <div className="font-medium">{event.title ?? event.form ?? "Policy event"}</div>
                                <div className="text-sm text-muted-foreground">
                                    {event.summary ?? event.filing_date ?? "Stored internal event snapshot"}
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    )
}
