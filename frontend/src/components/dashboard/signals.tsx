"use client"

import { cn } from "@/lib/utils"

type Freshness = "fresh" | "stale" | "pending"

export function FreshnessDot({ freshness }: { freshness: Freshness }) {
  return (
    <span
      className={cn(
        "relative inline-flex h-2 w-2 rounded-full",
        freshness === "fresh" && "bg-emerald-500",
        freshness === "stale" && "bg-amber-500",
        freshness === "pending" && "bg-slate-300"
      )}
      title={freshness === "fresh" ? "Fresh" : freshness === "stale" ? "Stale" : "Pending"}
    >
      {freshness === "fresh" && (
        <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75 animate-ping" />
      )}
    </span>
  )
}

type ConfidenceLevel = "high" | "medium" | "low" | "unknown"

interface ConfidenceBadgeProps {
  score: number
  showLabel?: boolean
  size?: "sm" | "md"
}

export function ConfidenceBadge({ score, showLabel = true, size = "sm" }: ConfidenceBadgeProps) {
  const level: ConfidenceLevel = score >= 0.8 ? "high" : score >= 0.5 ? "medium" : score > 0 ? "low" : "unknown"

  const colors = {
    high: "bg-emerald-100 text-emerald-700 border-emerald-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-red-100 text-red-700 border-red-200",
    unknown: "bg-slate-100 text-slate-500 border-slate-200",
  }

  const labels = {
    high: "High",
    medium: "Medium",
    low: "Low",
    unknown: "Unknown",
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        colors[level],
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-xs"
      )}
      title={`Confidence: ${(score * 100).toFixed(0)}%`}
    >
      {showLabel && labels[level]}
      {!showLabel && <span>{(score * 100).toFixed(0)}%</span>}
    </span>
  )
}

type UrgencyLevel = "high" | "medium" | "low"

interface UrgencyTagProps {
  urgency: number
  showLabel?: boolean
  size?: "sm" | "md"
}

export function UrgencyTag({ urgency, showLabel = true, size = "sm" }: UrgencyTagProps) {
  const level: UrgencyLevel = urgency >= 0.8 ? "high" : urgency >= 0.5 ? "medium" : "low"

  const colors = {
    high: "bg-red-100 text-red-700 border-red-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-blue-100 text-blue-700 border-blue-200",
  }

  const labels = {
    high: "Urgent",
    medium: "Soon",
    low: "Low",
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border font-medium",
        colors[level],
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-xs"
      )}
      title={`Urgency: ${(urgency * 100).toFixed(0)}%`}
    >
      {showLabel && labels[level]}
      {!showLabel && <span>{(urgency * 100).toFixed(0)}%</span>}
    </span>
  )
}

type SignalType = "risk" | "opportunity" | "approval" | "attention" | "info"

interface ActionCardProps {
  title: string
  detail?: string
  type: SignalType
  href?: string
  onClick?: () => void
  confidence?: number
  freshness?: Freshness
  urgency?: number
}

export function ActionCard({ title, detail, type, href, onClick, confidence, freshness, urgency }: ActionCardProps) {
  const borderColors: Record<SignalType, string> = {
    risk: "border-l-4 border-l-red-500",
    opportunity: "border-l-4 border-l-emerald-500",
    approval: "border-l-4 border-l-amber-500",
    attention: "border-l-4 border-l-blue-500",
    info: "border-l-4 border-l-slate-300",
  }

  const icons: Record<SignalType, React.ReactNode> = {
    risk: (
      <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    opportunity: (
      <svg className="h-4 w-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    approval: (
      <svg className="h-4 w-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    attention: (
      <svg className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
      </svg>
    ),
    info: (
      <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  }

  const content = (
    <div className={cn("rounded-lg border bg-white p-4 transition-colors hover:bg-black/[0.02]", borderColors[type])}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{icons[type]}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium truncate">{title}</h3>
            {freshness && <FreshnessDot freshness={freshness} />}
          </div>
          {detail && <p className="mt-1 text-xs text-black/50 line-clamp-2">{detail}</p>}
          <div className="mt-2 flex items-center gap-2">
            {confidence !== undefined && <ConfidenceBadge score={confidence} showLabel={false} size="sm" />}
            {urgency !== undefined && <UrgencyTag urgency={urgency} showLabel={false} size="sm" />}
          </div>
        </div>
      </div>
    </div>
  )

  if (href) {
    return (
      <a href={href} className="block">
        {content}
      </a>
    )
  }

  if (onClick) {
    return (
      <button onClick={onClick} className="w-full text-left">
        {content}
      </button>
    )
  }

  return content
}

interface SignalStripProps {
  signals: Array<{
    id: string
    label: string
    value: string
    change?: number
    freshness?: Freshness
  }>
}

export function SignalStrip({ signals }: SignalStripProps) {
  return (
    <div className="quiet-scroll flex gap-4 overflow-x-auto pb-2">
      {signals.map((signal) => (
        <div
          key={signal.id}
          className="flex items-center gap-2 rounded-full border bg-white px-3 py-1.5 text-xs whitespace-nowrap"
        >
          {signal.freshness && <FreshnessDot freshness={signal.freshness} />}
          <span className="font-medium">{signal.label}</span>
          <span className="text-black/50">{signal.value}</span>
          {signal.change !== undefined && (
            <span className={cn(
              signal.change >= 0 ? "text-emerald-600" : "text-red-600"
            )}>
              {signal.change >= 0 ? "+" : ""}{signal.change.toFixed(2)}%
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

interface AttentionItem {
  id: string
  title: string
  detail?: string
  type: SignalType
  confidence?: number
  freshness?: Freshness
  urgency?: number
  href?: string
  onClick?: () => void
}

interface AttentionQueueProps {
  items: AttentionItem[]
  maxItems?: number
}

export function AttentionQueue({ items, maxItems = 10 }: AttentionQueueProps) {
  const sorted = [...items].sort((a, b) => {
    const aScore = (a.urgency ?? 0.5) * 0.6 + (a.confidence ?? 0.5) * 0.4
    const bScore = (b.urgency ?? 0.5) * 0.6 + (b.confidence ?? 0.5) * 0.4
    return bScore - aScore
  })

  const display = sorted.slice(0, maxItems)

  return (
    <div className="space-y-2">
      {display.map((item) => (
        <ActionCard
          key={item.id}
          title={item.title}
          detail={item.detail}
          type={item.type}
          confidence={item.confidence}
          freshness={item.freshness}
          urgency={item.urgency}
          href={item.href}
          onClick={item.onClick}
        />
      ))}
      {items.length > maxItems && (
        <div className="text-center text-xs text-black/40 py-2">
          +{items.length - maxItems} more items
        </div>
      )}
    </div>
  )
}
