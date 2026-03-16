import Link from "next/link"
import { ArrowRight, Bot, BriefcaseBusiness, LayoutDashboard } from "lucide-react"

import { PulseItem } from "@/lib/app-state"
import { LiveHomePulse } from "@/components/marketing/live-home-pulse"
import { HomepageTopNav } from "@/components/marketing/homepage-top-nav"

function PreviewMetric({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string
  value: string
  detail: string
  tone?: "neutral" | "warn" | "risk"
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
      <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-slate-500">{label}</div>
      <div
        className={[
          "mt-2 font-display text-lg font-bold tracking-[-0.04em]",
          tone === "warn" ? "text-amber-300" : tone === "risk" ? "text-orange-300" : "text-slate-50",
        ].join(" ")}
      >
        {value}
      </div>
      <div className="mt-1 text-xs text-slate-500">{detail}</div>
    </div>
  )
}

export function MarketingHomePage({
  pulse,
  homeHref = "/",
  authenticated = false,
  workspaceHref = "/dashboard",
  userLabel,
}: {
  pulse: PulseItem[]
  homeHref?: string
  authenticated?: boolean
  workspaceHref?: string
  userLabel?: string | null
}) {
  return (
    <div className="min-h-screen bg-[#06080d] text-slate-100">
      <div className="absolute inset-x-0 top-0 h-[480px] bg-[radial-gradient(circle_at_top_left,rgba(26,140,255,0.18),transparent_28%),radial-gradient(circle_at_top_right,rgba(0,212,180,0.12),transparent_25%)]" />
      <div className="relative">
        <HomepageTopNav
          homeHref={homeHref}
          authenticated={authenticated}
          workspaceHref={workspaceHref}
          userLabel={userLabel}
        />

        <div className="mx-auto max-w-[1240px] px-4 lg:px-8">
          <div id="pulse" className="pt-3">
            <LiveHomePulse initialItems={pulse} />
          </div>

          <section className="grid gap-10 py-16 lg:grid-cols-[1fr_480px] lg:items-center lg:py-20">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Finance OS · PM edition
              </div>
              <h1 className="mt-5 max-w-[12ch] font-display text-5xl font-black tracking-[-0.08em] text-slate-50 md:text-6xl">
                Signals in.
                <br />
                Decisions out.
              </h1>
              <p className="mt-5 max-w-xl text-base leading-7 text-slate-400">
                STRATOS turns macro pressure, portfolio state, and event intelligence into structured
                decisions for PMs, analysts, and C-suite operators who cannot afford noise.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  href={authenticated ? workspaceHref : "/auth/signin?return_url=/onboarding/workspace"}
                  className="inline-flex items-center gap-2 rounded-2xl bg-sky-500 px-5 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 hover:bg-sky-400"
                >
                  {authenticated ? "Open workspace" : "Start workspace"} <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/api/demo"
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 px-5 py-3 text-sm font-semibold text-slate-200 transition-colors hover:border-slate-700 hover:text-white"
                >
                  Try sample workspace
                </Link>
              </div>
              <p className="mt-4 text-xs text-slate-500">
                No credit card · Role-aware from day one · India + US + BTC scope
              </p>
            </div>

            <div id="command" className="rounded-[1.5rem] border border-slate-800 bg-slate-950/70 p-4 shadow-[0_30px_120px_-48px_rgba(0,0,0,0.8)]">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-slate-500">
                  Command Center
                </div>
                <div className="flex items-center gap-2 text-[11px] text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                  Live · India · US · BTC
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <PreviewMetric label="Macro regime" value="RISK-OFF" detail="Elevated · 3 signals" tone="risk" />
                <PreviewMetric label="Portfolio risk" value="ELEVATED" detail="Δ +0.18 vs prior week" tone="warn" />
              </div>
              <div className="mt-3 space-y-3">
                {[
                  ["RBI maintains stance amid sticky CPI", "Policy · 2h ago · HIGH URGENCY", "bg-red-400"],
                  ["BTC funding flips negative — watch unwind", "Crypto · 4h ago · MEDIUM", "bg-amber-400"],
                ].map(([title, detail, color]) => (
                  <div key={title} className="flex items-start gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                    <span className={`mt-1 h-8 w-1 rounded-full ${color}`} />
                    <div>
                      <div className="text-sm font-medium text-slate-100">{title}</div>
                      <div className="mt-1 text-xs text-slate-500">{detail}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex items-center gap-3 rounded-2xl border border-sky-500/25 bg-sky-500/10 p-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-950 text-sky-300">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="flex-1 text-sm text-slate-300">
                  “What do oil, sticky inflation, and BTC sentiment mean for my portfolio?”
                </div>
                <span className="font-mono-ui text-xs font-semibold text-sky-300">Ask →</span>
              </div>
            </div>
          </section>

          <section id="workflows" className="py-4">
            <div className="mb-5 font-mono-ui text-[11px] uppercase tracking-[0.24em] text-slate-500">
              Core workflows
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              {[
                {
                  icon: LayoutDashboard,
                  title: "Command Center",
                  body: "What matters now — macro, pulse, risk, queue.",
                },
                {
                  icon: BriefcaseBusiness,
                  title: "Portfolio OS",
                  body: "What it means for your book — positions, exposure, scenarios.",
                },
                {
                  icon: Bot,
                  title: "Decision Agent",
                  body: "One question in. Structured decision memo out.",
                },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.title}
                    className="rounded-[1.35rem] border border-slate-800 bg-slate-950/55 p-5 transition-colors hover:border-slate-700"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-slate-200">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="mt-4 font-display text-xl font-bold tracking-[-0.04em] text-slate-50">
                      {item.title}
                    </div>
                    <div className="mt-2 text-sm leading-6 text-slate-400">{item.body}</div>
                  </div>
                )
              })}
            </div>
          </section>

          <section id="roles" className="my-12 rounded-[1.5rem] border border-slate-800 bg-[#080e1a] p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="font-display text-2xl font-bold tracking-[-0.05em] text-slate-50">
                  One engine. Four lenses.
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  Role-aware shell adapts emphasis, prompts, and defaults to your function.
                </p>
              </div>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {[
                ["PM", "NOW LIVE", "Portfolio Manager", "Risk, scenarios, positioning, events → memo. 2–4 clicks to insight."],
                ["Analyst", "COMING SOON", "Analyst", "Compare, anomaly, quality signals, peer context, evidence stack."],
                ["CFO", "COMING SOON", "CFO", "Macro pressure, rates/FX exposure, business sensitivity mapping."],
                ["CEO", "COMING SOON", "CEO", "What matters, key risks, strategic memo. Signal without the noise."],
              ].map(([tag, badge, title, body]) => (
                <div
                  key={title}
                  className="relative rounded-[1.1rem] border border-slate-800 bg-slate-950/50 p-4 transition-colors hover:border-slate-700"
                >
                  <span className="font-mono-ui text-[10px] font-bold uppercase tracking-[0.2em] text-sky-300">
                    {tag}
                  </span>
                  <span className="absolute right-4 top-4 rounded border border-sky-500/25 bg-sky-500/10 px-2 py-1 font-mono-ui text-[9px] uppercase tracking-[0.18em] text-sky-300">
                    {badge}
                  </span>
                  <div className="mt-4 font-display text-lg font-bold tracking-[-0.04em] text-slate-50">
                    {title}
                  </div>
                  <div className="mt-2 text-sm leading-6 text-slate-500">{body}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="pb-16 text-center">
            <h2 className="font-display text-4xl font-black tracking-[-0.06em] text-slate-50">
              Your decision surface is ready.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-500">
              Set up your workspace in under 3 minutes. Upload a portfolio, choose your scope, open
              Command.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Link
                href={authenticated ? workspaceHref : "/auth/signin?return_url=/onboarding/workspace"}
                className="inline-flex items-center gap-2 rounded-2xl bg-sky-500 px-5 py-3 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5 hover:bg-sky-400"
              >
                {authenticated ? "Open workspace" : "Start workspace"} <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/api/demo"
                className="inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 px-5 py-3 text-sm font-semibold text-slate-200 transition-colors hover:border-slate-700 hover:text-white"
              >
                Try sample workspace
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-5 font-mono-ui text-[11px] uppercase tracking-[0.22em] text-slate-600">
              <span>Docs</span>
              <span>Pricing</span>
              <span>Privacy</span>
              <span>© 2026 STRATOS</span>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
