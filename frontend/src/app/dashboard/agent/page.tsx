"use client";
import { startTransition, useEffect, useRef, useState } from "react";
import { Bot, Loader2, Send, Sparkles, User } from "lucide-react";

import { AgentResponse, api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PlanStep {
  tool_name: string;
  arguments: Record<string, unknown>;
}

interface ToolRun {
  tool: string;
  status: "success" | "failed";
  result_summary?: string;
  error?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  context?: { intent: string; role: string };
  memo?: AgentResponse;
  plan?: PlanStep[];
  status?: string;
  toolRuns?: ToolRun[];
}

const guidedPrompts = [
  {
    label: "Portfolio shock",
    prompt:
      "What do sticky inflation, oil pressure, and BTC risk sentiment mean for my portfolio?",
  },
  {
    label: "Country risk",
    prompt:
      "How should I frame India sovereign risk versus US macro pressure this week?",
  },
  {
    label: "Single-name check",
    prompt:
      "What should I watch in AAPL quality, event pulse, and regime history before adding risk?",
  },
];

function isSubstantiveFinancePrompt(query: string): boolean {
  // Accept all non-empty queries
  return query.trim().length > 0;
}

export default function AgentPage() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const threadIdRef = useRef<string>(crypto.randomUUID());

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    const textarea = composerRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [query]);

  useEffect(() => {
    if (query.trim()) return;
    const intervalId = window.setInterval(() => {
      startTransition(() => {
        setHintIndex((current) => (current + 1) % guidedPrompts.length);
      });
    }, 4500);
    return () => window.clearInterval(intervalId);
  }, [query]);

  const activeGuide = guidedPrompts[hintIndex];

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    const assistantId = crypto.randomUUID();
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmedQuery,
    };
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      status: "Planning execution strategy...",
      toolRuns: [],
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setQuery("");
    setLoading(true);

    try {
      await api.orchestrateV5Stream(
        trimmedQuery,
        (type, data) => {
          startTransition(() => {
            setMessages((current) =>
              current.map((message) => {
                if (message.id !== assistantId) return message;
                if (type === "status")
                  return { ...message, status: data?.message || data };
                if (type === "context")
                  return {
                    ...message,
                    context: { intent: "research", role: data?.mode || "pm" },
                  };
                if (type === "node_start" || type === "node_progress")
                  return {
                    ...message,
                    status: `Running ${data?.node || data?.stage || "node"}...`,
                  };
                if (type === "node_complete")
                  return { ...message, status: `Completed ${data?.node}.` };
                if (type === "token")
                  return {
                    ...message,
                    content: (message.content || "") + (data?.content || ""),
                  };
                if (type === "final_output") {
                  const packet = data?.packet || {};
                  const thesis = packet?.thesis || "";
                  return {
                    ...message,
                    content: "",
                    memo: {
                      intent: "research",
                      role: packet?.action === "buy" ? "cfo" : "pm",
                      decision: packet?.action || "hold",
                      summary: thesis,
                      recommendation: thesis,
                      confidence_score: packet?.confidence || 0.5,
                      confidence_calibration:
                        (packet?.confidence || 0) > 0.7 ? "high" : "medium",
                      risk_band: packet?.action === "buy" ? "low" : "medium",
                      worst_case: "",
                      evidence_blocks: [],
                      key_findings: [],
                      specialist_views: [],
                      trace: {},
                    },
                    status: undefined,
                  };
                }
                if (type === "error")
                  return {
                    ...message,
                    status: `Error: ${data?.message || "Unknown error"}`,
                  };
                return message;
              }),
            );
          });
        },
        { threadId: threadIdRef.current },
      );
    } catch {
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                status: undefined,
                content: "The V5 orchestrator failed. Please try again.",
              }
            : message,
        ),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-slate-900">Agent</h1>
          <p className="text-xs text-slate-500">V5 Orchestrator</p>
        </div>
      </div>

      {/* Messages */}
      <div
        className="quiet-scroll content-auto flex-1 space-y-8 overflow-y-auto px-6 pb-6"
        ref={scrollRef}
      >
        {messages.length === 0 && (
          <div className="flex h-full min-h-[60vh] flex-col items-center justify-center text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
              <Bot className="h-8 w-8" />
            </div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
              What can I help with?
            </h2>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              Portfolio analysis, market research, or investment decisions.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-2">
              {guidedPrompts.map((prompt) => (
                <button
                  key={prompt.label}
                  type="button"
                  className="rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50"
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
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100">
              <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
            </div>
            <div className="text-sm text-slate-500">Thinking...</div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 bg-white px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <form
            onSubmit={handleSubmit}
            className="relative flex items-end gap-2 rounded-xl border border-slate-200 bg-slate-50/50 p-1.5 transition-colors focus-within:border-slate-300 focus-within:bg-white"
          >
            <textarea
              ref={composerRef}
              placeholder={`Ask about ${activeGuide.prompt.slice(0, 50)}...`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (query.trim())
                    handleSubmit(e as unknown as React.FormEvent);
                }
              }}
              disabled={loading}
              rows={1}
              className="max-h-40 min-h-[44px] flex-1 resize-none rounded-lg border-0 bg-transparent px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0 disabled:bg-transparent"
            />
            <Button
              type="submit"
              size="icon"
              disabled={loading || !query.trim()}
              className="h-9 w-9 shrink-0 rounded-lg bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-200"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
          <div className="mt-3 flex gap-2">
            {guidedPrompts.map((prompt, index) => (
              <button
                key={prompt.label}
                type="button"
                className={cn(
                  "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                  index === hintIndex
                    ? "border-cyan-200 bg-cyan-50 text-cyan-700"
                    : "border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700",
                )}
                onClick={() => {
                  setHintIndex(index);
                  setQuery(prompt.prompt);
                }}
              >
                {prompt.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-medium",
          isUser ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("max-w-2xl", isUser ? "text-right" : "text-left")}>
        {message.status && (
          <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
            <Loader2 className="h-3 w-3 animate-spin" />
            {message.status}
          </div>
        )}
        {isUser ? (
          <div className="inline-block rounded-2xl bg-slate-900 px-4 py-2.5 text-sm text-white">
            {message.content}
          </div>
        ) : message.memo ? (
          <div className="text-sm text-slate-700">{message.content}</div>
        ) : null}
      </div>
    </div>
  );
}

function MemoCard({ memo }: { memo: AgentResponse }) {
  const confScore = Math.round(memo.confidence_score * 100);
  const confColor =
    memo.confidence_score >= 0.75
      ? "emerald"
      : memo.confidence_score >= 0.45
        ? "amber"
        : "red";
  const riskColor =
    memo.risk_band === "Low"
      ? "emerald"
      : memo.risk_band === "Medium"
        ? "amber"
        : "red";

  return (
    <div className="w-full max-w-2xl space-y-4">
      {/* Decision Header */}
      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Decision
            </div>
            <div className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">
              {memo.decision || memo.recommendation}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <Badge color={confColor} label={`${confScore}%`} sub="confidence" />
            <Badge
              color={riskColor}
              label={memo.risk_band || "medium"}
              sub="risk"
            />
          </div>
        </div>

        {memo.summary && (
          <p className="mt-4 text-sm leading-relaxed text-slate-600">
            {memo.summary}
          </p>
        )}
      </div>

      {/* Answer Section */}
      {memo.recommendation && (
        <div className="rounded-2xl border border-slate-200/60 bg-slate-50/50 p-5">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
            Analysis
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-700">
            {memo.recommendation}
          </p>
        </div>
      )}

      {/* Key Insights Grid */}
      {(memo.key_findings?.length ||
        memo.historical_context?.length ||
        memo.portfolio_impact?.length) && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {memo.key_findings?.length && (
            <InsightCard title="Key Findings" items={memo.key_findings} />
          )}
          {memo.historical_context?.length && (
            <InsightCard title="Context" items={memo.historical_context} />
          )}
          {memo.portfolio_impact?.length && (
            <InsightCard title="Impact" items={memo.portfolio_impact} />
          )}
        </div>
      )}

      {/* Recommendations */}
      {(memo.recommended_actions?.length || memo.watch_items?.length) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {memo.recommended_actions?.length && (
            <InsightCard
              title="Actions"
              items={memo.recommended_actions}
              variant="action"
            />
          )}
          {memo.watch_items?.length && (
            <InsightCard
              title="Watch"
              items={memo.watch_items}
              variant="watch"
            />
          )}
        </div>
      )}

      {/* Evidence */}
      {memo.evidence_blocks?.length && (
        <div className="rounded-2xl border border-slate-200/60 bg-slate-50/50 p-5">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
            Evidence
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {memo.evidence_blocks.map((block, i) => (
              <div
                key={i}
                className="rounded-xl border border-slate-200/60 bg-white p-3"
              >
                <div className="text-xs font-medium text-slate-900">
                  {block.title}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {block.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warning */}
      {memo.worst_case && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200/60 bg-amber-50/50 p-4">
          <svg
            className="mt-0.5 h-5 w-5 shrink-0 text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span className="text-sm text-amber-800">{memo.worst_case}</span>
        </div>
      )}
    </div>
  );
}

function Badge({
  color,
  label,
  sub,
}: {
  color: "emerald" | "amber" | "red";
  label: string;
  sub: string;
}) {
  const styles = {
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
    red: "bg-red-50 text-red-700 border-red-200",
  };
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-1.5",
        styles[color],
      )}
    >
      <span className="text-sm font-semibold">{label}</span>
      <span className="text-[10px] uppercase tracking-wider opacity-70">
        {sub}
      </span>
    </div>
  );
}

function InsightCard({
  title,
  items,
  variant = "default",
}: {
  title: string;
  items: string[];
  variant?: "default" | "action" | "watch";
}) {
  const borderColors = {
    default: "border-slate-200/60 bg-white",
    action: "border-emerald-200/60 bg-emerald-50/30",
    watch: "border-amber-200/60 bg-amber-50/30",
  };
  return (
    <div className={cn("rounded-2xl border p-4", borderColors[variant])}>
      <div className="text-[10px] font-semibold uppercase tracking-widest text-slate-400">
        {title}
      </div>
      <div className="mt-2 space-y-1.5">
        {items.slice(0, 3).map((item, i) => (
          <div key={i} className="text-xs leading-relaxed text-slate-700">
            {item}
          </div>
        ))}
        {items.length > 3 && (
          <div className="text-[10px] text-slate-400">
            +{items.length - 3} more
          </div>
        )}
      </div>
    </div>
  );
}
