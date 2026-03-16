import { NextResponse } from "next/server"

import { applyNoStore, clearAppCookies, getAppSession, toPublicSession } from "@/lib/server/app-session"

export async function GET() {
  const session = await getAppSession()
  if (!session) {
    const response = NextResponse.json({ ok: false, reason: "missing-session" }, { status: 401 })
    clearAppCookies(response)
    return applyNoStore(response)
  }

  return applyNoStore(NextResponse.json({ ok: true, session: toPublicSession(session) }))
}
