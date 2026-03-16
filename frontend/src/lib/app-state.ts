export type WorkspaceRole = "pm" | "analyst" | "cfo" | "ceo"
export type WorkspaceFocus = "portfolio" | "macro" | "research" | "events"
export type MemberRole = "owner" | "member" | "viewer"
export type PortfolioImportMode = "manual" | "csv" | "sample" | "none"
export type OnboardingStep = "workspace" | "portfolio" | "scope" | "ready"
export type BillingPlan = "trial" | "pro" | "locked"

export interface AppSession {
  userId: string
  name: string
  email: string
  source: "local" | "demo"
  sessionId?: string
  keycloakToken?: string
  refreshToken?: string
  expiresAt: string
  refreshExpiresAt?: string
  createdAt: string
}

export interface WorkspaceState {
  workspaceId: string
  workspaceName: string
  role: WorkspaceRole
  focus: WorkspaceFocus
  memberRole: MemberRole
  markets: string[]
  benchmark: string
  watchlist: string[]
  portfolioImportMode: PortfolioImportMode
  portfolioReady: boolean
  onboardingComplete: boolean
  sampleMode: boolean
  demoMode: boolean
  plan: BillingPlan
  accessState: "full" | "read_only" | "restricted"
  lastPath: string
  updatedAt: string
}

export interface OnboardingDraft {
  userId: string
  step: OnboardingStep
  workspaceName: string
  role: WorkspaceRole
  focus: WorkspaceFocus
  portfolioImportMode: PortfolioImportMode | null
  scope: {
    markets: string[]
    benchmark: string | null
    watchlist: string[]
  }
  isSample: boolean
  lastUpdated: string
}

export interface PulseItem {
  label: string
  symbol: string
  value: string
  change: number
  freshness: "fresh" | "stale"
  timestamp: string | null
}

export const COOKIE_NAMES = {
  session: "stratos_session",
  workspace: "stratos_workspace",
  draft: "stratos_onboarding_draft",
  authState: "stratos_auth_state",
} as const

export const CORE_MARKETS = ["US", "India", "BTC"] as const

export const HOME_PULSE_CONFIG = [
  { label: "NIFTY", symbol: "INDEX:NIFTY50", fallbackValue: "23,408", fallbackChange: -1.11 },
  { label: "SENSEX", symbol: "INDEX:SENSEX", fallbackValue: "75,502", fallbackChange: -1.26 },
  { label: "BANKNIFTY", symbol: "INDEX:BANKNIFTY", fallbackValue: "54,413", fallbackChange: -1.22 },
  { label: "INDIA VIX", symbol: "INDEX:INDIAVIX", fallbackValue: "21.60", fallbackChange: -4.64 },
  { label: "US10Y", symbol: "MACRO:US10Y", fallbackValue: "4.58%", fallbackChange: 0.04 },
  { label: "DXY", symbol: "INDEX:DXY", fallbackValue: "104.8", fallbackChange: 0.22 },
  { label: "BTC", symbol: "X:BTCUSD", fallbackValue: "83,240", fallbackChange: -2.1 },
  { label: "GOLD", symbol: "X:XAUUSD", fallbackValue: "2,170", fallbackChange: 1.79 },
  { label: "CRUDE OIL", symbol: "CMD:CRUDE", fallbackValue: "73.8", fallbackChange: -3.71 },
] as const

export const SAMPLE_PORTFOLIO = {
  name: "primary",
  benchmark: "SPY",
  constraints: {
    max_single_name_weight: 0.6,
    max_crypto_weight: 0.35,
  },
  positions: [
    { ticker: "AAPL", quantity: 120, average_cost: 188, asset_class: "equity" },
    { ticker: "MSFT", quantity: 74, average_cost: 402, asset_class: "equity" },
    { ticker: "NVDA", quantity: 32, average_cost: 1110, asset_class: "equity" },
    { ticker: "X:BTCUSD", quantity: 0.8, average_cost: 68000, asset_class: "crypto" },
  ],
}

export function createDefaultDraft(userId: string): OnboardingDraft {
  return {
    userId,
    step: "workspace",
    workspaceName: "",
    role: "pm",
    focus: "portfolio",
    portfolioImportMode: null,
    scope: {
      markets: [...CORE_MARKETS],
      benchmark: "SPY",
      watchlist: [],
    },
    isSample: false,
    lastUpdated: new Date().toISOString(),
  }
}

export function createDefaultWorkspaceState(
  session: Pick<AppSession, "userId">,
  overrides: Partial<WorkspaceState> = {}
): WorkspaceState {
  const now = new Date().toISOString()
  return {
    workspaceId: `ws-${session.userId}`,
    workspaceName: "STRATOS Workspace",
    role: "pm",
    focus: "portfolio",
    memberRole: "owner",
    markets: [...CORE_MARKETS],
    benchmark: "SPY",
    watchlist: [],
    portfolioImportMode: "none",
    portfolioReady: false,
    onboardingComplete: false,
    sampleMode: false,
    demoMode: false,
    plan: "trial",
    accessState: "full",
    lastPath: "/dashboard",
    updatedAt: now,
    ...overrides,
  }
}

export function mergeWorkspaceState(
  current: WorkspaceState,
  patch: Partial<WorkspaceState>
): WorkspaceState {
  return {
    ...current,
    ...patch,
    updatedAt: new Date().toISOString(),
  }
}

export function isSafeDashboardPath(path: string | null | undefined): boolean {
  if (!path) {
    return false
  }

  return path.startsWith("/dashboard") && !path.startsWith("/dashboard/admin")
}
