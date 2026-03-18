"use client"

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react"

export type HandoffType = "position" | "event" | "brief" | "market" | "thread" | null

export interface HandoffContext {
  type: HandoffType
  id: string | null
  reason?: string
  action?: string
  sourcePage?: string
  timestamp: number
  query?: string
}

interface HandoffContextValue extends HandoffContext {
  setHandoff: (context: Partial<HandoffContext>) => void
  clearHandoff: () => void
  parseFromUrl: () => void
}

const HandoffContext = createContext<HandoffContextValue | null>(null)

const SESSION_KEY = "stratos.handoff"
const DEFAULT_HANDOFF: HandoffContext = {
  type: null,
  id: null,
  timestamp: 0,
}

function parseUrlParams(): Partial<HandoffContext> {
  if (typeof window === "undefined") return {}

  const params = new URLSearchParams(window.location.search)
  const handoff = params.get("handoff")
  const id = params.get("id")
  const reason = params.get("reason")
  const action = params.get("action")
  const query = params.get("query")

  if (!handoff || !id) return {}

  const typeMap: Record<string, HandoffType> = {
    position: "position",
    event: "event",
    brief: "brief",
    market: "market",
    thread: "thread",
  }

  return {
    type: typeMap[handoff] ?? null,
    id,
    reason: reason ?? undefined,
    action: action ?? undefined,
    query: query ?? undefined,
    sourcePage: window.location.pathname,
    timestamp: Date.now(),
  }
}

export function HandoffProvider({ children, initialHandoff }: { children: ReactNode; initialHandoff?: Partial<HandoffContext> }) {
  const [handoff, setHandoffState] = useState<HandoffContext>(() => {
    if (typeof window !== "undefined") {
      try {
        const stored = sessionStorage.getItem(SESSION_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (Date.now() - parsed.timestamp < 30 * 60 * 1000) {
            return parsed
          }
        }
      } catch {
        // Ignore parse errors
      }

      const urlParams = parseUrlParams()
      if (Object.keys(urlParams).length > 0) {
        return { ...DEFAULT_HANDOFF, ...urlParams }
      }
    }
    return { ...DEFAULT_HANDOFF, ...initialHandoff }
  })

  useEffect(() => {
    if (handoff.type && handoff.id) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(handoff))
    } else {
      sessionStorage.removeItem(SESSION_KEY)
    }
  }, [handoff])

  const setHandoff = useCallback((context: Partial<HandoffContext>) => {
    setHandoffState((prev) => ({
      ...prev,
      ...context,
      timestamp: Date.now(),
    }))
  }, [])

  const clearHandoff = useCallback(() => {
    setHandoffState(DEFAULT_HANDOFF)
    sessionStorage.removeItem(SESSION_KEY)
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href)
      url.searchParams.delete("handoff")
      url.searchParams.delete("id")
      url.searchParams.delete("reason")
      url.searchParams.delete("action")
      url.searchParams.delete("query")
      window.history.replaceState({}, "", url.toString())
    }
  }, [])

  const parseFromUrl = useCallback(() => {
    const params = parseUrlParams()
    if (Object.keys(params).length > 0) {
      setHandoffState((prev) => ({
        ...DEFAULT_HANDOFF,
        ...params,
        sourcePage: params.sourcePage ?? prev.sourcePage,
      }))
    }
  }, [])

  return (
    <HandoffContext.Provider value={{ ...handoff, setHandoff, clearHandoff, parseFromUrl }}>
      {children}
    </HandoffContext.Provider>
  )
}

export function useHandoff(): HandoffContextValue {
  const context = useContext(HandoffContext)
  if (!context) {
    return {
      ...DEFAULT_HANDOFF,
      setHandoff: () => {},
      clearHandoff: () => {},
      parseFromUrl: () => {},
    }
  }
  return context
}

export function buildHandoffUrl(
  page: string,
  type: HandoffType,
  id: string,
  options?: { reason?: string; action?: string; query?: string }
): string {
  const params = new URLSearchParams()
  params.set("handoff", type ?? "")
  params.set("id", id)
  if (options?.reason) params.set("reason", options.reason)
  if (options?.action) params.set("action", options.action)
  if (options?.query) params.set("query", options.query)
  return `${page}?${params.toString()}`
}

export function useRoleHandoff() {
  const { setHandoff, clearHandoff, type, id } = useHandoff()

  const handoffToAgent = useCallback(
    (context: { position?: string; event?: string; brief?: string; market?: string; query?: string }) => {
      if (context.position) {
        setHandoff({
          type: "position",
          id: context.position,
          action: "analyze",
          query: context.query ?? `Analyze ${context.position} position`,
        })
      } else if (context.event) {
        setHandoff({
          type: "event",
          id: context.event,
          action: "scenario",
          query: context.query ?? `Analyze ${context.event} event impact`,
        })
      } else if (context.brief) {
        setHandoff({
          type: "brief",
          id: context.brief,
          action: "synthesize",
          query: context.query ?? `Synthesize research brief`,
        })
      } else if (context.market) {
        setHandoff({
          type: "market",
          id: context.market,
          action: "interpret",
          query: context.query ?? `Interpret ${context.market} market context`,
        })
      }
    },
    [setHandoff]
  )

  const handoffToPortfolio = useCallback(
    (position: string, reason?: string) => {
      setHandoff({
        type: "position",
        id: position,
        reason,
      })
    },
    [setHandoff]
  )

  const handoffToResearch = useCallback(
    (briefId: string, action?: string) => {
      setHandoff({
        type: "brief",
        id: briefId,
        action,
      })
    },
    [setHandoff]
  )

  const handoffToEvents = useCallback(
    (eventId: string, reason?: string) => {
      setHandoff({
        type: "event",
        id: eventId,
        reason,
      })
    },
    [setHandoff]
  )

  return {
    handoffToAgent,
    handoffToPortfolio,
    handoffToResearch,
    handoffToEvents,
    clearHandoff,
    currentType: type,
    currentId: id,
  }
}
