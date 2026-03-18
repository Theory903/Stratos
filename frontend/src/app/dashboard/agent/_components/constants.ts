import type { RoleLens, ResponseMode } from "./types"

export const roleLenses: Array<{ id: RoleLens; label: string; description: string }> = [
  { id: "auto", label: "Auto", description: "Let STRATOS choose the right runtime, tools, and specialist view." },
  { id: "general", label: "General LLM", description: "Open-ended reasoning, writing, and planning." },
  { id: "ca", label: "CA", description: "Accounting, controls, close, tax, and compliance work." },
  { id: "pm", label: "PM", description: "Portfolio, risk, capital allocation, and scenario decisions." },
  { id: "cfa", label: "CFA", description: "Valuation, equity research, diligence, and investment memos." },
  { id: "cmo", label: "CMO", description: "Campaigns, growth, positioning, and GTM execution." },
]

export const responseModes: Array<{ id: ResponseMode; label: string; description: string }> = [
  { id: "direct", label: "Direct", description: "Fast answer-first response." },
  { id: "research", label: "Research", description: "Evidence-led answer with citations when possible." },
  { id: "memo", label: "Memo", description: "Decision memo with structure and action items." },
  { id: "presentation", label: "Presentation", description: "Board-style output for distribution." },
]

export const guidedPrompts: Array<{
  label: string
  prompt: string
  hint: string
  lens: RoleLens
  mode: ResponseMode
}> = [
  {
    label: "Portfolio shock",
    prompt: "What do sticky inflation, oil pressure, and BTC risk sentiment mean for my portfolio?",
    hint: "Mention the book, the shock, and the decision you need to make.",
    lens: "pm",
    mode: "memo",
  },
  {
    label: "Country risk",
    prompt: "How should I frame India sovereign risk versus US macro pressure this week?",
    hint: "Good for macro or policy framing before sizing new exposure.",
    lens: "pm",
    mode: "research",
  },
  {
    label: "Single-name check",
    prompt: "What should I watch in AAPL quality, event pulse, and regime history before adding risk?",
    hint: "Best when you want one clean memo instead of three separate dashboards.",
    lens: "cfa",
    mode: "memo",
  },
  {
    label: "Month-end close",
    prompt: "Act as my CA and build a month-end close checklist with reconciliations, risk flags, and owner-wise deadlines.",
    hint: "Useful for finance ops, controls, and audit readiness.",
    lens: "ca",
    mode: "memo",
  },
  {
    label: "CMO launch plan",
    prompt: "Act as my CMO and create a 30-day launch plan for STRATOS with messaging, channels, KPIs, and weekly experiments.",
    hint: "Good for positioning, demand gen, and campaign planning.",
    lens: "cmo",
    mode: "presentation",
  },
  {
    label: "General operator",
    prompt: "Break this project into a practical execution plan, key risks, owners, and next actions.",
    hint: "Use when you want broad LLM help instead of a finance-only memo.",
    lens: "general",
    mode: "direct",
  },
]
