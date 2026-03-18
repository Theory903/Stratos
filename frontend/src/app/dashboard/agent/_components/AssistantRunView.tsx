"use client"
import { useState } from "react"
import { AlertTriangle, CheckCircle2, ChevronDown, XCircle } from "lucide-react"
import type { AgentResponse } from "@/lib/api"
import type { PlanStep, ToolRun, HitlInterrupt } from "./types"
import { cn } from "@/lib/utils"
import { MetricChip } from "./MetricChip"
import { StructuredList } from "./StructuredList"
import { FinanceCouncilView, RunOverviewPanel } from "./FinancePanels"
import { ApprovalGateView } from "./ApprovalGateView"
import {
  hasFinancePayload,
  isDisplayableMetadata,
  modeLabel,
  readableToolName,
  roleLabel,
  summarizeToolText,
} from "./utils"

// ─── ThoughtsAccordion ─────────────────────────────────────────────────────────

export function ThoughtsAccordion({
  status,
  toolRuns,
  plan,
  metadata,
  context,
}: {
  status?: string
  toolRuns?: ToolRun[]
  plan?: PlanStep[]
  metadata?: string[]
  context?: { intent: string; role: string; mode?: string; engine?: string }
}) {
  const [open, setOpen] = useState(false)

  const hasContent =
    status ||
    (toolRuns && toolRuns.length > 0) ||
    (plan && plan.length > 0) ||
    (metadata && metadata.filter(isDisplayableMetadata).length > 0) ||
    context
  if (!hasContent) return null

  const stepCount = (toolRuns?.length ?? 0) + (plan?.length ?? 0)

  return (
    <div className="mb-3 overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      {/* Accordion trigger */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-slate-100"
      >
        {status ? (
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sky-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-sky-500" />
          </span>
        ) : (
          <span className="h-2 w-2 shrink-0 rounded-full bg-slate-300" />
        )}
        <span className="flex-1 text-xs text-slate-600">
          {status ?? (stepCount > 0 ? `${stepCount} step${stepCount === 1 ? "" : "s"} completed` : "Thinking")}
        </span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 shrink-0 text-slate-400 transition-transform", open && "rotate-180")}
        />
      </button>

      {/* Accordion body */}
      {open && (
        <div className="border-t border-slate-200 p-3 space-y-3">
          {/* Context badges */}
          {context && (
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full border border-border/60 bg-white px-2.5 py-0.5 text-[11px] text-slate-700">
                <span className="text-muted-foreground">Intent · </span>
                <span className="font-medium">{context.intent}</span>
              </span>
              <span className="rounded-full border border-border/60 bg-white px-2.5 py-0.5 text-[11px] text-slate-700">
                <span className="text-muted-foreground">Role · </span>
                <span className="font-medium">{roleLabel(context.role)}</span>
              </span>
              {context.mode && (
                <span className="rounded-full border border-border/60 bg-white px-2.5 py-0.5 text-[11px] text-slate-700">
                  <span className="text-muted-foreground">Mode · </span>
                  <span className="font-medium">{modeLabel(context.mode)}</span>
                </span>
              )}
            </div>
          )}

          {/* Metadata pills */}
          {metadata && metadata.filter(isDisplayableMetadata).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {metadata.slice(-4).filter(isDisplayableMetadata).map((item) => (
                <span key={item} className="rounded-full border border-border/50 bg-white px-2 py-0.5 text-[11px] text-muted-foreground">
                  {item}
                </span>
              ))}
            </div>
          )}

          {/* Execution plan */}
          {plan && plan.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Plan</div>
              {plan.map((step, index) => (
                <div key={`${step.tool_name}-${index}`} className="rounded-lg border border-border/60 bg-white p-2.5 text-xs">
                  <div className="font-medium text-slate-800">{readableToolName(step.tool_name)}</div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(step.arguments).map(([key, value]) => (
                      <span key={key} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">
                        {key}: {String(value)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tool runs */}
          {toolRuns && toolRuns.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Tool Calls</div>
              {toolRuns.map((run, index) => (
                <div key={`${run.tool}-${index}`} className="flex gap-2 rounded-lg border border-border/50 bg-white p-2.5">
                  {run.status === "success" ? (
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                  ) : (
                    <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-500" />
                  )}
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-slate-800">{readableToolName(run.tool)}</div>
                    <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                      {summarizeToolText(run.status === "success" ? run.result_summary : run.error)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── AssistantRunView ──────────────────────────────────────────────────────────

export function AssistantRunView({
  content,
  context,
  memo,
  plan,
  toolRuns,
  metadata,
  status,
  hitlInterrupt,
  onResolveHitl,
}: {
  content: string
  context?: { intent: string; role: string; mode?: string; engine?: string }
  memo?: AgentResponse
  plan?: PlanStep[]
  toolRuns?: ToolRun[]
  metadata?: string[]
  status?: string
  hitlInterrupt?: HitlInterrupt
  onResolveHitl?: (decision: "approve" | "reject") => void
}) {
  const showThoughts =
    status || (toolRuns && toolRuns.length > 0) || (plan && plan.length > 0) || context || (metadata && metadata.length > 0)

  return (
    <div>
      {showThoughts && (
        <ThoughtsAccordion status={status} toolRuns={toolRuns} plan={plan} metadata={metadata} context={context} />
      )}

      {/* HITL approval gate — shown above the memo/content while unresolved */}
      {hitlInterrupt && !hitlInterrupt.resolved && onResolveHitl && (
        <div className="mb-3">
          <ApprovalGateView interrupt={hitlInterrupt} onResolved={onResolveHitl} />
        </div>
      )}
      {hitlInterrupt?.resolved && (
        <div className="mb-3 flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-muted-foreground">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
          <span>Approval gate resolved — run resumed.</span>
        </div>
      )}

      {memo ? (
        <div className="space-y-3">
          {/* Minimal header - just show the answer */}
          {memo.summary && (
            <div className="text-sm leading-6 text-slate-800 whitespace-pre-wrap">{memo.summary}</div>
          )}
          
          {/* Only show decision badge if it's a trade decision */}
          {memo.decision && !["info", "hold"].includes(memo.decision.toLowerCase()) && (
            <div className="flex items-center gap-2">
              <span className={cn(
                "rounded-full px-2.5 py-1 text-xs font-medium",
                memo.decision.toLowerCase() === "buy" && "bg-emerald-100 text-emerald-700",
                memo.decision.toLowerCase() === "sell" && "bg-red-100 text-red-700",
                !["buy", "sell"].includes(memo.decision.toLowerCase()) && "bg-slate-100 text-slate-700"
              )}>
                {memo.decision.toUpperCase()}
              </span>
              {memo.confidence_score > 0 && (
                <span className="text-xs text-muted-foreground">
                  {(memo.confidence_score * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
          )}

          {/* Skip the heavy panels for simple responses - just show content if different */}
          {memo.recommendation && memo.recommendation !== memo.summary && (
            <div className="text-sm leading-6 text-slate-700 whitespace-pre-wrap">{memo.recommendation}</div>
          )}
        </div>
      ) : content ? (
        <div className="text-sm leading-7 text-slate-800 whitespace-pre-wrap">{content}</div>
      ) : null}
    </div>
  )
}
