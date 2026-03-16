import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="surface-glow w-full max-w-xl rounded-[2rem] border border-border/70 bg-white/82 p-8 text-center backdrop-blur-sm">
        <div className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
          STRATOS
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-slate-950">
          This page is outside the current operating map.
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          The route you asked for does not exist in this workspace yet. Go back to Command and
          continue from a valid product surface.
        </p>
        <div className="mt-6 flex justify-center">
          <Button asChild>
            <Link href="/dashboard">Return to Command</Link>
          </Button>
        </div>
      </div>
    </main>
  )
}
