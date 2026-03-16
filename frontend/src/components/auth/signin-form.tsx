"use client"

import { useEffect, useMemo, useState, useTransition } from "react"
import { Loader2, LogIn, ServerCrash, UserPlus } from "lucide-react"
import { useRouter, useSearchParams } from "next/navigation"

const REMEMBER_ME_KEY = "stratos-auth-remember-me"

export function SignInForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [intent, setIntent] = useState<"login" | "register">("login")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [rememberMe, setRememberMe] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const returnUrl = useMemo(() => searchParams?.get("return_url") || "/dashboard", [searchParams])

  useEffect(() => {
    const remembered = window.localStorage.getItem(REMEMBER_ME_KEY) === "1"
    setRememberMe(remembered)
  }, [])

  function persistRememberedValues(nextRememberMe: boolean) {
    if (nextRememberMe) {
      window.localStorage.setItem(REMEMBER_ME_KEY, "1")
      return
    }

    window.localStorage.removeItem(REMEMBER_ME_KEY)
  }

  function submit() {
    setError(null)
    startTransition(async () => {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          intent,
          name,
          email,
          password,
          rememberMe,
          returnUrl,
        }),
      }).catch(() => null)

      if (!response) {
        setError("Login failed. Retry in a moment.")
        return
      }

      const payload = (await response.json().catch(() => null)) as
        | { ok?: boolean; error?: string; redirectTo?: string }
        | null

      if (!response.ok || !payload?.ok || !payload.redirectTo) {
        setError(payload?.error || "Login failed. Check your details and retry.")
        return
      }

      persistRememberedValues(rememberMe)
      router.push(payload.redirectTo)
      router.refresh()
    })
  }

  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 gap-2 rounded-[1rem] bg-slate-100 p-1">
        <button
          type="button"
          onClick={() => setIntent("login")}
          className={`rounded-[0.85rem] px-3 py-2 text-sm font-medium transition-colors ${
            intent === "login" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"
          }`}
        >
          Log in
        </button>
        <button
          type="button"
          onClick={() => setIntent("register")}
          className={`rounded-[0.85rem] px-3 py-2 text-sm font-medium transition-colors ${
            intent === "register" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"
          }`}
        >
          Create account
        </button>
      </div>

      {intent === "register" ? (
        <label className="grid gap-1.5 text-sm text-slate-700">
          <span className="font-medium text-slate-900">Name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="h-11 rounded-xl border border-border/80 bg-white px-3 text-sm text-slate-950 outline-none ring-0 transition-colors focus:border-primary/35"
            placeholder="Abhishek"
          />
        </label>
      ) : null}

      <label className="grid gap-1.5 text-sm text-slate-700">
        <span className="font-medium text-slate-900">Email</span>
        <input
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          type="email"
          className="h-11 rounded-xl border border-border/80 bg-white px-3 text-sm text-slate-950 outline-none ring-0 transition-colors focus:border-primary/35"
          placeholder="you@workspace.com"
        />
      </label>

      <label className="grid gap-1.5 text-sm text-slate-700">
        <span className="font-medium text-slate-900">Password</span>
        <input
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          className="h-11 rounded-xl border border-border/80 bg-white px-3 text-sm text-slate-950 outline-none ring-0 transition-colors focus:border-primary/35"
          placeholder="At least 8 characters"
        />
      </label>

      <label className="flex items-center gap-3 rounded-[1rem] border border-border/70 bg-slate-50 px-3.5 py-3 text-sm text-slate-700">
        <input
          checked={rememberMe}
          onChange={(event) => setRememberMe(event.target.checked)}
          type="checkbox"
          className="h-4 w-4 rounded border-border/80 text-primary focus:ring-primary"
        />
        <span>
          <span className="block font-medium text-slate-900">Remember this browser</span>
          <span className="block text-xs text-slate-500">Keep your local session active longer on this device.</span>
        </span>
      </label>

      {error ? (
        <div className="rounded-[1rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <div className="mb-1 flex items-center gap-2 font-semibold">
            <ServerCrash className="h-4 w-4" />
            Authentication error
          </div>
          <div>{error}</div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={submit}
        disabled={isPending}
        className="inline-flex h-12 items-center justify-center gap-2 rounded-[1rem] bg-slate-950 px-4 text-sm font-semibold text-white transition-colors hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : intent === "login" ? <LogIn className="h-4 w-4" /> : <UserPlus className="h-4 w-4" />}
        {intent === "login" ? "Log in" : "Create account"}
      </button>
    </div>
  )
}
