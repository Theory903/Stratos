import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"

import { COOKIE_NAMES } from "@/lib/app-state"

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl
  const isProtected = pathname.startsWith("/dashboard") || pathname.startsWith("/onboarding")

  if (!isProtected) {
    return NextResponse.next()
  }

  const sessionCookie = request.cookies.get(COOKIE_NAMES.session)?.value
  if (sessionCookie) {
    return NextResponse.next()
  }

  const signInUrl = new URL("/auth/signin", request.url)
  signInUrl.searchParams.set("return_url", `${pathname}${search}`)
  return NextResponse.redirect(signInUrl)
}

export const config = {
  matcher: ["/dashboard/:path*", "/onboarding/:path*"],
}
