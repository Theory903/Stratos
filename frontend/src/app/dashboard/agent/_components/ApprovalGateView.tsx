/**
 * ApprovalGateView
 *
 * Rendered inside an assistant message whenever the orchestrator pauses at an
 * HITL approval gate (SSE event type = "hitl_interrupt").
 *
 * The component shows each pending approval request and two CTA buttons:
 *   • Approve  → POST /orchestrate/v4/resume { decision: "approve" }
 *   • Reject   → POST /orchestrate/v4/resume { decision: "reject" }
 *
 * After the user acts the component becomes "resolved" (read-only receipt).
 */
"use client"

import { useState } from "react"
import { CheckCircle2, ShieldAlert, XCircle } from "lucide-react"
import { api } from "@/lib/api"
import type { HitlInterrupt } from "./types"
import { cn } from "@/lib/utils"

// ─── Props ─────────────────────────────────────────────────────────────────────

export interface ApprovalGateViewProps {
  interrupt: HitlInterrupt
  /** Called by the parent (page.tsx) after the API call succeeds */
  onResolved: (decision: "approve" | "reject") => void
}

// ─── Component ─────────────────────────────────────────────────────────────────

export function ApprovalGateView({ interrupt, onResolved }: ApprovalGateViewProps) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { run_id, thread_id, approvals, resolved } = interrupt

  async function act(decision: "approve" | "reject") {
    setBusy(decision)
    setError(null)
    try {
      await api.resumeRun(run_id, thread_id, decision)
      onResolved(decision)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit decision.")
      setBusy(null)
    }
  }

  // ── Resolved receipt ────────────────────────────────────────────────────────
  if (resolved) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-muted-foreground">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
        <span>Approval gate resolved — run resumed.</span>
      </div>
    )
  }

  // ── Pending gate ────────────────────────────────────────────────────────────
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-3.5 shadow-sm">

      {/* Header */}
      <div className="mb-2.5 flex items-center gap-2">
        <ShieldAlert className="h-4 w-4 shrink-0 text-amber-600" />
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-800">
          Approval Required
        </span>
      </div>

      {/* Approval items */}
      <div className="mb-3 space-y-2">
        {approvals.map((req) => (
          <div
            key={req.approval_id}
            className="rounded-lg border border-amber-200/80 bg-white/70 p-2.5"
          >
            <div className="flex items-start gap-2">
              <span
                className={cn(
                  "mt-px h-1.5 w-1.5 shrink-0 rounded-full",
                  req.required ? "bg-red-500" : "bg-amber-400"
                )}
              />
              <p className="text-xs leading-5 text-slate-800">{req.reason}</p>
            </div>
            {req.required && (
              <span className="ml-3.5 text-[10px] uppercase tracking-wider text-red-600">
                Required
              </span>
            )}
          </div>
        ))}
      </div>

      {/* CTA buttons */}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => act("approve")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded-lg border py-2 text-xs font-semibold transition-colors",
            busy !== null
              ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              : "border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-emerald-100 active:bg-emerald-200"
          )}
        >
          <CheckCircle2 className={cn("h-3.5 w-3.5", busy === "approve" && "animate-spin")} />
          {busy === "approve" ? "Approving…" : "Approve"}
        </button>

        <button
          type="button"
          disabled={busy !== null}
          onClick={() => act("reject")}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 rounded-lg border py-2 text-xs font-semibold transition-colors",
            busy !== null
              ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
              : "border-red-200 bg-red-50 text-red-800 hover:bg-red-100 active:bg-red-200"
          )}
        >
          <XCircle className={cn("h-3.5 w-3.5", busy === "reject" && "animate-spin")} />
          {busy === "reject" ? "Rejecting…" : "Reject"}
        </button>
      </div>

      {/* Inline error */}
      {error && (
        <p className="mt-2 text-[11px] text-red-700">{error}</p>
      )}
    </div>
  )
}
