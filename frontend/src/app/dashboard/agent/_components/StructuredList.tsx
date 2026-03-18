import { cn } from "@/lib/utils"

export function StructuredList({
  title,
  items,
  tone = "default",
}: {
  title: string
  items: string[]
  tone?: "default" | "muted"
}) {
  return (
    <div className="rounded-xl border bg-background/70 p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">{title}</div>
      <div className="space-y-2 text-sm">
        {items.map((item) => (
          <div
            key={item}
            className={cn(
              "rounded-lg border px-3 py-2.5 leading-6",
              tone === "muted"
                ? "border-border/50 bg-slate-50/70 text-slate-600"
                : "border-border/60 bg-white/80 text-slate-800"
            )}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  )
}
