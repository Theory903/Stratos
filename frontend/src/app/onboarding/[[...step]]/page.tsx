import { redirect } from "next/navigation"

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard"
import {
  getAppSession,
  getEntryRedirectTarget,
  getResolvedDraft,
  getResolvedWorkspaceState,
} from "@/lib/server/app-session"

const VALID_STEPS = new Set(["workspace", "portfolio", "scope", "ready"])

export default async function OnboardingPage({
  params,
}: {
  params: { step?: string[] }
}) {
  const session = await getAppSession()
  const workspace = await getResolvedWorkspaceState(session)

  if (!session) {
    redirect("/auth/signin?return_url=/onboarding/workspace")
  }

  if (workspace?.onboardingComplete) {
    redirect(getEntryRedirectTarget(session, workspace) ?? "/dashboard")
  }

  const draft = await getResolvedDraft(session)
  const requestedStep = params.step?.[0]
  const initialStep =
    requestedStep && VALID_STEPS.has(requestedStep)
      ? (requestedStep as "workspace" | "portfolio" | "scope" | "ready")
      : draft?.step ?? "workspace"

  return (
    <OnboardingWizard
      session={session}
      initialDraft={draft!}
      initialWorkspace={workspace!}
      initialStep={initialStep}
    />
  )
}
