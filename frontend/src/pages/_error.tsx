import Link from "next/link"
import type { NextPageContext } from "next"

type ErrorPageProps = {
  statusCode?: number
}

function ErrorPage({ statusCode }: ErrorPageProps) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <div className="surface-glow w-full max-w-xl rounded-[2rem] border border-border/70 bg-white/82 p-8 text-center backdrop-blur-sm">
        <div className="font-mono-ui text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
          STRATOS
        </div>
        <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-slate-950">
          {statusCode ? `Error ${statusCode}` : "Unexpected error"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          The interface hit an unexpected state. Return to Command and retry from a clean flow.
        </p>
        <div className="mt-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white"
          >
            Return to Command
          </Link>
        </div>
      </div>
    </main>
  )
}

ErrorPage.getInitialProps = ({ res, err }: NextPageContext) => {
  const statusCode = res?.statusCode ?? err?.statusCode ?? 500
  return { statusCode }
}

export default ErrorPage
