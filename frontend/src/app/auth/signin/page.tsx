import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, ShieldCheck } from "lucide-react"

import { SignInForm } from "@/components/auth/signin-form"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  getAppSession,
  getEntryRedirectTarget,
  getResolvedWorkspaceState,
} from "@/lib/server/app-session"

function formatReturnTarget(target: string | undefined): string {
  if (!target || target === "/dashboard") {
    return "Command Center"
  }

  if (target.startsWith("/dashboard/portfolio")) {
    return "Portfolio"
  }

  if (target.startsWith("/dashboard/agent")) {
    return "Agent"
  }

  if (target.startsWith("/dashboard/events")) {
    return "Events"
  }

  if (target.startsWith("/dashboard/research")) {
    return "Research"
  }

  if (target.startsWith("/onboarding")) {
    return "Onboarding"
  }

  return "Workspace"
}

export default async function SignInPage({
  searchParams,
}: {
  searchParams?: { error?: string; return_url?: string }
}) {
  const session = await getAppSession()
  const workspace = await getResolvedWorkspaceState(session)
  const redirectTarget = getEntryRedirectTarget(session, workspace)
  if (redirectTarget) {
    redirect(redirectTarget)
  }

  const returnUrl = searchParams?.return_url || "/dashboard"
  const error = searchParams?.error ? "Authentication did not complete. Retry the local login flow." : null
  const returnTarget = formatReturnTarget(returnUrl)

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#f1f5f9_100%)]">
      <div className="mx-auto flex min-h-screen w-full max-w-3xl flex-col px-4 py-6 sm:px-6">
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/home"
            className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:border-primary/20 hover:text-slate-950"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>
          <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-white/80 px-4 py-2 text-sm text-slate-600 shadow-sm">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Secure workspace access
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center py-10">
          <Card className="w-full max-w-[460px] overflow-hidden border-border/70 bg-white/92 shadow-[0_30px_80px_-46px_rgba(15,23,42,0.38)]">
            <CardHeader className="border-b border-border/60 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.92))]">
              <div className="mb-3 inline-flex w-fit items-center gap-2 rounded-full border border-border/70 bg-slate-950 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-slate-50">
                STRATOS
              </div>
              <CardTitle className="text-[1.7rem] tracking-[-0.03em]">Log in to your workspace</CardTitle>
              <p className="text-sm leading-6 text-slate-600">
                Use your local STRATOS account and return to <span className="font-medium text-slate-950">{returnTarget}</span>.
              </p>
            </CardHeader>
            <CardContent className="grid gap-5 pt-5">
              {error ? (
                <div className="rounded-[1.15rem] border border-amber-200 bg-amber-50/95 px-4 py-3 text-sm leading-6 text-amber-950">
                  {error}
                </div>
              ) : null}
              <SignInForm />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
