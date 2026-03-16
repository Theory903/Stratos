import { NextRequest, NextResponse } from "next/server"

import {
  OnboardingDraft,
  WorkspaceState,
  createDefaultDraft,
  createDefaultWorkspaceState,
  mergeWorkspaceState,
} from "@/lib/app-state"
import {
  getAppSession,
  getOnboardingDraft,
  getWorkspaceState,
  setDraftCookie,
  setWorkspaceCookie,
} from "@/lib/server/app-session"
import { upsertLocalUserState } from "@/lib/server/local-auth-store"

export async function GET() {
  const session = await getAppSession()
  return NextResponse.json({
    workspace: await getWorkspaceState(session),
    draft: await getOnboardingDraft(session),
  })
}

export async function PUT(request: NextRequest) {
  const session = await getAppSession()
  if (!session) {
    return NextResponse.json({ ok: false, reason: "unauthorized" }, { status: 401 })
  }

  const payload = (await request.json().catch(() => ({}))) as {
    workspace?: Partial<WorkspaceState>
    draft?: Partial<OnboardingDraft>
  }

  const workspace = mergeWorkspaceState(
    (await getWorkspaceState(session)) ?? createDefaultWorkspaceState(session),
    payload.workspace ?? {}
  )
  const draft = {
    ...((await getOnboardingDraft(session)) ?? createDefaultDraft(session.userId)),
    ...(payload.draft ?? {}),
    lastUpdated: new Date().toISOString(),
  } satisfies OnboardingDraft

  const response = NextResponse.json({ ok: true, workspace, draft })
  if (session.source === "local") {
    await upsertLocalUserState(session.userId, workspace, draft)
  }
  setWorkspaceCookie(response, workspace)
  setDraftCookie(response, draft)
  return response
}
