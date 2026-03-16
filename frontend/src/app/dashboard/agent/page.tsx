"use client"
import { startTransition, useEffect, useRef, useState } from "react"
import { AlertTriangle, Bot, CheckCircle2, Loader2, Send, Sparkles, User, XCircle } from "lucide-react"

import { AgentResponse, api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface PlanStep {
  tool_name: string
  arguments: Record<string, unknown>
}

interface ToolRun {
  tool: string
  status: "success" | "failed"
  result_summary?: string
  error?: string
}

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  context?: { intent: string; role: string }
  memo?: AgentResponse
  plan?: PlanStep[]
  status?: string
  toolRuns?: ToolRun[]
}

const guidedPrompts = [
  {
    label: "Portfolio shock",
    prompt: "What do sticky inflation, oil pressure, and BTC risk sentiment mean for my portfolio?",
    hint: "Mention the book, the shock, and the decision you need to make.",
  },
  {
    label: "Country risk",
    prompt: "How should I frame India sovereign risk versus US macro pressure this week?",
    hint: "Good for macro or policy framing before sizing new exposure.",
  },
  {
    label: "Single-name check",
    prompt: "What should I watch in AAPL quality, event pulse, and regime history before adding risk?",
    hint: "Best when you want one clean memo instead of three separate dashboards.",
  },
] as const

function isSubstantiveFinancePrompt(query: string): boolean {
  const normalized = query.trim().toLowerCase()
  if (!normalized) {
    return false
  }

  const financeKeywords = [
    "aapl",
    "btc",
    "india",
    "risk",
    "macro",
    "portfolio",
    "regime",
    "scenario",
    "fed",
    "oil",
    "inflation",
  ]

  return (
    query.trim().split(/\s+/).length >= 3 ||
    financeKeywords.some((keyword) => normalized.includes(keyword)) ||
    /^[A-Z:]{2,10}\??$/.test(query.trim())
  )
}

