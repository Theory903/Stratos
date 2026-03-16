"use client"

import { PulseItem } from "@/lib/app-state"
import { cn } from "@/lib/utils"

export function MarketPulseStrip({
  items,
  variant = "dark",
  compact = false,
}: {
  items: PulseItem[]
  variant?: "dark" | "light"
  compact?: boolean
}) {
  const duplicated = [...items, ...items]

  return (
    <div
      className={cn(
        "overflow-hidden border-b",
        variant === "dark"
          ? "border-slate-800/80 bg-[#08101a]"
          : "rounded-[1.1rem] border-border/70 bg-white/60"
      )}
    >
      <div className="ticker-track flex w-max items-center hover:[animation-play-state:paused]">
        {duplicated.map((item, index) => (
          <div
            key={`${item.label}-${index}`}
            className={cn(
              "flex shrink-0 items-center gap-2 border-r",
              compact ? "px-4 py-2" : "px-6 py-2.5",
              variant === "dark" ? "border-slate-800/80" : "border-border/60"
            )}
          >
            <span
              className={cn(
                "font-mono-ui text-[10px] font-semibold uppercase tracking-[0.22em]",
                variant === "dark" ? "text-slate-500" : "text-muted-foreground"
              )}
            >
              {item.label}
            </span>
            <span
              className={cn(
                "font-mono-ui text-xs",
                variant === "dark" ? "text-slate-200" : "text-slate-900"
              )}
            >
              {item.value}
            </span>
            <span
              className={cn(
                "rounded px-1.5 py-0.5 font-mono-ui text-[10px]",
                item.change >= 0 ? "bg-emerald-400/10 text-emerald-500" : "bg-red-400/10 text-red-500"
              )}
            >
              {item.change >= 0 ? "▴" : "▾"} {Math.abs(item.change).toFixed(2)}%
            </span>
            {item.freshness === "stale" && (
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  variant === "dark" ? "bg-amber-400/70" : "bg-amber-500"
                )}
                title="Using last cached value"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

