"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Clock,
  Code2,
  Download,
  GitBranch,
  Loader2,
  MessageSquare,
  Play,
  RefreshCw,
  Settings,
  Sparkles,
  Workflow,
  Zap,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

interface WorkflowNode {
  id: string
  type: string
  label: string
  status: "idle" | "running" | "completed" | "error"
  duration_ms?: number
  inputs?: Record<string, any>
  outputs?: Record<string, any>
  error?: string
}

interface WorkflowEdge {
  from: string
  to: string
  label?: string
}

interface WorkflowTrace {
  run_id: string
  thread_id: string
  status: string
  started_at: string
  completed_at?: string
  duration_ms?: number
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  current_node?: string
  events: TraceEvent[]
}

interface TraceEvent {
  timestamp: string
  node_id: string
  type: string
  data: any
}

const DEFAULT_WORKFLOW: WorkflowTrace = {
  run_id: "",
  thread_id: "",
  status: "idle",
  started_at: "",
  nodes: [
    { id: "supervisor", type: "supervisor", label: "Supervisor", status: "idle" },
    { id: "market_analyst", type: "analyst", label: "Market Analyst", status: "idle" },
    { id: "risk_analyst", type: "analyst", label: "Risk Analyst", status: "idle" },
    { id: "portfolio_analyst", type: "analyst", label: "Portfolio Analyst", status: "idle" },
    { id: "trader", type: "trader", label: "Trader", status: "idle" },
    { id: "researcher", type: "researcher", label: "Researcher", status: "idle" },
    { id: "debate", type: "debate", label: "Debate", status: "idle" },
    { id: "resolver", type: "resolver", label: "Resolver", status: "idle" },
    { id: "output", type: "output", label: "Output", status: "idle" },
  ],
  edges: [
    { from: "supervisor", to: "market_analyst", label: "market query" },
    { from: "supervisor", to: "risk_analyst", label: "risk query" },
    { from: "supervisor", to: "portfolio_analyst", label: "portfolio query" },
    { from: "market_analyst", to: "debate" },
    { from: "risk_analyst", to: "debate" },
    { from: "portfolio_analyst", to: "debate" },
    { from: "debate", to: "resolver" },
    { from: "resolver", to: "trader", label: "action" },
    { from: "resolver", to: "researcher", label: "research" },
    { from: "researcher", to: "supervisor" },
    { from: "trader", to: "output" },
  ],
  events: [],
}

const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
  supervisor: { x: 400, y: 50 },
  market_analyst: { x: 150, y: 150 },
  risk_analyst: { x: 400, y: 150 },
  portfolio_analyst: { x: 650, y: 150 },
  researcher: { x: 650, y: 250 },
  debate: { x: 400, y: 250 },
  resolver: { x: 400, y: 350 },
  trader: { x: 250, y: 450 },
  output: { x: 400, y: 550 },
}

const NODE_COLORS: Record<string, string> = {
  supervisor: "bg-violet-500",
  analyst: "bg-blue-500",
  trader: "bg-emerald-500",
  researcher: "bg-amber-500",
  debate: "bg-orange-500",
  resolver: "bg-purple-500",
  output: "bg-slate-500",
}

type StudioTab = "workflow" | "prompts" | "tools" | "policies" | "traces" | "test"

