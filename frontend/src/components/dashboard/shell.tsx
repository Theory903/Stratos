import Link from "next/link"

import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function StatusPill({
  children,
  tone = "default",
}: {
  children: React.ReactNode
  tone?: "default" | "muted" | "accent"
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1.5 text-[10px] font-medium uppercase tracking-[0.18em]",
        tone === "accent" && "border-cyan-200 bg-cyan-50 text-cyan-900",
        tone === "muted" && "border-border/80 bg-white/60 text-muted-foreground",
        tone === "default" && "border-slate-300/70 bg-slate-900 text-slate-50"
      )}
    >
      {children}
    </span>
  )
}

export function PageHero({
  eyebrow,
  title,
  description,
  badges = [],
  actions,
  compact = false,
}: {
  eyebrow?: string
  title?: string
  description?: string
  badges?: Array<{ label: string; tone?: "default" | "muted" | "accent" }>
  actions?: React.ReactNode
  compact?: boolean
}) {
  const hasHeading = Boolean(eyebrow || title)

  return (
    <section
      className={cn(
        "surface-glow grid gap-4 border border-border/70 bg-white/62 backdrop-blur-sm xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center",
        compact ? "rounded-[1.5rem] p-3.5 xl:p-4" : "rounded-[1.8rem] p-4 xl:p-5"
      )}
    >
      <div
        className={cn(
          compact ? "space-y-1.5" : "space-y-2",
          compact && !hasHeading && "flex flex-wrap items-center gap-2.5 space-y-0"
        )}
      >
        {eyebrow && (
          <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            {eyebrow}
          </div>
        )}
        {hasHeading ? (
          <div className={cn(compact ? "space-y-1" : "space-y-1.5")}>
            {title && (
              <h1
                className={cn(
                  "max-w-4xl font-semibold tracking-[-0.05em] text-slate-950",
                  compact ? "text-xl md:text-[1.7rem]" : "text-[2rem] md:text-[2.15rem]"
                )}
              >
                {title}
              </h1>
            )}
            {description && (
              <p className="max-w-2xl text-sm leading-5 text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        ) : (
          description && (
            <p className="max-w-2xl text-sm leading-5 text-slate-700">{description}</p>
          )
        )}
        {badges.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {badges.map((badge) => (
              <StatusPill key={badge.label} tone={badge.tone}>
                {badge.label}
              </StatusPill>
            ))}
          </div>
        )}
      </div>
      {actions && <div className="flex items-start xl:justify-end">{actions}</div>}
    </section>
  )
}

export function FocusStrip({
  title,
  items,
}: {
  title: string
  items: Array<{ label: string; detail?: string }>
}) {
  return (
    <section className="rounded-[1.35rem] border border-border/70 bg-white/48 p-2.5 backdrop-blur-sm">
      <div className="mb-2 flex items-center justify-between gap-3 px-1">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-900">{title}</h2>
        <span className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          Live
        </span>
      </div>
      <div className="quiet-scroll flex gap-2 overflow-x-auto pb-0.5">
        {items.map((item, index) => (
          <div
            key={item.label}
            className="min-w-[180px] rounded-[1rem] border border-border/70 bg-background/84 p-2.5"
          >
            <div className="flex items-center gap-3">
              <span className="flex h-5 w-5 items-center justify-center rounded-full border border-border/70 bg-white text-[9px] font-semibold text-slate-700">
                {index + 1}
              </span>
              <div className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-950">{item.label}</div>
            </div>
            {item.detail && (
              <div className="mt-1 pl-8 text-[11px] leading-4 text-muted-foreground">{item.detail}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

export function SegmentedControl<T extends string>({
  value,
  onChange,
  items,
}: {
  value: T
  onChange: (value: T) => void
  items: Array<{ label: string; value: T }>
}) {
  return (
    <div className="quiet-scroll flex gap-2 overflow-x-auto rounded-full border border-border/70 bg-background/80 p-1">
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onChange(item.value)}
          className={cn(
            "rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-200 motion-reduce:transition-none",
            value === item.value
              ? "bg-slate-950 text-white"
              : "text-muted-foreground hover:bg-white hover:text-slate-950"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}

export function ActionCluster({
  items,
}: {
  items: Array<{
    href?: string
    label: string
    onClick?: () => void
    tone?: "default" | "outline"
    disabled?: boolean
  }>
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) =>
        item.href ? (
          <Link
            key={`${item.label}-${item.href}`}
            href={item.href}
            className={cn(
              buttonVariants({
                variant: item.tone === "outline" ? "outline" : "default",
                size: "sm",
              })
            )}
          >
            {item.label}
          </Link>
        ) : (
          <button
            key={item.label}
            type="button"
            className={cn(
              buttonVariants({
                variant: item.tone === "outline" ? "outline" : "default",
                size: "sm",
              })
            )}
            onClick={item.onClick}
            disabled={item.disabled}
          >
            {item.label}
          </button>
        )
      )}
    </div>
  )
}
