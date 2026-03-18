import { cn } from "@/lib/utils"

export function MetricChip({
  label,
  value,
  tone,
  detail,
}: {
  label: string
  value: string
  tone: "positive" | "neutral" | "caution"
  detail?: string
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-3",
        tone === "positive" && "border-emerald-200 bg-emerald-50 text-emerald-900",
        tone === "neutral" && "border-slate-200 bg-slate-50 text-slate-900",
        tone === "caution" && "border-amber-200 bg-amber-50 text-amber-900"
      )}
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.2em] opacity-70">{label}</div>
      <div className="mt-1 text-base font-semibold">{value}</div>
      {detail && <div className="mt-1 text-[11px] opacity-70">{detail}</div>}
    </div>
  )
}
