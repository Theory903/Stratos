import { NextRequest, NextResponse } from "next/server"

import { AppSession, SAMPLE_PORTFOLIO, createDefaultDraft, createDefaultWorkspaceState } from "@/lib/app-state"
import { setDraftCookie, setSessionCookie, setWorkspaceCookie } from "@/lib/server/app-session"

const DATA_FABRIC_V2 =
  (process.env.NEXT_PUBLIC_DATA_FABRIC_URL ?? "http://localhost:8000").replace(/\/+$/, "") + "/api/v2"

export async function GET(request: NextRequest) {
  const session: AppSession = {
    userId: "demo-user",
    name: "Sample PM",
    email: "demo@stratos.local",
    source: "demo",
    expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 12).toISOString(),
    createdAt: new Date().toISOString(),
  }

  const workspace = createDefaultWorkspaceState(session, {
    workspaceId: "demo-workspace",
    workspaceName: "STRATOS Demo Workspace",
    portfolioImportMode: "sample",
    portfolioReady: true,
    onboardingComplete: true,
    sampleMode: true,
    demoMode: true,
  })

  await fetch(`${DATA_FABRIC_V2}/portfolio/positions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(SAMPLE_PORTFOLIO),
  }).catch(() => null)

  const response = NextResponse.redirect(new URL("/dashboard", request.url))
  setSessionCookie(response, session)
  setWorkspaceCookie(response, workspace)
  setDraftCookie(response, createDefaultDraft(session.userId))
  return response
}
