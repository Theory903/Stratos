"use client"
import { useSearchParams } from "next/navigation"
import { startTransition, useEffect, useRef, useState } from "react"
import ReactMarkdown from "react-markdown"
import {
  Bell,
  Bot,
  CheckCircle2,
  Clock,
  FileText,
  History,
  Loader2,
  MessageSquare,
  MoreHorizontal,
  Play,
  Send,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  TrendingDown,
  TrendingUp,
  User,
  X,
  XCircle,
} from "lucide-react"

import { AgentResponse, api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SegmentedControl } from "@/components/dashboard/shell"
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
  context?: { intent: string; role: string; mode?: string }
  memo?: AgentResponse
  plan?: PlanStep[]
  status?: string
  toolRuns?: ToolRun[]
  isThinking?: boolean
  error?: string
  streamingContent?: string
  timestamp?: Date
}

interface Thread {
  id: string
  title: string
  status: "active" | "completed" | "interrupted" | "pending"
  mode: string
  createdAt: string
  updatedAt: string
  messages: number
}

interface Approval {
  id: string
  title: string
  type: string
  risk: "low" | "medium" | "high"
  requestedAt: string
  requestedBy: string
  action: string
  details: string
}

const guidedPrompts = [
  { label: "Portfolio shock", prompt: "What do sticky inflation, oil pressure, and BTC risk sentiment mean for my portfolio?" },
  { label: "Country risk", prompt: "How should I frame India sovereign risk versus US macro pressure this week?" },
  { label: "Single-name check", prompt: "What should I watch in AAPL quality, event pulse, and regime history before adding risk?" },
]

function isSubstantiveFinancePrompt(query: string): boolean {
  const normalized = query.trim().toLowerCase()
  if (!normalized) return false
  const financeKeywords = ["aapl", "btc", "india", "risk", "macro", "portfolio", "regime", "scenario", "fed", "oil", "inflation"]
  return (
    query.trim().split(/\s+/).length >= 3 ||
    financeKeywords.some((keyword) => normalized.includes(keyword)) ||
    /^[A-Z:]{2,10}\??$/.test(query.trim())
  )
}

type AgentTab = "runs" | "history" | "approvals"