export default function AgentPage() {
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [hintIndex, setHintIndex] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const threadIdRef = useRef<string>(crypto.randomUUID())

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    const textarea = composerRef.current
    if (!textarea) {
      return
    }

    textarea.style.height = "0px"
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }, [query])

  useEffect(() => {
    if (query.trim()) {
      return
    }

    const intervalId = window.setInterval(() => {
      startTransition(() => {
        setHintIndex((current) => (current + 1) % guidedPrompts.length)
      })
    }, 4500)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [query])

  const activeGuide = guidedPrompts[hintIndex]

  const handleComposerKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      const form = event.currentTarget.form
      form?.requestSubmit()
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) return

    if (!isSubstantiveFinancePrompt(trimmedQuery)) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: trimmedQuery,
        },
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "Ask a portfolio, macro, event, or research question with enough context to ground the workflow. Example: What do sticky inflation, oil pressure, and BTC risk sentiment mean for my portfolio?",
        },
      ])
      setQuery("")
      return
    }

    const assistantId = crypto.randomUUID()
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuery,
    }
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      status: "Planning execution strategy...",
      toolRuns: [],
    }

    setMessages((current) => [...current, userMessage, assistantMessage])
    setQuery("")
    setLoading(true)

    try {
      await api.streamOrchestrateV3(
        userMessage.content,
        (type, data) => {
        startTransition(() => {
          setMessages((current) =>
            current.map((message) => {
              if (message.id !== assistantId) {
                return message
              }

              if (type === "status") {
                return { ...message, status: data }
              }
              if (type === "plan") {
                return { ...message, plan: data as PlanStep[] }
              }
              if (type === "context") {
                return { ...message, context: data as { intent: string; role: string } }
              }
              if (type === "token") {
                return {
                  ...message,
                  status: "Synthesizing memo...",
                  content: `${message.content}${data as string}`,
                }
              }
              if (type === "task_result") {
                return {
                  ...message,
                  toolRuns: [...(message.toolRuns ?? []), data as ToolRun],
                }
              }
              if (type === "final_memo") {
                return {
                  ...message,
                  memo: data as AgentResponse,
                  status: undefined,
                }
              }
              return message
            })
          )
        })
        },
        { threadId: threadIdRef.current }
      )
    } catch (error) {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                status: undefined,
                content: "The V2 orchestrator failed before the strategic memo completed.",
              }
            : message
        )
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100svh-8rem)] flex-col">
      <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <CardHeader className="border-b border-border/60 bg-white/60">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-border/70 bg-white/90 text-slate-950">
              <Bot className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-base">STRATOS Agent</CardTitle>
              <p className="text-sm text-muted-foreground">Ask, run, memo.</p>
            </div>
          </div>
        </CardHeader>

        <div className="quiet-scroll content-auto flex-1 space-y-4 overflow-y-auto p-4 md:p-6" ref={scrollRef}>
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center">
                <div className="flex max-w-2xl flex-col items-center text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-3xl border border-border/70 bg-white/90 text-slate-950">
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <h2 className="mt-5 text-2xl font-semibold tracking-[-0.04em] text-slate-950 md:text-3xl">
                    What do you need to decide?
                  </h2>
                  <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
                    Ask with portfolio, macro, event, or single-name context.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {guidedPrompts.map((prompt, index) => (
                      <button
                        key={prompt.label}
                        type="button"
                        className={cn(
                          "rounded-full border px-3 py-2 text-sm transition-colors",
                          index === hintIndex
                            ? "border-cyan-300/60 bg-cyan-50 text-cyan-900"
                            : "border-border/70 bg-white/80 text-slate-700 hover:border-primary/20 hover:text-slate-950"
                        )}
                        onClick={() => {
                          setHintIndex(index)
                          setQuery(prompt.prompt)
                        }}
                      >
                        {prompt.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={cn("flex gap-3", message.role === "user" ? "flex-row-reverse" : "flex-row")}
              >
                <div
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border",
                    message.role === "user"
                      ? "border-primary/20 bg-primary text-primary-foreground"
                      : "border-border/70 bg-white/70 text-slate-900"
                  )}
                >
                  {message.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div
                  className={cn(
                    "max-w-[88%] rounded-[1.4rem] px-4 py-3",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "border border-border/70 bg-white/80 text-foreground"
                  )}
                >
                  {message.status && (
                    <div className="mb-2 flex items-center gap-2 text-xs italic text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {message.status}
                    </div>
                  )}

                  {message.role === "assistant" && (
                    <AssistantRunView
                      content={message.content}
                      context={message.context}
                      memo={message.memo}
                      plan={message.plan}
                      toolRuns={message.toolRuns}
                    />
                  )}

                  {message.role === "user" && <div className="whitespace-pre-wrap">{message.content}</div>}
                </div>
              </div>
            ))}

            {loading && messages[messages.length - 1]?.role === "user" && (
              <div className="flex gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-border/70 bg-white/70">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
                <div className="rounded-[1.2rem] border border-border/70 bg-white/80 px-4 py-2 text-sm text-muted-foreground">
                  Connecting to V2 orchestrator...
                </div>
              </div>
            )}
        </div>

        <CardFooter className="border-t border-border/60 bg-white/52 p-3 md:p-4">
          <form onSubmit={handleSubmit} className="w-full">
            <div className="rounded-[1.7rem] border border-border/70 bg-white/90 p-2.5 shadow-[0_18px_36px_-28px_rgba(15,23,42,0.45)]">
              <div className="flex items-center justify-between gap-3 px-1 pb-2">
                <div className="quiet-scroll flex gap-2 overflow-x-auto">
                  {guidedPrompts.map((prompt, index) => (
                    <button
                      key={prompt.label}
                      type="button"
                      className={cn(
                        "rounded-full border px-2.5 py-1.5 text-xs transition-colors",
                        index === hintIndex
                          ? "border-cyan-300/60 bg-cyan-50 text-cyan-900"
                          : "border-border/70 bg-white text-muted-foreground hover:border-primary/20 hover:text-slate-950"
                      )}
                      onClick={() => {
                        setHintIndex(index)
                        setQuery(prompt.prompt)
                      }}
                    >
                      {prompt.label}
                    </button>
                  ))}
                </div>
                <div className="hidden shrink-0 text-[11px] text-muted-foreground md:block">
                  Enter to send
                </div>
              </div>

              <div className="flex items-end gap-2 rounded-[1.35rem] border border-border/60 bg-slate-50/80 px-2 py-2">
                <textarea
                  ref={composerRef}
                  placeholder={`Try: ${activeGuide.prompt}`}
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleComposerKeyDown}
                  disabled={loading}
                  rows={1}
                  aria-label="Ask STRATOS Agent"
                  className="max-h-40 min-h-[3rem] flex-1 resize-none rounded-[1.1rem] border-0 bg-transparent px-3 py-2.5 text-sm leading-6 text-slate-950 outline-none placeholder:text-muted-foreground"
                />
                <Button
                  type="submit"
                  disabled={loading || !query.trim()}
                  className="h-10 w-10 shrink-0 rounded-2xl px-0 shadow-none"
                >
                  <Send className="h-4 w-4" />
                  <span className="sr-only">Send</span>
                </Button>
              </div>
            </div>
          </form>
        </CardFooter>
      </Card>
    </div>
  )
}

