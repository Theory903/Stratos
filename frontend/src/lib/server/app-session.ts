import "server-only"

import {
  createCipheriv,
  createDecipheriv,
  createHash,
  createHmac,
  randomBytes,
  timingSafeEqual,
} from "node:crypto"

import { cookies } from "next/headers"
import { NextResponse } from "next/server"

import {
  AppSession,
  COOKIE_NAMES,
  OnboardingDraft,
  WorkspaceState,
  createDefaultDraft,
  createDefaultWorkspaceState,
  isSafeDashboardPath,
} from "@/lib/app-state"
import { deleteLocalSession, getLocalSession, getLocalUserState } from "@/lib/server/local-auth-store"

let hasWarnedAboutLocalPreviewSecret = false

function getCookieSecret(): string {
  const secret =
    process.env.AUTH_COOKIE_SECRET ||
    process.env.FRONTEND_AUTH_COOKIE_SECRET ||
    process.env.JWT_SECRET

  if (secret) {
    return secret
  }

  const configuredAppUrl =
    process.env.APP_URL ||
    process.env.NEXT_PUBLIC_APP_URL ||
    "http://localhost:3000"
  const isLocalPreview =
    configuredAppUrl.includes("localhost") ||
    configuredAppUrl.includes("127.0.0.1") ||
    process.env.STRATOS_ALLOW_INSECURE_LOCAL_AUTH === "true"

  if (process.env.NODE_ENV === "production" && !isLocalPreview) {
    throw new Error("AUTH_COOKIE_SECRET must be set in production")
  }

  if (process.env.NODE_ENV === "production" && isLocalPreview && !hasWarnedAboutLocalPreviewSecret) {
    hasWarnedAboutLocalPreviewSecret = true
    console.warn(
      "AUTH_COOKIE_SECRET is not set. Falling back to the local preview secret because the app is running on localhost."
    )
  }

  return "stratos-dev-cookie-secret"
}

function signCookiePayload(payload: string): string {
  return createHmac("sha256", getCookieSecret()).update(payload).digest("base64url")
}

function getCookieEncryptionKey(): Buffer {
  return createHash("sha256").update(getCookieSecret()).digest()
}

function encodeCookieValue<T>(value: T): string {
  const iv = randomBytes(12)
  const cipher = createCipheriv("aes-256-gcm", getCookieEncryptionKey(), iv)
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(value), "utf8"), cipher.final()])
  const authTag = cipher.getAuthTag()

  return `v1.${iv.toString("base64url")}.${ciphertext.toString("base64url")}.${authTag.toString("base64url")}`
}

function decodeCookieValue<T>(value: string | undefined): T | null {
  if (!value) {
    return null
  }

  try {
    const [version, iv, ciphertext, authTag] = value.split(".")
    if (version === "v1" && iv && ciphertext && authTag) {
      const decipher = createDecipheriv("aes-256-gcm", getCookieEncryptionKey(), Buffer.from(iv, "base64url"))
      decipher.setAuthTag(Buffer.from(authTag, "base64url"))
      const decrypted = Buffer.concat([
        decipher.update(Buffer.from(ciphertext, "base64url")),
        decipher.final(),
      ]).toString("utf8")

      return JSON.parse(decrypted) as T
    }

    const [payload, signature] = value.split(".")
    if (payload && signature) {
      const expected = signCookiePayload(payload)
      if (!timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
        return null
      }
      return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as T
    }

    if (process.env.NODE_ENV !== "production") {
      return JSON.parse(Buffer.from(value, "base64url").toString("utf8")) as T
    }

    return null
  } catch {
    return null
  }
}

function getLegacyAppSession(): AppSession | null {
  const session = decodeCookieValue<AppSession>(cookies().get(COOKIE_NAMES.session)?.value)
  if (!session) {
    return null
  }

  if (new Date(session.expiresAt).getTime() <= Date.now()) {
    return null
  }

  return session
}

export async function getAppSession(): Promise<AppSession | null> {
  const rawCookie = cookies().get(COOKIE_NAMES.session)?.value
  if (!rawCookie) {
    return null
  }

  if (rawCookie.startsWith("dbs_")) {
    return getLocalSession(rawCookie)
  }

  return getLegacyAppSession()
}

