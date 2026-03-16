import { NextResponse } from "next/server"

import { applyNoStore, clearAppCookies, clearLocalSession, getAppSession } from "@/lib/server/app-session"

export async function GET(request: Request) {
  const session = await getAppSession()
  await clearLocalSession(session)

  const response = NextResponse.redirect(new URL("/auth/signin", request.url))
  clearAppCookies(response)
  return applyNoStore(response)
}