function AssistantRunView({
  content,
  context,
  memo,
  plan,
  toolRuns,
}: {
  content: string
  context?: { intent: string; role: string }
  memo?: AgentResponse
  plan?: PlanStep[]
  toolRuns?: ToolRun[]
}) {
  return (
    <div className="space-y-3">
      {context && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full border bg-background px-2 py-1 text-foreground">
            Intent {context.intent}
          </span>
          <span className="rounded-full border bg-background px-2 py-1 text-foreground">
            Role {context.role}
          </span>
        </div>
      )}
      {memo ? (
        <div className="space-y-3">
          <div className="rounded-2xl border border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.96),rgba(255,255,255,0.9))] p-4 shadow-[0_20px_40px_-32px_rgba(15,23,42,0.45)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">
              Decision
            </div>
            <div className="mt-2 text-lg font-semibold tracking-[-0.03em] text-slate-950">
              {memo.decision || memo.recommendation}
            </div>
            {memo.summary && <p className="mt-2 text-sm leading-6 text-slate-600">{memo.summary}</p>}
            <div className="mt-4 grid gap-3 md:grid-cols-[1.6fr_0.9fr]">
              <div className="rounded-xl border border-slate-200 bg-white/90 p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Answer
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{memo.recommendation}</p>
              </div>
              <div className="grid gap-3">
                <MetricChip
                  label="Confidence"
                  value={`${(memo.confidence_score * 100).toFixed(0)}%`}
                  tone={memo.confidence_score >= 0.75 ? "positive" : memo.confidence_score >= 0.45 ? "neutral" : "caution"}
                  detail={memo.confidence_calibration ? `${memo.confidence_calibration} calibration` : undefined}
                />
                <MetricChip
                  label="Risk"
                  value={memo.risk_band}
                  tone={memo.risk_band === "Low" ? "positive" : memo.risk_band === "Medium" ? "neutral" : "caution"}
                />
              </div>
            </div>
          </div>
          {memo.key_findings && memo.key_findings.length > 0 && (
            <StructuredList title="What Matters" items={memo.key_findings} />
          )}
          {memo.historical_context && memo.historical_context.length > 0 && (
            <StructuredList title="Context" items={memo.historical_context} />
          )}
          {memo.portfolio_impact && memo.portfolio_impact.length > 0 && (
            <StructuredList title="Portfolio Impact" items={memo.portfolio_impact} />
          )}
          {memo.recommended_actions && memo.recommended_actions.length > 0 && (
            <StructuredList title="Do Next" items={memo.recommended_actions} />
          )}
          {memo.watch_items && memo.watch_items.length > 0 && (
            <StructuredList title="Watch Next" items={memo.watch_items} />
          )}
          {memo.data_quality && memo.data_quality.length > 0 && (
            <StructuredList title="Data Quality" items={memo.data_quality} tone="muted" />
          )}
          {memo.evidence_blocks && memo.evidence_blocks.length > 0 && (
            <div className="rounded-xl border bg-background/70 p-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Evidence
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {memo.evidence_blocks.map((block, index) => (
                  <div key={`${block.title}-${index}`} className="rounded-lg border border-border/60 bg-white/80 p-3">
                    <div className="text-sm font-medium text-slate-900">{block.title}</div>
                    <div className="mt-1 text-xs leading-5 text-muted-foreground">{block.detail}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {memo.scenario_tree && memo.scenario_tree.length > 0 && (
            <div className="rounded-xl border bg-background/70 p-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Scenarios
              </div>
              <div className="space-y-2 text-sm">
                {memo.scenario_tree.slice(0, 3).map((scenario: any, index: number) => (
                  <div key={index} className="rounded-lg border border-border/60 bg-white/80 p-3">
                    <div className="font-medium text-slate-900">{scenario.scenario || scenario.event || `Scenario ${index + 1}`}</div>
                    <div className="mt-1 text-xs leading-5 text-muted-foreground">
                      {scenario.impact || scenario.description || "No impact description."}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {memo.worst_case && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{memo.worst_case}</span>
            </div>
          )}
          {plan && plan.length > 0 && (
            <details className="rounded-xl border bg-background/70 p-3">
              <summary className="cursor-pointer list-none text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Execution Plan
              </summary>
              <div className="mt-3 space-y-2 text-sm">
                {plan.map((step, index) => (
                  <div key={`${step.tool_name}-${index}`} className="rounded-lg border border-border/60 bg-white/80 p-3">
                    <div className="font-medium text-slate-900">{readableToolName(step.tool_name)}</div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {Object.entries(step.arguments).map(([key, value]) => (
                        <span key={key} className="rounded-full border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground">
                          {key}: {String(value)}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
          {toolRuns && toolRuns.length > 0 && (
            <details className="rounded-xl border bg-background/70 p-3">
              <summary className="cursor-pointer list-none text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Tool Execution
              </summary>
              <div className="mt-3 space-y-2 text-sm">
                {toolRuns.map((run, index) => (
                  <div key={`${run.tool}-${index}`} className="flex gap-3 rounded-lg border border-border/60 bg-white/80 p-3">
                    {run.status === "success" ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
                    ) : (
                      <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                    )}
                    <div className="min-w-0">
                      <div className="font-medium text-slate-900">{readableToolName(run.tool)}</div>
                      <div className="mt-1 whitespace-pre-wrap break-words text-xs leading-5 text-muted-foreground">
                        {summarizeToolText(run.status === "success" ? run.result_summary : run.error)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      ) : (
        <div className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{content}</div>
      )}
    </div>
  )
}

function StructuredList({
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
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
        {title}
      </div>
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

function MetricChip({
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

function readableToolName(toolName: string) {
  return toolName
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

function summarizeToolText(value?: string) {
  if (!value) {
    return "No additional output."
  }

  return value.length > 280 ? `${value.slice(0, 277)}...` : value
}