export default function StudioPage() {
  const [activeTab, setActiveTab] = useState<StudioTab>("workflow")
  const [workflow, setWorkflow] = useState<WorkflowTrace>(DEFAULT_WORKFLOW)
  const [testQuery, setTestQuery] = useState("")
  const [testing, setTesting] = useState(false)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const canvasRef = useRef<SVGSVGElement>(null)

  const simulateRun = useCallback(async () => {
    setTesting(true)
    const runWorkflow = { ...DEFAULT_WORKFLOW, run_id: `run_${Date.now()}`, started_at: new Date().toISOString(), status: "running" }
    setWorkflow(runWorkflow)

    const nodeOrder = ["supervisor", "market_analyst", "risk_analyst", "portfolio_analyst", "debate", "resolver", "trader", "output"]

    for (let i = 0; i < nodeOrder.length; i++) {
      const nodeId = nodeOrder[i]
      await new Promise((r) => setTimeout(r, 800 + Math.random() * 400))

      setWorkflow((prev) => ({
        ...prev,
        current_node: nodeId,
        nodes: prev.nodes.map((n) =>
          n.id === nodeId ? { ...n, status: "completed" as const, duration_ms: 200 + Math.random() * 300 } : n
        ),
      }))
    }

    setWorkflow((prev) => ({
      ...prev,
      status: "completed",
      completed_at: new Date().toISOString(),
      current_node: undefined,
    }))
    setTesting(false)
  }, [])

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Studio</h1>
          <p className="text-sm text-black/50">Operator console for STRATOS agent configuration</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={simulateRun} disabled={testing}>
            {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            <span className="ml-2">Test Run</span>
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[
          { id: "workflow", label: "Workflow", icon: Workflow },
          { id: "prompts", label: "Prompts", icon: MessageSquare },
          { id: "tools", label: "Tools", icon: Code2 },
          { id: "policies", label: "Policies", icon: Settings },
          { id: "traces", label: "Traces", icon: Activity },
          { id: "test", label: "Test", icon: Zap },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id as StudioTab)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors",
              activeTab === id ? "text-black border-b-2 border-black" : "text-black/50 hover:text-black/70"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === "workflow" && (
          <WorkflowView
            workflow={workflow}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            canvasRef={canvasRef}
          />
        )}

        {activeTab === "prompts" && <PromptsView />}
        {activeTab === "tools" && <ToolsView />}
        {activeTab === "policies" && <PoliciesView />}
        {activeTab === "traces" && <TracesView workflow={workflow} />}
        {activeTab === "test" && (
          <TestView
            query={testQuery}
            setQuery={setTestQuery}
            testing={testing}
            onRun={simulateRun}
            workflow={workflow}
          />
        )}
      </div>
    </div>
  )
}