function getCookieWorkspaceState(): WorkspaceState | null {
  return decodeCookieValue<WorkspaceState>(cookies().get(COOKIE_NAMES.workspace)?.value)
}

function getCookieOnboardingDraft(): OnboardingDraft | null {
  return decodeCookieValue<OnboardingDraft>(cookies().get(COOKIE_NAMES.draft)?.value)
}

export async function getWorkspaceState(session: AppSession | null = null): Promise<WorkspaceState | null> {
  const cookieValue = getCookieWorkspaceState()
  if (cookieValue) {
    return cookieValue
  }

  if (session?.source === "local") {
    const persisted = await getLocalUserState(session.userId)
    return persisted?.workspace_json ?? null
  }

  return null
}

export async function getOnboardingDraft(session: AppSession | null = null): Promise<OnboardingDraft | null> {
  const cookieValue = getCookieOnboardingDraft()
  if (cookieValue) {
    return cookieValue
  }

  if (session?.source === "local") {
    const persisted = await getLocalUserState(session.userId)
    return persisted?.draft_json ?? null
  }

  return null
}

export async function getResolvedWorkspaceState(session: AppSession | null): Promise<WorkspaceState | null> {
  if (!session) {
    return null
  }

  return (await getWorkspaceState(session)) ?? createDefaultWorkspaceState(session)
}

export async function getResolvedDraft(session: AppSession | null): Promise<OnboardingDraft | null> {
  if (!session) {
    return null
  }

  return (await getOnboardingDraft(session)) ?? createDefaultDraft(session.userId)
}

export function getEntryRedirectTarget(
  session: AppSession | null,
  workspace: WorkspaceState | null
): string | null {
  if (!session) {
    return null
  }

  if (!workspace || !workspace.onboardingComplete) {
    return "/onboarding/workspace"
  }

  if (isSafeDashboardPath(workspace.lastPath)) {
    return workspace.lastPath
  }

  return "/dashboard"
}

export function setSessionCookie(response: NextResponse, session: AppSession): void {
  const cookieValue =
    session.source === "local" && session.sessionId
      ? session.sessionId
      : encodeCookieValue(session)

  response.cookies.set(COOKIE_NAMES.session, cookieValue, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    priority: "high",
    expires: new Date(session.expiresAt),
  })
}

export function setWorkspaceCookie(response: NextResponse, workspace: WorkspaceState): void {
  response.cookies.set(COOKIE_NAMES.workspace, encodeCookieValue(workspace), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    priority: "medium",
    maxAge: 60 * 60 * 24 * 30,
  })
}

export function setDraftCookie(response: NextResponse, draft: OnboardingDraft): void {
  response.cookies.set(COOKIE_NAMES.draft, encodeCookieValue(draft), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
    priority: "medium",
    maxAge: 60 * 60 * 24 * 30,
  })
}

export function clearAppCookies(response: NextResponse): void {
  response.cookies.delete(COOKIE_NAMES.session)
  response.cookies.delete(COOKIE_NAMES.workspace)
  response.cookies.delete(COOKIE_NAMES.draft)
  response.cookies.delete(COOKIE_NAMES.authState)
}

export function applyNoStore(response: NextResponse): NextResponse {
  response.headers.set("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
  response.headers.set("Pragma", "no-cache")
  return response
}

export function decodeJwtPayload<T = Record<string, unknown>>(token: string): T | null {
  try {
    const payload = token.split(".")[1]
    if (!payload) {
      return null
    }
    return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as T
  } catch {
    return null
  }
}

export async function clearLocalSession(session: AppSession | null): Promise<void> {
  if (session?.source === "local" && session.sessionId) {
    await deleteLocalSession(session.sessionId)
  }
}

export function getSafeReturnUrl(candidate: string | null): string {
  if (!candidate) {
    return "/dashboard"
  }

  if (!candidate.startsWith("/")) {
    return "/dashboard"
  }

  if (candidate.startsWith("//") || candidate.includes("\\")) {
    return "/dashboard"
  }

  if (candidate.startsWith("/admin")) {
    return "/dashboard"
  }

  return candidate
}

export function toPublicSession(session: AppSession | null) {
  if (!session) {
    return null
  }

  return {
    userId: session.userId,
    name: session.name,
    email: session.email,
    source: session.source,
    expiresAt: session.expiresAt,
    createdAt: session.createdAt,
  }
}
