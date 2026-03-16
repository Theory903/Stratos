"use client"

import { startTransition, useEffect, useRef, useState } from "react"
import { AlertTriangle, Bot, CheckCircle2, Loader2, Send, User, XCircle } from "lucide-react"

import { AgentResponse, api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
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
  memo?: AgentResponse
  plan?: PlanStep[]
  status?: string
  toolRuns?: ToolRun[]
}

export default function AgentPage() {
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!query.trim()) return

    const assistantId = crypto.randomUUID()
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: query.trim(),
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
      await api.streamOrchestrateV2(userMessage.content, (type, data) => {
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
      })
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
    <div className="flex h-[calc(100vh-8rem)] flex-col gap-4">
      <Card className="flex flex-1 flex-col overflow-hidden">
        <CardHeader className="border-b bg-muted/20">
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            STRATOS Strategy Agent
          </CardTitle>
        </CardHeader>

        <div className="flex-1 space-y-4 overflow-y-auto p-4" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Try asking: &quot;How should I position if inflation stays sticky and India growth holds?&quot;
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={cn("flex gap-3", message.role === "user" ? "flex-row-reverse" : "flex-row")}
            >
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                )}
              >
                {message.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>

              <div
                className={cn(
                  "max-w-[85%] rounded-lg px-4 py-3",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
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
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
              <div className="rounded-lg bg-muted px-4 py-2 text-sm text-muted-foreground">
                Connecting to V2 orchestrator...
              </div>
            </div>
          )}
        </div>

        <CardFooter className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex w-full gap-2">
            <Input
              placeholder="Ask for a strategic memo grounded in internal snapshots..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              disabled={loading}
              className="flex-1"
            />
            <Button type="submit" disabled={loading || !query.trim()}>
              <Send className="h-4 w-4" />
              <span className="sr-only">Send</span>
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  )
}

function AssistantRunView({
  content,
  memo,
  plan,
  toolRuns,
}: {
  content: string
  memo?: AgentResponse
  plan?: PlanStep[]
  toolRuns?: ToolRun[]
}) {
  return (
    <div className="space-y-3">
      {plan && plan.length > 0 && (
        <div className="rounded-lg border bg-background/70 p-3">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Execution plan
          </div>
          <div className="space-y-2 text-sm">
            {plan.map((step, index) => (
              <div key={`${step.tool_name}-${index}`} className="rounded-md border border-border/60 p-2">
                <div className="font-medium">{step.tool_name}</div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {Object.entries(step.arguments)
                    .map(([key, value]) => `${key}: ${String(value)}`)
                    .join(" · ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {toolRuns && toolRuns.length > 0 && (
        <div className="rounded-lg border bg-background/70 p-3">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Tool execution
          </div>
          <div className="space-y-2 text-sm">
            {toolRuns.map((run, index) => (
              <div key={`${run.tool}-${index}`} className="flex gap-3 rounded-md border border-border/60 p-2">
                {run.status === "success" ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
                ) : (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                )}
                <div>
                  <div className="font-medium">{run.tool}</div>
                  <div className="text-xs text-muted-foreground">
                    {run.status === "success" ? run.result_summary : run.error}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {memo ? (
        <div className="space-y-3">
          <div className="text-base font-semibold text-primary">{memo.recommendation}</div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span
              className={cn(
                "rounded-full border px-2 py-1",
                memo.confidence_score > 0.7 ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"
              )}
            >
              Confidence {(memo.confidence_score * 100).toFixed(0)}%
            </span>
            <span className="rounded-full border bg-background px-2 py-1 text-foreground">
              Risk {memo.risk_band}
            </span>
          </div>
          {memo.scenario_tree && memo.scenario_tree.length > 0 && (
            <div className="rounded-lg border bg-background/70 p-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Scenario tree
              </div>
              <div className="space-y-2 text-sm">
                {memo.scenario_tree.slice(0, 3).map((scenario: any, index: number) => (
                  <div key={index}>
                    <span className="font-medium">{scenario.scenario || scenario.event}:</span>{" "}
                    {scenario.impact || scenario.description}
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
        </div>
      ) : (
        <div className="whitespace-pre-wrap">{content}</div>
      )}
    </div>
  )
}
