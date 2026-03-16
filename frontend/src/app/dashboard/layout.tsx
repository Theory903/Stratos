import { redirect } from "next/navigation"

import { DashboardFrame } from "@/components/layout/dashboard-frame"
import { getAppSession, getResolvedWorkspaceState } from "@/lib/server/app-session"
import { getMarketPulseItems } from "@/lib/server/market-pulse"

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getAppSession()
  const workspace = await getResolvedWorkspaceState(session)

  if (!session) {
    redirect("/auth/signin?return_url=/dashboard")
  }

  if (!workspace || !workspace.onboardingComplete) {
    redirect("/onboarding/workspace")
  }

  const pulse = await getMarketPulseItems()

  return (
    <DashboardFrame session={session} workspace={workspace} pulse={pulse}>
      {children}
    </DashboardFrame>
  )
}