function WorkflowView({
  workflow,
  selectedNode,
  onSelectNode,
  canvasRef,
}: {
  workflow: WorkflowTrace
  selectedNode: string | null
  onSelectNode: (id: string | null) => void
  canvasRef: React.RefObject<SVGSVGElement>
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px] h-full">
      {/* Workflow Canvas */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              Agent Workflow (V5 LangGraph)
            </CardTitle>
            <div className="flex items-center gap-2 text-xs">
              {workflow.status === "running" && (
                <span className="flex items-center gap-1 text-blue-600">
                  <span className="h-2 w-2 rounded-full bg-blue-600 animate-pulse" />
                  Running
                </span>
              )}
              {workflow.status === "completed" && (
                <span className="flex items-center gap-1 text-emerald-600">
                  <CheckCircle2 className="h-3 w-3" />
                  Completed
                </span>
              )}
              {workflow.status === "error" && (
                <span className="flex items-center gap-1 text-red-600">
                  <AlertCircle className="h-3 w-3" />
                  Error
                </span>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative bg-black/[0.02] rounded-lg border overflow-hidden" style={{ height: 600 }}>
            <svg ref={canvasRef} width="100%" height="100%" className="absolute inset-0">
              {/* Grid */}
              <defs>
                <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-black/[0.05]" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />

              {/* Edges */}
              {workflow.edges.map((edge, i) => {
                const fromPos = NODE_POSITIONS[edge.from]
                const toPos = NODE_POSITIONS[edge.to]
                if (!fromPos || !toPos) return null

                const fromNode = workflow.nodes.find((n) => n.id === edge.from)
                const toNode = workflow.nodes.find((n) => n.id === edge.to)
                const isActive = workflow.current_node === edge.from || workflow.current_node === edge.to
                const isComplete = fromNode?.status === "completed" && toNode?.status === "completed"

                const midX = (fromPos.x + toPos.x) / 2
                const midY = (fromPos.y + toPos.y) / 2

                return (
                  <g key={i}>
                    <path
                      d={`M ${fromPos.x} ${fromPos.y + 25} Q ${midX} ${midY} ${toPos.x} ${toPos.y - 25}`}
                      fill="none"
                      stroke={isActive ? "#8b5cf6" : isComplete ? "#10b981" : "#d1d5db"}
                      strokeWidth={isActive ? 2 : 1}
                      strokeDasharray={isActive ? "5,5" : undefined}
                      className="transition-colors"
                    />
                    {edge.label && (
                      <text
                        x={midX}
                        y={midY}
                        textAnchor="middle"
                        className="text-[10px] fill-black/40"
                      >
                        {edge.label}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Nodes */}
              {workflow.nodes.map((node) => {
                const pos = NODE_POSITIONS[node.id]
                if (!pos) return null

                const isSelected = selectedNode === node.id
                const isActive = workflow.current_node === node.id
                const color = NODE_COLORS[node.type] || "bg-slate-500"

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x - 60}, ${pos.y - 25})`}
                    className="cursor-pointer"
                    onClick={() => onSelectNode(isSelected ? null : node.id)}
                  >
                    <rect
                      width="120"
                      height="50"
                      rx="8"
                      className={cn(
                        "fill-white stroke-2 transition-all",
                        isSelected ? "stroke-violet-500" : isActive ? "stroke-violet-400" : "stroke-black/10",
                        node.status === "completed" && "fill-emerald-50",
                        node.status === "error" && "fill-red-50"
                      )}
                      style={{
                        filter: isActive ? "drop-shadow(0 0 8px rgba(139, 92, 246, 0.4))" : undefined,
                      }}
                    />
                    <rect
                      width="120"
                      height="6"
                      rx="2"
                      className={cn(color, node.status === "running" && "animate-pulse")}
                    />
                    <text x="60" y="32" textAnchor="middle" className="text-xs font-medium fill-black">
                      {node.label}
                    </text>
                    {node.status === "running" && (
                      <circle cx="110" cy="10" r="4" className="fill-violet-500 animate-ping" />
                    )}
                    {node.status === "completed" && (
                      <CheckCircle2 x="100" y="32" className="h-4 w-4 fill-emerald-500 text-white" />
                    )}
                    {node.status === "error" && (
                      <AlertCircle x="100" y="32" className="h-4 w-4 fill-red-500 text-white" />
                    )}
                  </g>
                )
              })}
            </svg>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-3 text-xs text-black/50">
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded-full bg-violet-500" /> Supervisor
            </span>
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded-full bg-blue-500" /> Analyst
            </span>
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded-full bg-orange-500" /> Debate
            </span>
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded-full bg-emerald-500" /> Action
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Node Inspector */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Node Inspector</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedNode ? (
            <NodeInspector
              node={workflow.nodes.find((n) => n.id === selectedNode)!}
            />
          ) : (
            <div className="text-sm text-black/50 py-8 text-center">
              Select a node to inspect
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function NodeInspector({ node }: { node: WorkflowNode }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
          Node
        </label>
        <div className="text-sm font-medium mt-1">{node.label}</div>
      </div>
      <div>
        <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
          Status
        </label>
        <div className={cn(
          "text-sm mt-1",
          node.status === "completed" && "text-emerald-600",
          node.status === "running" && "text-violet-600",
          node.status === "error" && "text-red-600",
          node.status === "idle" && "text-black/50"
        )}>
          {node.status}
        </div>
      </div>
      {node.duration_ms && (
        <div>
          <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
            Duration
          </label>
          <div className="text-sm mt-1">{node.duration_ms.toFixed(0)}ms</div>
        </div>
      )}
      {node.inputs && Object.keys(node.inputs).length > 0 && (
        <div>
          <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
            Inputs
          </label>
          <pre className="mt-1 text-xs bg-black/[0.03] p-2 rounded overflow-auto max-h-32">
            {JSON.stringify(node.inputs, null, 2)}
          </pre>
        </div>
      )}
      {node.outputs && Object.keys(node.outputs).length > 0 && (
        <div>
          <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
            Outputs
          </label>
          <pre className="mt-1 text-xs bg-black/[0.03] p-2 rounded overflow-auto max-h-32">
            {JSON.stringify(node.outputs, null, 2)}
          </pre>
        </div>
      )}
      {node.error && (
        <div>
          <label className="text-xs font-medium text-red-600 uppercase tracking-wider">
            Error
          </label>
          <div className="text-sm text-red-600 mt-1">{node.error}</div>
        </div>
      )}
    </div>
  )
}

function PromptsView() {
  const prompts = [
    { id: "supervisor", name: "Supervisor", role: "Orchestrator" },
    { id: "market", name: "Market Analyst", role: "Specialist" },
    { id: "risk", name: "Risk Analyst", role: "Specialist" },
    { id: "portfolio", name: "Portfolio Analyst", role: "Specialist" },
    { id: "trader", name: "Trader", role: "Executor" },
    { id: "debate", name: "Debate", role: "Reasoning" },
    { id: "resolver", name: "Resolver", role: "Decision" },
  ]

  return (
    <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
      <div className="space-y-1">
        {prompts.map((prompt) => (
          <button
            key={prompt.id}
            className="w-full text-left p-3 rounded-lg border hover:bg-black/[0.02] transition-colors"
          >
            <div className="text-sm font-medium">{prompt.name}</div>
            <div className="text-xs text-black/50">{prompt.role}</div>
          </button>
        ))}
      </div>
      <Card>
        <CardContent className="p-4">
          <textarea
            className="w-full h-96 text-sm font-mono border rounded-lg p-4 resize-none focus:outline-none focus:ring-2 focus:ring-black/10"
            placeholder="Select a prompt to edit..."
            readOnly
          />
          <div className="flex items-center justify-between mt-3">
            <div className="text-xs text-black/50">
              Temperature: 0.7 · Max tokens: 2048
            </div>
            <Button size="sm">Save Changes</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function ToolsView() {
  const [tools, setTools] = useState([
    { id: "search", name: "Web Search", enabled: true },
    { id: "data", name: "Data Fabric", enabled: true },
    { id: "memory", name: "Memory", enabled: true },
    { id: "risk", name: "Risk Check", enabled: true },
    { id: "portfolio", name: "Portfolio", enabled: true },
    { id: "calendar", name: "Calendar", enabled: false },
    { id: "email", name: "Email", enabled: false },
    { id: "slack", name: "Slack", enabled: false },
  ])

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Agent Tools</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {tools.map((tool) => (
              <label
                key={tool.id}
                className="flex items-center gap-3 p-3 rounded-lg border hover:bg-black/[0.02] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={tool.enabled}
                  onChange={(e) =>
                    setTools(tools.map((t) => (t.id === tool.id ? { ...t, enabled: e.target.checked } : t)))
                  }
                  className="h-4 w-4 rounded border-black/20"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium">{tool.name}</div>
                  <div className="text-xs text-black/50">tools.{tool.id}</div>
                </div>
                <span
                  className={cn(
                    "text-xs px-2 py-0.5 rounded",
                    tool.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                  )}
                >
                  {tool.enabled ? "Enabled" : "Disabled"}
                </span>
              </label>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function PoliciesView() {
  const [policies, setPolicies] = useState({
    max_position_size: 0.15,
    max_portfolio_var: 0.05,
    min_confidence: 0.6,
    risk_off_multiplier: 0.5,
    max_leverage: 1.2,
    crisis_threshold_vix: 30,
  })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Risk Policies</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { key: "max_position_size", label: "Max Position Size", suffix: "%", divisor: 100 },
            { key: "max_portfolio_var", label: "Max Portfolio VaR", suffix: "%", divisor: 100 },
            { key: "min_confidence", label: "Min Confidence", suffix: "", divisor: 100 },
            { key: "risk_off_multiplier", label: "Risk-Off Multiplier", suffix: "x", divisor: 1 },
            { key: "max_leverage", label: "Max Leverage", suffix: "x", divisor: 1 },
            { key: "crisis_threshold_vix", label: "Crisis VIX Threshold", suffix: "", divisor: 1 },
          ].map(({ key, label, suffix, divisor }) => (
            <div key={key}>
              <label className="text-xs font-medium text-black/50">{label}</label>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="range"
                  min="0"
                  max={key === "crisis_threshold_vix" ? 50 : 1}
                  step="0.01"
                  value={(policies as any)[key]}
                  onChange={(e) =>
                    setPolicies({ ...policies, [key]: parseFloat(e.target.value) })
                  }
                  className="flex-1"
                />
                <span className="text-sm w-16 text-right">
                  {(policies as any)[key] / divisor}{suffix}
                </span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Active Policy</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-2 border-b">
              <span className="text-black/50">Mode</span>
              <span className="font-medium">NORMAL</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-black/50">De-risking</span>
              <span className="text-emerald-600">Inactive</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-black/50">Current VaR</span>
              <span className="font-medium">3.2%</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-black/50">Crisis Mode</span>
              <span className="text-slate-400">VIX below threshold</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function TracesView({ workflow }: { workflow: WorkflowTrace }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Execution Traces
          </CardTitle>
        </CardHeader>
        <CardContent>
          {workflow.status === "idle" ? (
            <div className="text-center py-12 text-sm text-black/50">
              Run a test to see traces
            </div>
          ) : (
            <div className="space-y-3">
              {workflow.nodes.map((node, i) => (
                <div
                  key={node.id}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-lg border",
                    node.status === "completed" && "bg-emerald-50 border-emerald-200",
                    node.status === "running" && "bg-violet-50 border-violet-200",
                    node.status === "idle" && "bg-black/[0.02]"
                  )}
                >
                  <div className="flex items-center justify-center h-6 w-6 rounded-full bg-black/[0.05]">
                    <span className="text-xs font-medium">{i + 1}</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{node.label}</div>
                    <div className="text-xs text-black/50">{node.id}</div>
                  </div>
                  <div className="text-right">
                    {node.status === "running" && (
                      <Loader2 className="h-4 w-4 animate-spin text-violet-600" />
                    )}
                    {node.status === "completed" && (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    )}
                    {node.duration_ms && (
                      <div className="text-xs text-black/50 mt-1">
                        {node.duration_ms.toFixed(0)}ms
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function TestView({
  query,
  setQuery,
  testing,
  onRun,
  workflow,
}: {
  query: string
  setQuery: (v: string) => void
  testing: boolean
  onRun: () => void
  workflow: WorkflowTrace
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_400px]">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Test Query</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a query to test the agent..."
            className="w-full h-32 p-3 text-sm border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-black/10"
          />
          <div className="flex items-center gap-2">
            <Button onClick={onRun} disabled={testing || !query.trim()}>
              {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              <span className="ml-2">Run Agent</span>
            </Button>
            <Button variant="outline">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {workflow.status !== "idle" && (
            <div className="mt-4 p-4 bg-black/[0.02] rounded-lg border">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="h-4 w-4 text-violet-600" />
                <span className="text-sm font-medium">Agent Response</span>
              </div>
              <p className="text-sm text-black/70">
                {testing
                  ? "Agent is processing your query..."
                  : workflow.status === "completed"
                  ? "Based on my analysis, I recommend reducing exposure to high-volatility positions and increasing allocation to defensive sectors. The current market regime suggests a risk-off posture."
                  : "Waiting for query..."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Live Metrics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-black/50 mb-1">Tokens Used</div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-semibold">{testing ? "1,247" : "0"}</span>
                <span className="text-xs text-black/50 mb-1">/ 4,096</span>
              </div>
              <div className="mt-1 h-2 bg-black/[0.05] rounded-full overflow-hidden">
                <div
                  className="h-full bg-violet-500 transition-all"
                  style={{ width: testing ? "30%" : "0%" }}
                />
              </div>
            </div>
            <div>
              <div className="text-xs text-black/50 mb-1">Confidence</div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-semibold">{testing ? "78%" : "--"}</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-black/50 mb-1">Nodes Processed</div>
              <div className="flex items-end gap-2">
                <span className="text-2xl font-semibold">
                  {workflow.nodes.filter((n) => n.status === "completed").length}
                </span>
                <span className="text-xs text-black/50 mb-1">/ {workflow.nodes.length}</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-black/50 mb-1">Duration</div>
              <div className="text-2xl font-semibold">
                {testing ? "2.4s" : workflow.status === "completed" ? "3.1s" : "--"}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
