"use client"

import Link from "next/link"
import { useEffect } from "react"

import { Button } from "@/components/ui/button"

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="surface-glow w-full max-w-xl rounded-[2rem] border border-border/70 bg-white/82 p-8 backdrop-blur-sm">
        <div className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
          STRATOS
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-slate-950">
          The workspace hit an unexpected fault.
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          This is a UI-level failure, not a strategic conclusion. Retry the view or step back to
          Command and continue from a clean state.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button onClick={reset}>Retry view</Button>
          <Button asChild variant="outline">
            <Link href="/dashboard">Go to Command</Link>
          </Button>
        </div>
      </div>
    </main>
  )
}