export default function AgentPage() {
  const searchParams = useSearchParams()
  const initialTab = searchParams.get("tab") as AgentTab | null
  const isNewRun = searchParams.has("new")

  const [activeTab, setActiveTab] = useState<AgentTab>(initialTab || "runs")
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [hintIndex, setHintIndex] = useState(0)
  const [selectedMode, setSelectedMode] = useState<"auto" | "fast" | "council" | "research" | "replay">("auto")
  const scrollRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const threadIdRef = useRef<string>(crypto.randomUUID())

  const [threads] = useState<Thread[]>([
    { id: "1", title: "AAPL hedge recommendation", status: "completed", mode: "council", createdAt: "2024-01-15T10:30:00Z", updatedAt: "2024-01-15T10:45:00Z", messages: 12 },
    { id: "2", title: "Portfolio risk assessment", status: "completed", mode: "research", createdAt: "2024-01-14T14:20:00Z", updatedAt: "2024-01-14T14:55:00Z", messages: 8 },
    { id: "3", title: "BTC sentiment analysis", status: "active", mode: "council", createdAt: "2024-01-15T09:00:00Z", updatedAt: "2024-01-15T09:15:00Z", messages: 3 },
    { id: "4", title: "Oil scenario analysis", status: "interrupted", mode: "research", createdAt: "2024-01-13T16:00:00Z", updatedAt: "2024-01-13T16:30:00Z", messages: 5 },
  ])

  const [approvals] = useState<Approval[]>([
    { id: "1", title: "Reduce AAPL position", type: "trade", risk: "medium", requestedAt: "2024-01-15T09:30:00Z", requestedBy: "Agent", action: "SELL 10%", details: "Overweight concentration at 18%, exceeds 15% limit" },
    { id: "2", title: "Add BTC hedge", type: "trade", risk: "high", requestedAt: "2024-01-15T08:45:00Z", requestedBy: "Agent", action: "BUY 5%", details: "Vol spike detected, regime shift from risk-on to neutral" },
    { id: "3", title: "Update INFY thesis", type: "research", risk: "low", requestedAt: "2024-01-14T17:00:00Z", requestedBy: "Agent", action: "BULLISH", details: "Margin expansion continues, new deal wins" },
  ])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  useEffect(() => {
    const textarea = composerRef.current
    if (!textarea) return
    textarea.style.height = "0px"
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }, [query])

  useEffect(() => {
    if (query.trim()) return
    const intervalId = window.setInterval(() => {
      startTransition(() => {
        setHintIndex((current) => (current + 1) % guidedPrompts.length)
      })
    }, 4500)
    return () => window.clearInterval(intervalId)
  }, [query])

  const activeGuide = guidedPrompts[hintIndex]

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) return

    if (!isSubstantiveFinancePrompt(trimmedQuery)) {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "user", content: trimmedQuery },
        { id: crypto.randomUUID(), role: "assistant", content: "Ask a portfolio, macro, event, or research question with enough context to ground the workflow." },
      ])
      setQuery("")
      return
    }

    const assistantId = crypto.randomUUID()
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", content: trimmedQuery }
    const assistantMessage: Message = { 
      id: assistantId, 
      role: "assistant", 
      content: "", 
      status: "Initializing STRATOS...",
      isThinking: true,
      toolRuns: [] 
    }

    setMessages((current) => [...current, userMessage, assistantMessage])
    setQuery("")
    setLoading(true)

    try {
      await api.orchestrateV5Stream(
        trimmedQuery,
        (type, data) => {
          startTransition(() => {
            setMessages((current) =>
              current.map((message) => {
                if (message.id !== assistantId) return message
                
                if (type === "status") {
                  return { ...message, status: data?.message || data }
                }
                if (type === "context") {
                  return { 
                    ...message, 
                    context: { 
                      intent: "research", 
                      role: data?.mode || "pm",
                      mode: data?.mode 
                    },
                    status: `Running in ${data?.mode || 'auto'} mode...`
                  }
                }
                if (type === "node_start" || type === "node_progress") {
                  const nodeName = data?.node || data?.stage || 'node'
                  const cleanName = nodeName.replace('RunnableSequence', '').replace(/_/g, ' ')
                  return { ...message, status: `Running ${cleanName || 'node'}...` }
                }
                if (type === "node_complete") {
                  return message
                }
                if (type === "token") {
                  const tokenContent = data?.content || ""
                  if (tokenContent) {
                    const currentContent = message.streamingContent || ""
                    return { ...message, streamingContent: currentContent + tokenContent }
                  }
                  return message
                }
                if (type === "final_output") {
                  const packet = data?.packet || {}
                  const thesis = packet?.thesis || ""
                  return {
                    ...message,
                    content: thesis,
                    isThinking: false,
                    streamingContent: undefined,
                    memo: {
                      intent: packet?.intent || "research",
                      role: packet?.action === "buy" ? "cfo" : "pm",
                      decision: packet?.action || "info",
                      summary: thesis,
                      recommendation: thesis,
                      confidence_score: packet?.confidence || 0.5,
                      confidence_calibration: (packet?.confidence || 0) > 0.7 ? "high" : "medium",
                      risk_band: packet?.action === "buy" ? "Low" : packet?.action === "sell" ? "High" : "Medium",
                      worst_case: "",
                      evidence_blocks: [],
                      key_findings: [],
                      specialist_views: [],
                      trace: {},
                    },
                    status: undefined,
                  }
                }
                if (type === "error") {
                  return { ...message, error: data?.message || "Unknown error", status: undefined, isThinking: false }
                }
                return message
              })
            )
          })
        },
        { threadId: threadIdRef.current }
      )
    } catch {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId ? { ...message, status: undefined, content: "The V5 orchestrator failed. Please try again." } : message
        )
      )
    } finally {
      setLoading(false)
    }
  }

  const startNewRun = () => {
    setMessages([])
    threadIdRef.current = crypto.randomUUID()
    setActiveTab("runs")
  }

  return (
    <div className="flex h-[calc(100vh-140px)] flex-col lg:h-[calc(100vh-180px)]">
      {/* Tab Navigation */}
      <div className="mb-4 flex items-center justify-between border-b border-slate-200">
        <div className="flex gap-1">
          <button
            onClick={() => setActiveTab("runs")}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
              activeTab === "runs"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            )}
          >
            <MessageSquare className="h-4 w-4" />
            Runs
            {loading && <span className="ml-1 h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />}
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
              activeTab === "history"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            )}
          >
            <History className="h-4 w-4" />
            History
            <span className="ml-1 rounded-full bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
              {threads.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("approvals")}
            className={cn(
              "flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors",
              activeTab === "approvals"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            )}
          >
            <Bell className="h-4 w-4" />
            Approvals
            {approvals.length > 0 && (
              <span className="ml-1 rounded-full bg-amber-500 px-1.5 py-0.5 text-xs font-bold text-white">
                {approvals.length}
              </span>
            )}
          </button>
        </div>
        <Button onClick={startNewRun} size="sm" className="gap-2">
          <Sparkles className="h-4 w-4" />
          New Run
        </Button>
      </div>

      {/* Tab Content */}
      {activeTab === "runs" && (
        <RunsTab
          query={query}
          setQuery={setQuery}
          messages={messages}
          loading={loading}
          hintIndex={hintIndex}
          activeGuide={activeGuide}
          selectedMode={selectedMode}
          setSelectedMode={setSelectedMode}
          handleSubmit={handleSubmit}
          scrollRef={scrollRef}
          composerRef={composerRef}
        />
      )}

      {activeTab === "history" && (
        <HistoryTab threads={threads} />
      )}

      {activeTab === "approvals" && (
        <ApprovalsTab approvals={approvals} />
      )}
    </div>
  )
}

