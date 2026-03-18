"use client"

import { startTransition, useEffect, useMemo, useState } from "react"
import { ArrowRight, CheckCircle2, FileUp, Loader2, Plus, Upload } from "lucide-react"
import { useRouter } from "next/navigation"

import {
  AppSession,
  OnboardingDraft,
  PortfolioImportMode,
  SAMPLE_PORTFOLIO,
  WorkspaceState,
  createDefaultDraft,
} from "@/lib/app-state"
import { DEMO_MODE_ENABLED } from "@/lib/runtime-flags"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

type PositionRow = {
  ticker: string
  quantity: string
  cost_basis: string
  asset_class: string
}

const LOCAL_STORAGE_PREFIX = "stratos.onboarding."
const REQUIRED_COLUMNS = ["ticker", "quantity", "cost_basis"] as const

function normalizeHeader(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, "_")
}

function parseCsv(text: string): {
  headers: string[]
  rows: PositionRow[]
  failedRows: string[]
} {
  const lines = text.replace(/\r\n/g, "\n").split("\n").filter(Boolean)
  if (lines.length < 2) {
    return { headers: [], rows: [], failedRows: ["CSV needs a header row and at least one data row."] }
  }

  const headers = lines[0].split(",").map(normalizeHeader)
  const missing = REQUIRED_COLUMNS.filter((column) => !headers.includes(column))
  if (missing.length > 0) {
    return {
      headers,
      rows: [],
      failedRows: [`Missing required columns: ${missing.join(", ")}`],
    }
  }

  const rows: PositionRow[] = []
  const failedRows: string[] = []
  const tickerIndex = headers.indexOf("ticker")
  const quantityIndex = headers.indexOf("quantity")
  const costBasisIndex = headers.indexOf("cost_basis")
  const assetClassIndex = headers.indexOf("asset_class")

  lines.slice(1).forEach((line, index) => {
    const values = line.split(",").map((value) => value.trim())
    const ticker = values[tickerIndex] || ""
    const quantity = values[quantityIndex] || ""
    const costBasis = values[costBasisIndex] || ""
    const assetClass = values[assetClassIndex] || "equity"

    if (!ticker || Number.isNaN(Number(quantity)) || Number.isNaN(Number(costBasis))) {
      failedRows.push(`Row ${index + 2}: invalid ticker, quantity, or cost basis.`)
      return
    }

    rows.push({
      ticker,
      quantity,
      cost_basis: costBasis,
      asset_class: assetClass || "equity",
    })
  })

  return { headers, rows, failedRows }
}

async function persistDraft(
  draft: Partial<OnboardingDraft>,
  workspace: Partial<WorkspaceState>
): Promise<void> {
  await fetch("/api/workspace", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft, workspace }),
  })
}

