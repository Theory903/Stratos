export interface PlanStep {
  tool_name: string
  arguments: Record<string, unknown>
}

export interface ToolRun {
  tool: string
  status: "success" | "failed"
  result_summary?: string
  error?: string
}

/** A single item in an HITL approval gate emitted by the orchestrator */
export interface ApprovalRequest {
  approval_id: string
  /** Human-readable description of the action awaiting approval */
  reason: string
  required: boolean
}

/** Payload attached to a message when execution is interrupted for HITL */
export interface HitlInterrupt {
  run_id: string
  thread_id: string
  approvals: ApprovalRequest[]
  /** Has the user already acted on this gate? */
  resolved?: boolean
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  context?: { intent: string; role: string; mode?: string; engine?: string }
  memo?: import("@/lib/api").AgentResponse
  plan?: PlanStep[]
  status?: string
  toolRuns?: ToolRun[]
  metadata?: string[]
  /** Present when the run paused at an HITL approval gate */
  hitlInterrupt?: HitlInterrupt
}

export type RoleLens = "auto" | "general" | "ca" | "pm" | "cfa" | "cmo"
export type ResponseMode = "direct" | "research" | "memo" | "presentation"
