import { NextResponse } from "next/server"

import {
  applyNoStore,
  clearAppCookies,
  getAppSession,
  getResolvedDraft,
  getResolvedWorkspaceState,
  toPublicSession,
} from "@/lib/server/app-session"

export async function GET() {
  const session = await getAppSession()
  const response = NextResponse.json({
    authenticated: Boolean(session),
    session: toPublicSession(session),
    workspace: await getResolvedWorkspaceState(session),
    draft: await getResolvedDraft(session),
  })

  if (!session) {
    clearAppCookies(response)
  }

  return applyNoStore(response)
}
