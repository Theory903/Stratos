// Macro Dashboard Page
"use client"

import { startTransition, useEffect, useState } from "react"
import { api, PendingSnapshot, WorldState } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Globe, TrendingUp, AlertTriangle, DollarSign } from "lucide-react"

export default function MacroPage() {
    const [worldState, setWorldState] = useState<WorldState | null>(null)
    const [loading, setLoading] = useState(true)
    const [pending, setPending] = useState<PendingSnapshot | null>(null)
    const [retryIn, setRetryIn] = useState<number | null>(null)

    useEffect(() => {
        let active = true

        async function fetchData() {
            try {
                const snapshot = await api.pollDataFabricV2<WorldState>(
                    "/world-state",
                    (pendingState) => {
                        if (!active) return
                        startTransition(() => {
                            setPending(pendingState)
                            setRetryIn(pendingState.suggested_retry_seconds)
                        })
                    }
                )
                if (!active) return
                startTransition(() => {
                    setWorldState(snapshot.data)
                    setPending(null)
                    setRetryIn(null)
                })
            } catch (e) {
                console.error("Failed to fetch world state", e)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }
        fetchData()

        return () => {
            active = false
        }
    }, [])

    useEffect(() => {
        if (retryIn === null || retryIn <= 0) {
            return
        }
        const handle = window.setInterval(() => {
            setRetryIn((current) => {
                if (current === null || current <= 1) {
                    window.clearInterval(handle)
                    return 0
                }
                return current - 1
            })
        }, 1000)
        return () => window.clearInterval(handle)
    }, [retryIn])

    if (loading) {
        return (
            <div className="p-8">
                {pending ? (
                    <div className="space-y-2">
                        <div>Preparing global macro snapshot...</div>
                        <div className="text-sm text-muted-foreground">
                            Auto-refreshing in {retryIn ?? pending.suggested_retry_seconds}s
                        </div>
                    </div>
                ) : (
                    <div>Loading global macro data...</div>
                )}
            </div>
        )
    }
    if (!worldState) return <div className="p-8">Failed to load macro data. Ensure Data Fabric is running.</div>

    const metrics = [
        {
            title: "Interest Rate",
            value: `${(worldState.interest_rate * 100).toFixed(2)}%`,
            icon: DollarSign,
            desc: "Global reference rate",
            color: "text-blue-500",
        },
        {
            title: "Inflation (CPI)",
            value: `${(worldState.inflation * 100).toFixed(2)}%`,
            icon: TrendingUp,
            desc: "YoY Change",
            color: worldState.inflation > 0.03 ? "text-red-500" : "text-green-500",
        },
        {
            title: "Geopolitical Risk",
            value: worldState.geopolitical_risk.toFixed(2),
            icon: Globe,
            desc: "Index (0-1)",
            color: worldState.geopolitical_risk > 0.6 ? "text-red-500" : "text-yellow-500",
        },
        {
            title: "Market Volatility",
            value: worldState.volatility_index.toFixed(2),
            icon: AlertTriangle,
            desc: "VIX Equivalent",
            color: "text-purple-500",
        },
    ]

    return (
        <div className="flex flex-col gap-6">
            <h2 className="text-3xl font-bold tracking-tight">Global Macro Dashboard</h2>

            {pending && (
                <Card className="border-dashed">
                    <CardContent className="pt-6 text-sm text-muted-foreground">
                        Snapshot is stale. A background refresh was queued and the view is showing the latest
                        internal data.
                    </CardContent>
                </Card>
            )}

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {metrics.map((m) => {
                    const Icon = m.icon
                    return (
                        <Card key={m.title}>
                            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                <CardTitle className="text-sm font-medium">{m.title}</CardTitle>
                                <Icon className={`h-4 w-4 ${m.color}`} />
                            </CardHeader>
                            <CardContent>
                                <div className="text-2xl font-bold">{m.value}</div>
                                <p className="text-xs text-muted-foreground">{m.desc}</p>
                            </CardContent>
                        </Card>
                    )
                })}
            </div>

            <Card className="col-span-4">
                <CardHeader>
                    <CardTitle>Liquidity & Commodity Index</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex gap-8">
                        <div>
                            <span className="block text-sm font-medium text-muted-foreground">Global Liquidity</span>
                            <span className="text-2xl font-bold">{worldState.liquidity_index.toFixed(2)}</span>
                        </div>
                        <div>
                            <span className="block text-sm font-medium text-muted-foreground">Commodity Index</span>
                            <span className="text-2xl font-bold">{worldState.commodity_index.toFixed(2)}</span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
