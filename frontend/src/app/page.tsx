import { redirect } from "next/navigation"

import { MarketingHomePage } from "@/components/marketing/homepage"
import { getEntryRedirectTarget, getAppSession, getResolvedWorkspaceState } from "@/lib/server/app-session"
import { getMarketPulseItems } from "@/lib/server/market-pulse"

export default async function Home() {
    const session = await getAppSession()
    const workspace = await getResolvedWorkspaceState(session)
    const redirectTarget = getEntryRedirectTarget(session, workspace)

    if (redirectTarget) {
        redirect(redirectTarget)
    }

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