function RunsTab({
  query,
  setQuery,
  messages,
  loading,
  hintIndex,
  activeGuide,
  selectedMode,
  setSelectedMode,
  handleSubmit,
  scrollRef,
  composerRef,
}: {
  query: string
  setQuery: (q: string) => void
  messages: Message[]
  loading: boolean
  hintIndex: number
  activeGuide: typeof guidedPrompts[0]
  selectedMode: "auto" | "fast" | "council" | "research" | "replay"
  setSelectedMode: (m: "auto" | "fast" | "council" | "research" | "replay") => void
  handleSubmit: (e: React.FormEvent) => void
  scrollRef: React.RefObject<HTMLDivElement>
  composerRef: React.RefObject<HTMLTextAreaElement>
}) {
  return (
    <>
      {/* Messages */}
      <div className="quiet-scroll content-auto flex-1 space-y-4 overflow-y-auto px-2 pb-4" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="flex h-full min-h-[40vh] flex-col items-center justify-center text-center">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg">
              <Bot className="h-7 w-7" />
            </div>
            <h2 className="text-xl font-semibold tracking-tight text-slate-900">Start a Run</h2>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              Ask about portfolio analysis, market research, or investment decisions.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {guidedPrompts.map((prompt, i) => (
                <button
                  key={prompt.label}
                  type="button"
                  className={cn(
                    "rounded-full border px-4 py-2 text-sm font-medium transition-colors",
                    i === hintIndex
                      ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                  )}
                  onClick={() => setQuery(prompt.prompt)}
                >
                  {prompt.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {loading && messages[messages.length - 1]?.role === "user" && (
          <div className="flex items-center gap-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
              <Bot className="h-4 w-4" />
            </div>
            <ThinkingCard status="Generating response..." />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white px-4 py-4">
        <div className="mx-auto max-w-3xl">
          {/* Mode Selector */}
          <div className="mb-3">
            <SegmentedControl
              value={selectedMode}
              onChange={(v) => setSelectedMode(v as typeof selectedMode)}
              items={[
                { label: "Auto", value: "auto" },
                { label: "Fast", value: "fast" },
                { label: "Council", value: "council" },
                { label: "Research", value: "research" },
              ]}
            />
          </div>
          <form
            onSubmit={handleSubmit}
            className="relative flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-1.5 shadow-sm transition-all focus-within:border-indigo-200 focus-within:shadow-md focus-within:ring-2 focus-within:ring-indigo-500/10"
          >
            <textarea
              ref={composerRef}
              placeholder={`Ask about ${activeGuide.prompt.slice(0, 50)}...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  if (query.trim()) handleSubmit(e as unknown as React.FormEvent)
                }
              }}
              disabled={loading}
              rows={1}
              className="max-h-40 min-h-[48px] flex-1 resize-none rounded-xl border-0 bg-transparent px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0 disabled:bg-transparent"
            />
            <Button
              type="submit"
              size="icon"
              disabled={loading || !query.trim()}
              className="h-10 w-10 shrink-0 rounded-xl bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-200 transition-colors"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
        </div>
      </div>
    </>
  )
}

function HistoryTab({ threads }: { threads: Thread[] }) {
  return (
    <div className="overflow-y-auto">
      <div className="space-y-2">
        {threads.map((thread) => (
          <Card key={thread.id} className="cursor-pointer transition-colors hover:bg-slate-50">
            <CardContent className="flex items-center justify-between p-4">
              <div className="flex items-center gap-4">
                <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl",
                  thread.status === "active" && "bg-indigo-100 text-indigo-600",
                  thread.status === "completed" && "bg-emerald-100 text-emerald-600",
                  thread.status === "interrupted" && "bg-amber-100 text-amber-600",
                  thread.status === "pending" && "bg-slate-100 text-slate-600"
                )}>
                  {thread.status === "active" && <Play className="h-4 w-4" />}
                  {thread.status === "completed" && <CheckCircle2 className="h-4 w-4" />}
                  {thread.status === "interrupted" && <XCircle className="h-4 w-4" />}
                  {thread.status === "pending" && <Clock className="h-4 w-4" />}
                </div>
                <div>
                  <div className="font-medium text-slate-900">{thread.title}</div>
                  <div className="flex items-center gap-2 text-sm text-slate-500">
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{thread.mode}</span>
                    <span>·</span>
                    <span>{thread.messages} messages</span>
                    <span>·</span>
                    <span>{new Date(thread.updatedAt).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
              <Button size="sm" variant="ghost">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function ApprovalsTab({ approvals }: { approvals: Approval[] }) {
  const handleApprove = (id: string) => {
    console.log("Approving:", id)
  }

  const handleReject = (id: string) => {
    console.log("Rejecting:", id)
  }

  return (
    <div className="overflow-y-auto">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Pending Approvals</h3>
        <p className="text-sm text-slate-500">Review and approve/reject agent recommendations</p>
      </div>
      <div className="space-y-4">
        {approvals.map((approval) => (
          <Card key={approval.id}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <span className={cn(
                    "rounded px-2 py-0.5 text-xs font-semibold",
                    approval.risk === "high" && "bg-red-100 text-red-700",
                    approval.risk === "medium" && "bg-amber-100 text-amber-700",
                    approval.risk === "low" && "bg-emerald-100 text-emerald-700"
                  )}>
                    {approval.risk} risk
                  </span>
                  {approval.title}
                </CardTitle>
                <span className="text-xs text-slate-500">
                  {new Date(approval.requestedAt).toLocaleString()}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4 rounded-lg bg-slate-50 p-3">
                <div className="mb-1 text-sm font-medium text-slate-700">Details</div>
                <p className="text-sm text-slate-600">{approval.details}</p>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <User className="h-4 w-4" />
                  <span>Requested by {approval.requestedBy}</span>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1 border-red-200 text-red-600 hover:bg-red-50"
                    onClick={() => handleReject(approval.id)}
                  >
                    <ThumbsDown className="h-4 w-4" />
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    className="gap-1 bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleApprove(approval.id)}
                  >
                    <ThumbsUp className="h-4 w-4" />
                    Approve
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  if (isUser) {
    return (
      <div className="flex flex-row-reverse gap-4 max-w-[85%] ml-auto">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
          <User className="h-4 w-4" />
        </div>
        <div>
          <div className="inline-block rounded-2xl rounded-br-md bg-slate-900 px-4 py-3 text-sm text-white">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  if (message.isThinking || message.status || message.streamingContent) {
    return (
      <div className="flex gap-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
          <Bot className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <ThinkingCard status={message.status} />
          {message.streamingContent && (
            <StreamingThoughts content={message.streamingContent} />
          )}
        </div>
      </div>
    )
  }

  if (message.memo) {
    return (
      <div className="flex gap-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md">
          <Bot className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <MemoCard memo={message.memo} />
        </div>
      </div>
    )
  }

  if (message.error) {
    return (
      <div className="flex gap-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-600 shadow-md">
          <XCircle className="h-4 w-4" />
        </div>
        <div className="flex-1">
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <div className="font-medium">Something went wrong</div>
            <div className="mt-1 text-red-600">{message.error}</div>
          </div>
        </div>
      </div>
    )
  }

  return null
}

function StreamingThoughts({ content }: { content: string }) {
  const parseTokenContent = (text: string) => {
    try {
      const parsed = JSON.parse(text)
      if (parsed.mode) return { type: 'mode', data: parsed }
      if (parsed.bull_thesis || parsed.bear_thesis) return { type: 'thesis', data: parsed }
      if (parsed.domain) return { type: 'specialist', data: parsed }
      return { type: 'raw', data: text }
    } catch {
      return { type: 'raw', data: text }
    }
  }

  const parsed = parseTokenContent(content)

  if (parsed.type === 'mode' && parsed.data.mode) {
    return (
      <div className="mt-3 rounded-xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-purple-50/80 p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
          <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">Research Mode</span>
        </div>
        <div className="text-sm font-medium text-slate-800">{parsed.data.rationale?.slice(0, 200)}...</div>
      </div>
    )
  }

  if (parsed.type === 'thesis' && (parsed.data.bull_thesis || parsed.data.bear_thesis)) {
    return (
      <div className="mt-3 rounded-xl border border-emerald-100 bg-gradient-to-br from-emerald-50/80 to-green-50/80 p-4">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="h-4 w-4 text-emerald-600" />
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600">Bull Case</span>
        </div>
        <p className="text-sm text-slate-700 line-clamp-3">{parsed.data.bull_thesis}</p>
        {parsed.data.bear_thesis && (
          <>
            <div className="flex items-center gap-2 mt-3 mb-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              <span className="text-xs font-semibold uppercase tracking-wider text-red-500">Bear Case</span>
            </div>
            <p className="text-sm text-slate-700 line-clamp-3">{parsed.data.bear_thesis}</p>
          </>
        )}
      </div>
    )
  }

  if (parsed.type === 'specialist' && parsed.data.domain) {
    const domainColors: Record<string, string> = {
      macro: 'from-blue-50 to-blue-100 border-blue-200',
      portfolio: 'from-purple-50 to-purple-100 border-purple-200',
      market: 'from-emerald-50 to-emerald-100 border-emerald-200',
      news: 'from-amber-50 to-amber-100 border-amber-200',
      social: 'from-pink-50 to-pink-100 border-pink-200',
    }
    const colorClass = domainColors[parsed.data.domain] || 'from-slate-50 to-slate-100 border-slate-200'
    
    return (
      <div className={`mt-3 rounded-xl border bg-gradient-to-br ${colorClass} p-4`}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">{parsed.data.domain} View</span>
          <span className="text-xs font-medium text-slate-500">Score: {parsed.data.score}</span>
        </div>
        <p className="text-sm text-slate-700 line-clamp-4">{parsed.data.thesis}</p>
      </div>
    )
  }

  return null
}

function ThinkingCard({ status }: { status?: string }) {
  const getThinkingMessage = (statusText?: string) => {
    if (!statusText) return "Analyzing your request..."
    const s = statusText.toLowerCase()
    if (s.includes("initializing")) return "Initializing STRATOS..."
    if (s.includes("running in")) return "Determining best approach..."
    if (s.includes("supervisor")) return "Coordinating specialists..."
    if (s.includes("macro")) return "Analyzing macro factors..."
    if (s.includes("market")) return "Evaluating market conditions..."
    if (s.includes("portfolio")) return "Building portfolio view..."
    if (s.includes("council")) return "Synthesizing specialist views..."
    return statusText
  }

  return (
    <div className="rounded-2xl border border-indigo-100/50 bg-gradient-to-br from-indigo-50/80 to-purple-50/80 p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-2 w-2 animate-bounce rounded-full bg-indigo-500"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-indigo-700">Thinking</div>
          <div className="mt-0.5 text-xs text-indigo-500/80">{getThinkingMessage(status)}</div>
        </div>
      </div>
    </div>
  )
}

function MemoCard({ memo }: { memo: AgentResponse }) {
  const confScore = Math.round(memo.confidence_score * 100)
  const confColor = memo.confidence_score >= 0.75 ? "emerald" : memo.confidence_score >= 0.45 ? "amber" : "red"
  const answer = memo.summary || memo.recommendation || ""

  return (
    <div className="space-y-3">
      <div className="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-sm">
        <div className="mb-3 flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-indigo-500 to-purple-600">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">STRATOS</span>
          <span className={cn(
            "ml-auto rounded px-2 py-0.5 text-xs font-semibold",
            confColor === "emerald" && "bg-emerald-100 text-emerald-700",
            confColor === "amber" && "bg-amber-100 text-amber-700",
            confColor === "red" && "bg-red-100 text-red-700"
          )}>
            {confScore}% confidence
          </span>
        </div>
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{answer}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
