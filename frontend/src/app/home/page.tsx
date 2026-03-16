import { MarketingHomePage } from "@/components/marketing/homepage"
import { getAppSession, getEntryRedirectTarget, getResolvedWorkspaceState } from "@/lib/server/app-session"
import { getMarketPulseItems } from "@/lib/server/market-pulse"

export default async function PublicHomePage() {
  const session = await getAppSession()
  const workspace = await getResolvedWorkspaceState(session)
  const redirectTarget = getEntryRedirectTarget(session, workspace)
  const pulse = await getMarketPulseItems()
  return (
    <MarketingHomePage
      pulse={pulse}
      homeHref="/home"
      authenticated={Boolean(session)}
      workspaceHref={redirectTarget ?? "/dashboard"}
      userLabel={session?.name ?? null}
    />
  )
}
