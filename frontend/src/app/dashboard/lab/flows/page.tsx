import { redirect } from "next/navigation"

import { FlowCatalogView } from "@/components/flows/flow-catalog-view"
import { loadFlowCatalog } from "@/lib/server/flow-catalog"
import { getAppSession, getWorkspaceState } from "@/lib/server/app-session"

export default async function LabFlowsPage() {
  const session = await getAppSession()
  const workspace = await getWorkspaceState(session)
  if (!workspace || workspace.memberRole !== "owner") {
    redirect("/dashboard")
  }

  const data = await loadFlowCatalog()

  return <FlowCatalogView data={data} />
}
