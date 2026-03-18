import { describe, it, expect } from "vitest"
import {
  readableToolName,
  readableEngineName,
  summarizeToolText,
  formatPercent,
  formatSignedNumber,
  formatDurationSeconds,
  isRoleLens,
  isResponseMode,
  hasFinancePayload,
  metricToneFromScore,
  healthStatusTone,
  decisionToneToMetricTone,
  deriveProviderHealthStatus,
} from "./utils"
import type { AgentResponse } from "@/lib/api"

// ─── readableToolName ──────────────────────────────────────────────────────────

describe("readableToolName", () => {
  it("converts snake_case to Title Case", () => {
    expect(readableToolName("my_tool_name")).toBe("My Tool Name")
  })

  it("handles single word", () => {
    expect(readableToolName("tool")).toBe("Tool")
  })

  it("handles already-uppercase word", () => {
    expect(readableToolName("GET")).toBe("GET")
  })
})

// ─── readableEngineName ────────────────────────────────────────────────────────

describe("readableEngineName", () => {
  it("returns STRATOS runtime for undefined", () => {
    expect(readableEngineName(undefined)).toBe("STRATOS runtime")
  })

  it("maps langchain_v3 alias", () => {
    expect(readableEngineName("langchain_v3")).toBe("LangChain adaptive agent")
  })

  it("maps adaptive_agent alias", () => {
    expect(readableEngineName("adaptive_agent")).toBe("LangChain adaptive agent")
  })

  it("maps finance_council alias", () => {
    expect(readableEngineName("finance_council")).toBe("Finance council")
  })

  it("maps v4_graph alias", () => {
    expect(readableEngineName("v4_graph")).toBe("V4 graph runtime")
  })

  it("falls back to readableToolName for unknown values", () => {
    expect(readableEngineName("custom_engine")).toBe("Custom Engine")
  })
})

// ─── summarizeToolText ─────────────────────────────────────────────────────────

describe("summarizeToolText", () => {
  it("returns placeholder for undefined", () => {
    expect(summarizeToolText(undefined)).toBe("No additional output.")
  })

  it("returns short text unchanged", () => {
    const text = "Hello world"
    expect(summarizeToolText(text)).toBe(text)
  })

  it("truncates text longer than 280 chars with ellipsis", () => {
    const text = "a".repeat(300)
    const result = summarizeToolText(text)
    expect(result).toHaveLength(280)
    expect(result.endsWith("...")).toBe(true)
  })

  it("does not truncate text exactly at 280 chars", () => {
    const text = "b".repeat(280)
    expect(summarizeToolText(text)).toBe(text)
  })
})

// ─── formatPercent ─────────────────────────────────────────────────────────────

describe("formatPercent", () => {
  it("formats 0.5 as 50.00%", () => {
    expect(formatPercent(0.5)).toBe("50.00%")
  })

  it("respects custom digit count", () => {
    expect(formatPercent(0.333, 1)).toBe("33.3%")
  })

  it("handles negative values", () => {
    expect(formatPercent(-0.1)).toBe("-10.00%")
  })
})

// ─── formatSignedNumber ────────────────────────────────────────────────────────

describe("formatSignedNumber", () => {
  it("prefixes positive numbers with +", () => {
    expect(formatSignedNumber(3.5)).toBe("+3.50")
  })

  it("formats zero as +0.00", () => {
    expect(formatSignedNumber(0)).toBe("+0.00")
  })

  it("does not add + prefix to negative numbers", () => {
    expect(formatSignedNumber(-1.25)).toBe("-1.25")
  })
})

// ─── formatDurationSeconds ─────────────────────────────────────────────────────

describe("formatDurationSeconds", () => {
  it("shows seconds for values under 60", () => {
    expect(formatDurationSeconds(45)).toBe("45s")
  })

  it("shows minutes for values 60–3599", () => {
    expect(formatDurationSeconds(90)).toBe("2m")
  })

  it("shows hours for values 3600+", () => {
    expect(formatDurationSeconds(7200)).toBe("2h")
  })
})

// ─── isRoleLens ───────────────────────────────────────────────────────────────

describe("isRoleLens", () => {
  it("returns true for known role IDs", () => {
    expect(isRoleLens("auto")).toBe(true)
    expect(isRoleLens("ca")).toBe(true)
    expect(isRoleLens("pm")).toBe(true)
    expect(isRoleLens("cfa")).toBe(true)
    expect(isRoleLens("cmo")).toBe(true)
    expect(isRoleLens("general")).toBe(true)
  })

  it("returns false for unknown IDs", () => {
    expect(isRoleLens("unknown")).toBe(false)
    expect(isRoleLens("")).toBe(false)
  })

  it("returns false for null", () => {
    expect(isRoleLens(null)).toBe(false)
  })
})

