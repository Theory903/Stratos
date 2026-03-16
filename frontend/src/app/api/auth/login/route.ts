import { NextRequest, NextResponse } from "next/server"

import { createDefaultDraft, createDefaultWorkspaceState } from "@/lib/app-state"
import { applyNoStore, getSafeReturnUrl, setDraftCookie, setSessionCookie, setWorkspaceCookie } from "@/lib/server/app-session"
import {
  createLocalSession,
  createLocalUser,
  findLocalUserByEmail,
  getLocalUserState,
  upsertLocalUserState,
  verifyLocalUser,
} from "@/lib/server/local-auth-store"

export async function POST(request: NextRequest) {
  const payload = (await request.json().catch(() => ({}))) as {
    intent?: "login" | "register"
    name?: string
    email?: string
    password?: string
    rememberMe?: boolean
    returnUrl?: string
  }

  const email = payload.email?.trim().toLowerCase() || ""
  const password = payload.password || ""
  const intent = payload.intent === "register" ? "register" : "login"
  const returnUrl = getSafeReturnUrl(payload.returnUrl ?? null)

  if (!email || !password) {
    return applyNoStore(NextResponse.json({ ok: false, error: "Email and password are required." }, { status: 400 }))
  }

  if (password.length < 8) {
    return applyNoStore(
      NextResponse.json({ ok: false, error: "Password must be at least 8 characters." }, { status: 400 })
    )
  }

  let user = null
  if (intent === "register") {
    const existing = await findLocalUserByEmail(email)
    if (existing) {
      return applyNoStore(NextResponse.json({ ok: false, error: "An account already exists for this email." }, { status: 409 }))
    }

    user = await createLocalUser({
      email,
      name: payload.name?.trim() || email.split("@")[0] || "STRATOS User",
      password,
    })
  } else {
    user = await verifyLocalUser(email, password)
    if (!user) {
      return applyNoStore(NextResponse.json({ ok: false, error: "Invalid email or password." }, { status: 401 }))
    }
  }

  const session = await createLocalSession({
    userId: user.id,
    email: user.email,
    name: user.name,
    rememberMe: payload.rememberMe === true,
  })

  const persisted = await getLocalUserState(user.id)
  const workspace =
    persisted?.workspace_json ??
    createDefaultWorkspaceState(session, {
      lastPath: returnUrl,
    })
  const draft = persisted?.draft_json ?? createDefaultDraft(user.id)

  await upsertLocalUserState(user.id, workspace, draft)

  const redirectTo = workspace.onboardingComplete
    ? returnUrl === "/dashboard" ? workspace.lastPath || "/dashboard" : returnUrl
    : "/onboarding/workspace"

  const response = NextResponse.json({ ok: true, redirectTo })
  setSessionCookie(response, session)
  setWorkspaceCookie(response, workspace)
  setDraftCookie(response, draft)
  return applyNoStore(response)
}