export function OnboardingWizard({
  session,
  initialDraft,
  initialWorkspace,
  initialStep,
}: {
  session: AppSession
  initialDraft: OnboardingDraft
  initialWorkspace: WorkspaceState
  initialStep: OnboardingDraft["step"]
}) {
  const router = useRouter()
  const localStorageKey = `${LOCAL_STORAGE_PREFIX}${session.userId}`
  const [step, setStep] = useState(initialStep)
  const [workspaceName, setWorkspaceName] = useState(initialDraft.workspaceName || initialWorkspace.workspaceName)
  const [role, setRole] = useState(initialDraft.role)
  const [focus, setFocus] = useState(initialDraft.focus)
  const [importMode, setImportMode] = useState<PortfolioImportMode>(initialDraft.portfolioImportMode ?? "none")
  const [markets, setMarkets] = useState<string[]>(initialDraft.scope.markets)
  const [benchmark, setBenchmark] = useState(initialDraft.scope.benchmark || initialWorkspace.benchmark)
  const [watchlistInput, setWatchlistInput] = useState(initialDraft.scope.watchlist.join(", "))
  const [manualRows, setManualRows] = useState<PositionRow[]>([
    { ticker: "", quantity: "", cost_basis: "", asset_class: "equity" },
  ])
  const [csvRows, setCsvRows] = useState<PositionRow[]>([])
  const [csvErrors, setCsvErrors] = useState<string[]>([])
  const [busy, setBusy] = useState<null | "save" | "portfolio" | "complete">(null)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    if (!DEMO_MODE_ENABLED && importMode === "sample") {
      setImportMode("none")
    }
  }, [importMode])

  useEffect(() => {
    const stored = window.localStorage.getItem(localStorageKey)
    if (!stored) {
      return
    }

    try {
      const draft = JSON.parse(stored) as {
        step?: OnboardingDraft["step"]
        workspaceName?: string
        role?: WorkspaceState["role"]
        focus?: WorkspaceState["focus"]
        importMode?: PortfolioImportMode
        markets?: string[]
        benchmark?: string
        watchlistInput?: string
        manualRows?: PositionRow[]
        csvRows?: PositionRow[]
      }

      if (draft.step) setStep(draft.step)
      if (draft.workspaceName) setWorkspaceName(draft.workspaceName)
      if (draft.role) setRole(draft.role)
      if (draft.focus) setFocus(draft.focus)
      if (draft.importMode) setImportMode(draft.importMode)
      if (draft.markets?.length) setMarkets(draft.markets)
      if (draft.benchmark) setBenchmark(draft.benchmark)
      if (typeof draft.watchlistInput === "string") setWatchlistInput(draft.watchlistInput)
      if (draft.manualRows?.length) setManualRows(draft.manualRows)
      if (draft.csvRows?.length) setCsvRows(draft.csvRows)
    } catch {
      window.localStorage.removeItem(localStorageKey)
    }
  }, [localStorageKey])

  useEffect(() => {
    const payload = {
      step,
      workspaceName,
      role,
      focus,
      importMode,
      markets,
      benchmark,
      watchlistInput,
      manualRows,
      csvRows,
    }
    window.localStorage.setItem(localStorageKey, JSON.stringify(payload))
  }, [benchmark, csvRows, focus, importMode, localStorageKey, manualRows, markets, role, step, watchlistInput, workspaceName])

  const watchlist = useMemo(
    () => watchlistInput.split(",").map((item) => item.trim()).filter(Boolean),
    [watchlistInput]
  )

  async function advanceTo(nextStep: OnboardingDraft["step"]) {
    const currentDraft = {
      ...createDefaultDraft(session.userId),
      step: nextStep,
      workspaceName: workspaceName.trim(),
      role,
      focus,
      portfolioImportMode: importMode === "none" ? null : importMode,
      scope: { markets, benchmark, watchlist },
      isSample: importMode === "sample",
      lastUpdated: new Date().toISOString(),
    } satisfies OnboardingDraft

    const workspacePatch = {
      workspaceName: workspaceName.trim() || "STRATOS Workspace",
      role,
      focus,
      markets,
      benchmark,
      watchlist,
      portfolioImportMode: importMode,
      sampleMode: importMode === "sample" || initialWorkspace.sampleMode,
      demoMode: initialWorkspace.demoMode,
      onboardingComplete: nextStep === "ready",
      portfolioReady:
        importMode === "sample" || manualRows.some((row) => row.ticker.trim()) || csvRows.length > 0,
    } satisfies Partial<WorkspaceState>

    setBusy("save")
    try {
      await persistDraft(currentDraft, workspacePatch)
      startTransition(() => {
        setStep(nextStep)
      })
    } finally {
      setBusy(null)
    }
  }

  async function commitPortfolio() {
    const normalizedManual = manualRows
      .filter((row) => row.ticker.trim())
      .map((row) => ({
        ticker: row.ticker.trim().toUpperCase(),
        quantity: Number(row.quantity),
        average_cost: Number(row.cost_basis),
        asset_class: row.asset_class || "equity",
      }))
      .filter((row) => !Number.isNaN(row.quantity) && row.quantity > 0 && !Number.isNaN(row.average_cost))

    const normalizedCsv = csvRows.map((row) => ({
      ticker: row.ticker.trim().toUpperCase(),
      quantity: Number(row.quantity),
      average_cost: Number(row.cost_basis),
      asset_class: row.asset_class || "equity",
    }))

    const positions =
      importMode === "sample"
        ? SAMPLE_PORTFOLIO.positions
        : importMode === "csv"
          ? normalizedCsv
          : normalizedManual

    if (importMode === "none" || positions.length === 0) {
      await advanceTo("scope")
      return
    }

    setBusy("portfolio")
    setNotice(null)
    try {
      await fetch(`${process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000"}/api/v2/portfolio/positions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "primary",
          benchmark,
          positions,
          constraints: SAMPLE_PORTFOLIO.constraints,
        }),
      })

      await advanceTo("scope")
      setNotice(importMode === "csv" && csvErrors.length > 0 ? `Imported ${positions.length} rows. ${csvErrors.length} row(s) skipped.` : null)
    } catch {
      setNotice("Portfolio import failed. You can still continue without a book.")
      await advanceTo("scope")
    } finally {
      setBusy(null)
    }
  }

  async function completeOnboarding() {
    setBusy("complete")
    await persistDraft(
      {
        step: "ready",
        workspaceName: workspaceName.trim() || "STRATOS Workspace",
        role,
        focus,
        portfolioImportMode: importMode === "none" ? null : importMode,
        scope: { markets, benchmark, watchlist },
        isSample: importMode === "sample",
        lastUpdated: new Date().toISOString(),
      },
      {
        workspaceName: workspaceName.trim() || "STRATOS Workspace",
        role,
        focus,
        markets,
        benchmark,
        watchlist,
        portfolioImportMode: importMode,
        onboardingComplete: true,
        portfolioReady:
          importMode === "sample" || manualRows.some((row) => row.ticker.trim()) || csvRows.length > 0,
        sampleMode: importMode === "sample" || initialWorkspace.sampleMode,
      }
    )
    router.push("/dashboard")
    router.refresh()
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-4 py-8 lg:px-8">
      <div className="space-y-2">
        <div className="font-mono-ui text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Onboarding
        </div>
        <h1 className="font-display text-4xl font-black tracking-[-0.06em] text-slate-950">
          Build your workspace.
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          One clean path: workspace identity, portfolio setup, scope, then Command Center.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {(["workspace", "portfolio", "scope", "ready"] as const).map((item, index) => (
          <div
            key={item}
            className={cn(
              "rounded-2xl border px-4 py-3 text-sm",
              item === step
                ? "border-primary/25 bg-primary/5 text-slate-950"
                : "border-border/70 bg-white/70 text-muted-foreground"
            )}
          >
            <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em]">{`0${index + 1}`}</div>
            <div className="mt-2 font-medium capitalize">{item}</div>
          </div>
        ))}
      </div>

      {step === "workspace" && (
        <Card>
          <CardHeader>
            <CardTitle>Create workspace</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <label className="text-sm font-medium text-slate-900">Workspace name</label>
              <Input value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} placeholder="STRATOS PM Desk" />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <ChoiceGrid
                label="Role"
                options={[
                  ["pm", "PM"],
                  ["analyst", "Analyst"],
                  ["cfo", "CFO"],
                  ["ceo", "CEO"],
                ]}
                value={role}
                onChange={(value) => setRole(value as WorkspaceState["role"])}
              />
              <ChoiceGrid
                label="Focus"
                options={[
                  ["portfolio", "Portfolio"],
                  ["macro", "Macro"],
                  ["research", "Research"],
                  ["events", "Events"],
                ]}
                value={focus}
                onChange={(value) => setFocus(value as WorkspaceState["focus"])}
              />
            </div>

            <div className="flex justify-end">
              <Button disabled={!workspaceName.trim() || busy !== null} onClick={() => advanceTo("portfolio")}>
                Continue <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "portfolio" && (
        <Card>
          <CardHeader>
            <CardTitle>Set up portfolio</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <ChoiceGrid
              label="Import mode"
              options={[
                ["manual", "Add manually"],
                ["csv", "Upload CSV"],
                ...(DEMO_MODE_ENABLED ? ([["sample", "Use sample book"]] as const) : []),
                ["none", "Skip for now"],
              ]}
              value={importMode}
              onChange={(value) => setImportMode(value as PortfolioImportMode)}
            />

            {importMode === "manual" && (
              <div className="grid gap-3">
                {manualRows.map((row, index) => (
                  <div key={index} className="grid gap-3 rounded-2xl border border-border/70 bg-muted/20 p-3 md:grid-cols-4">
                    <Input
                      placeholder="Ticker"
                      value={row.ticker}
                      onChange={(event) => {
                        const next = [...manualRows]
                        next[index] = { ...row, ticker: event.target.value }
                        setManualRows(next)
                      }}
                    />
                    <Input
                      placeholder="Quantity"
                      value={row.quantity}
                      onChange={(event) => {
                        const next = [...manualRows]
                        next[index] = { ...row, quantity: event.target.value }
                        setManualRows(next)
                      }}
                    />
                    <Input
                      placeholder="Cost basis"
                      value={row.cost_basis}
                      onChange={(event) => {
                        const next = [...manualRows]
                        next[index] = { ...row, cost_basis: event.target.value }
                        setManualRows(next)
                      }}
                    />
                    <Input
                      placeholder="Asset class"
                      value={row.asset_class}
                      onChange={(event) => {
                        const next = [...manualRows]
                        next[index] = { ...row, asset_class: event.target.value }
                        setManualRows(next)
                      }}
                    />
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    setManualRows((current) => [
                      ...current,
                      { ticker: "", quantity: "", cost_basis: "", asset_class: "equity" },
                    ])
                  }
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add row
                </Button>
              </div>
            )}

            {importMode === "csv" && (
              <div className="grid gap-3 rounded-2xl border border-border/70 bg-muted/15 p-4">
                <label className="inline-flex cursor-pointer items-center gap-3 rounded-2xl border border-dashed border-border/80 px-4 py-5 text-sm text-muted-foreground">
                  <Upload className="h-4 w-4" />
                  Upload CSV with ticker, quantity, cost_basis
                  <input
                    className="hidden"
                    type="file"
                    accept=".csv,text/csv"
                    onChange={async (event) => {
                      const file = event.target.files?.[0]
                      if (!file) {
                        return
                      }
                      const text = await file.text()
                      const parsed = parseCsv(text)
                      setCsvRows(parsed.rows)
                      setCsvErrors(parsed.failedRows)
                    }}
                  />
                </label>
                {csvRows.length > 0 && (
                  <div className="rounded-2xl border border-border/70 bg-white/75 p-3 text-sm text-slate-700">
                    Parsed {csvRows.length} row(s).
                  </div>
                )}
                {csvErrors.length > 0 && (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                    {csvErrors.map((item) => (
                      <div key={item}>{item}</div>
                    ))}
                  </div>
                )}
                <a
                  className="inline-flex items-center gap-2 text-sm font-medium text-sky-700"
                  download="stratos-portfolio-template.csv"
                  href={`data:text/csv;charset=utf-8,${encodeURIComponent("ticker,quantity,cost_basis,asset_class\nAAPL,100,185,equity\nBTC,0.25,65000,crypto\n")}`}
                >
                  <FileUp className="h-4 w-4" />
                  Download template
                </a>
              </div>
            )}

            {importMode === "sample" && (
              <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
                Sample workspace will load a PM-style book with AAPL, MSFT, NVDA, and BTC.
              </div>
            )}

            {notice ? <div className="text-sm text-amber-700">{notice}</div> : null}

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("workspace")}>
                Back
              </Button>
              <Button disabled={busy !== null} onClick={commitPortfolio}>
                {busy === "portfolio" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "scope" && (
        <Card>
          <CardHeader>
            <CardTitle>Choose scope</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-2">
              <div className="text-sm font-medium text-slate-900">Markets</div>
              <div className="flex flex-wrap gap-2">
                {["US", "India", "BTC", "Global"].map((market) => {
                  const active = markets.includes(market)
                  return (
                    <button
                      key={market}
                      type="button"
                      className={cn(
                        "rounded-full border px-4 py-2 text-sm transition-colors",
                        active
                          ? "border-primary/25 bg-primary/5 text-slate-950"
                          : "border-border/70 bg-white/75 text-muted-foreground"
                      )}
                      onClick={() =>
                        setMarkets((current) =>
                          current.includes(market)
                            ? current.filter((item) => item !== market)
                            : [...current, market]
                        )
                      }
                    >
                      {market}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-900">Benchmark</label>
                <Input value={benchmark} onChange={(event) => setBenchmark(event.target.value)} placeholder="SPY" />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium text-slate-900">Watchlist</label>
                <Input
                  value={watchlistInput}
                  onChange={(event) => setWatchlistInput(event.target.value)}
                  placeholder="AAPL, TSLA, India, BTC"
                />
              </div>
            </div>

            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("portfolio")}>
                Back
              </Button>
              <Button disabled={busy !== null || markets.length === 0} onClick={() => advanceTo("ready")}>
                Open workspace
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "ready" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              Your workspace is ready
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">
              Try this: “What do oil, sticky inflation, and BTC sentiment mean for my portfolio?”
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryItem label="Workspace" value={workspaceName.trim() || "STRATOS Workspace"} />
              <SummaryItem label="Role" value={role.toUpperCase()} />
              <SummaryItem label="Focus" value={focus} />
              <SummaryItem label="Benchmark" value={benchmark} />
            </div>
            <div className="flex justify-between">
              <Button variant="outline" onClick={() => setStep("scope")}>
                Back
              </Button>
              <Button disabled={busy !== null} onClick={completeOnboarding}>
                {busy === "complete" ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Open Command Center
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function ChoiceGrid({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: ReadonlyArray<readonly [string, string]>
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="grid gap-2">
      <div className="text-sm font-medium text-slate-900">{label}</div>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map(([optionValue, optionLabel]) => (
          <button
            key={optionValue}
            type="button"
            onClick={() => onChange(optionValue)}
            className={cn(
              "rounded-2xl border px-4 py-3 text-left text-sm transition-colors",
              value === optionValue
                ? "border-primary/25 bg-primary/5 text-slate-950"
                : "border-border/70 bg-white/75 text-muted-foreground"
            )}
          >
            {optionLabel}
          </button>
        ))}
      </div>
    </div>
  )
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-white/75 p-3">
      <div className="font-mono-ui text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-sm font-medium text-slate-950">{value}</div>
    </div>
  )
}