// ─── isResponseMode ───────────────────────────────────────────────────────────

describe("isResponseMode", () => {
  it("returns true for known mode IDs", () => {
    expect(isResponseMode("direct")).toBe(true)
    expect(isResponseMode("research")).toBe(true)
    expect(isResponseMode("memo")).toBe(true)
    expect(isResponseMode("presentation")).toBe(true)
  })

  it("returns false for unknown IDs", () => {
    expect(isResponseMode("narrative")).toBe(false)
  })

  it("returns false for null", () => {
    expect(isResponseMode(null)).toBe(false)
  })
})

// ─── hasFinancePayload ────────────────────────────────────────────────────────

describe("hasFinancePayload", () => {
  const base = { answer: "text" } as unknown as AgentResponse

  it("returns false when no finance fields are present", () => {
    expect(hasFinancePayload(base)).toBe(false)
  })

  it("returns true when decision_packet is present", () => {
    expect(hasFinancePayload({ ...base, decision_packet: {} as never })).toBe(true)
  })

  it("returns true when analyst_signals has entries", () => {
    expect(hasFinancePayload({ ...base, analyst_signals: [{} as never] })).toBe(true)
  })

  it("returns false when analyst_signals is empty array", () => {
    expect(hasFinancePayload({ ...base, analyst_signals: [] })).toBe(false)
  })

  it("returns true when freshness_summary is present", () => {
    expect(hasFinancePayload({ ...base, freshness_summary: {} as never })).toBe(true)
  })
})

// ─── metricToneFromScore ──────────────────────────────────────────────────────

describe("metricToneFromScore", () => {
  it("returns positive for score >= 0.1", () => {
    expect(metricToneFromScore(0.1)).toBe("positive")
    expect(metricToneFromScore(0.5)).toBe("positive")
  })

  it("returns caution for score <= -0.1", () => {
    expect(metricToneFromScore(-0.1)).toBe("caution")
    expect(metricToneFromScore(-1)).toBe("caution")
  })

  it("returns neutral for values between -0.1 and 0.1", () => {
    expect(metricToneFromScore(0)).toBe("neutral")
    expect(metricToneFromScore(0.05)).toBe("neutral")
  })
})

// ─── healthStatusTone ─────────────────────────────────────────────────────────

describe("healthStatusTone", () => {
  it("returns positive for healthy/ready", () => {
    expect(healthStatusTone("healthy")).toBe("positive")
    expect(healthStatusTone("READY")).toBe("positive")
  })

  it("returns caution for degraded/stale/down", () => {
    expect(healthStatusTone("degraded")).toBe("caution")
    expect(healthStatusTone("down")).toBe("caution")
    expect(healthStatusTone("offline")).toBe("caution")
  })

  it("returns neutral for unknown statuses", () => {
    expect(healthStatusTone("unknown_status")).toBe("neutral")
  })
})

// ─── decisionToneToMetricTone ─────────────────────────────────────────────────

describe("decisionToneToMetricTone", () => {
  it("maps BUY to positive", () => {
    expect(decisionToneToMetricTone("BUY")).toBe("positive")
  })

  it("maps SELL to caution", () => {
    expect(decisionToneToMetricTone("SELL")).toBe("caution")
  })

  it("maps NO_TRADE to caution", () => {
    expect(decisionToneToMetricTone("NO_TRADE")).toBe("caution")
  })

  it("maps unknown to neutral", () => {
    expect(decisionToneToMetricTone("HOLD")).toBe("neutral")
  })
})

// ─── deriveProviderHealthStatus ───────────────────────────────────────────────

describe("deriveProviderHealthStatus", () => {
  it("returns unknown when no args are provided", () => {
    expect(deriveProviderHealthStatus(undefined, undefined)).toBe("unknown")
  })

  it("returns degraded when market is not ready", () => {
    const freshness = { market_ready: false, order_book_ready: true } as never
    expect(deriveProviderHealthStatus(freshness, [])).toBe("degraded")
  })

  it("returns degraded when any analyst signal freshness_ok is false", () => {
    const freshness = { market_ready: true, order_book_ready: true } as never
    const signals = [{ freshness_ok: false } as never]
    expect(deriveProviderHealthStatus(freshness, signals)).toBe("degraded")
  })

  it("returns healthy when freshness looks good and signals are fresh", () => {
    const freshness = { market_ready: true, order_book_ready: true } as never
    const signals = [{ freshness_ok: true } as never]
    expect(deriveProviderHealthStatus(freshness, signals)).toBe("healthy")
  })

  it("returns healthy when only freshness_summary is present", () => {
    const freshness = { market_ready: true, order_book_ready: true } as never
    expect(deriveProviderHealthStatus(freshness, undefined)).toBe("healthy")
  })
})
