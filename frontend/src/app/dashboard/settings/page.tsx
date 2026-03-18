"use client"

import { useEffect, useState } from "react"
import {
  AlertCircle,
  Bell,
  Check,
  Globe,
  KeyRound,
  Loader2,
  Mail,
  Plus,
  Settings,
  Shield,
  Trash2,
  User,
  Users,
  PieChart,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

type Tab = "profile" | "workspace" | "members" | "alerts" | "access"

interface Workspace {
  id: string
  name: string
  owner_id: string
  benchmark: string
  markets: string[]
  member_count: number
  created_at: string
}

interface Member {
  workspace_id: string
  user_id: string
  email: string
  name: string
  role: string
  joined_at: string
}

interface WorkspaceSettings {
  name: string
  benchmark: string
  markets: string[]
}

interface AlertSettings {
  macro_pressure: boolean
  concentration_threshold: number
  event_urgency_min: number
  approval_notify: boolean
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("workspace")
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [userName, setUserName] = useState("")
  const [userEmail, setUserEmail] = useState("")
  const [workspaceSettings, setWorkspaceSettings] = useState<WorkspaceSettings>({
    name: "",
    benchmark: "SPY",
    markets: ["US", "India", "BTC"],
  })
  const [alertSettings, setAlertSettings] = useState<AlertSettings>({
    macro_pressure: true,
    concentration_threshold: 0.15,
    event_urgency_min: 0.7,
    approval_notify: true,
  })
  const [newMarket, setNewMarket] = useState("")
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviting, setInviting] = useState(false)
  const [workspaceId] = useState("default")
  const [currentUserId] = useState("current")

  useEffect(() => {
    loadWorkspace()
    loadMembers()
  }, [workspaceId])

  const loadWorkspace = async () => {
    try {
      const workspaces = await api.orchestrator.get("/workspaces", {
        params: { user_id: currentUserId },
      })
      if (workspaces.data?.length > 0) {
        setWorkspace(workspaces.data[0])
        setWorkspaceSettings({
          name: workspaces.data[0].name,
          benchmark: workspaces.data[0].benchmark,
          markets: workspaces.data[0].markets,
        })
      } else {
        const created = await api.orchestrator.post("/workspaces", {
          name: "My Workspace",
          owner_id: currentUserId,
          benchmark: "SPY",
          markets: ["US", "India", "BTC"],
        })
        setWorkspace(created.data)
        setWorkspaceSettings({
          name: created.data.name,
          benchmark: created.data.benchmark,
          markets: created.data.markets,
        })
      }
    } catch (error) {
      console.error("Failed to load workspace:", error)
    } finally {
      setLoading(false)
    }
  }

  const loadMembers = async () => {
    try {
      const membersResponse = await api.orchestrator.get(`/workspaces/${workspaceId}/members`, {
        params: { user_id: currentUserId },
      })
      setMembers(membersResponse.data || [])
    } catch (error) {
      console.error("Failed to load members:", error)
    }
  }

  const saveWorkspace = async () => {
    setSaving(true)
    try {
      await api.orchestrator.put(`/workspaces/${workspaceId}`, workspaceSettings, {
        params: { user_id: currentUserId },
      })
      await loadWorkspace()
    } catch (error) {
      console.error("Failed to save workspace:", error)
    } finally {
      setSaving(false)
    }
  }

  const saveAlerts = async () => {
    setSaving(true)
    try {
      await api.orchestrator.put(`/workspaces/${workspaceId}/alerts`, alertSettings, {
        params: { user_id: currentUserId },
      })
    } catch (error) {
      console.error("Failed to save alerts:", error)
    } finally {
      setSaving(false)
    }
  }

  const addMarket = async () => {
    if (!newMarket.trim()) return
    const updated = [...workspaceSettings.markets, newMarket.trim()]
    setWorkspaceSettings({ ...workspaceSettings, markets: updated })
    setNewMarket("")
  }

  const removeMarket = async (market: string) => {
    const updated = workspaceSettings.markets.filter((m) => m !== market)
    setWorkspaceSettings({ ...workspaceSettings, markets: updated })
  }

  const inviteMember = async () => {
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      await api.orchestrator.post(`/workspaces/${workspaceId}/members`, {
        user_id: `user_${Date.now()}`,
        email: inviteEmail,
        name: inviteEmail.split("@")[0],
        role: "member",
      })
      setInviteEmail("")
      await loadMembers()
    } catch (error) {
      console.error("Failed to invite member:", error)
    } finally {
      setInviting(false)
    }
  }

  const removeMember = async (userId: string) => {
    try {
      await api.orchestrator.delete(`/workspaces/${workspaceId}/members/${userId}`, {
        params: { user_id: currentUserId },
      })
      await loadMembers()
    } catch (error) {
      console.error("Failed to remove member:", error)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-black/30" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Settings</h1>
          <p className="text-sm text-black/50">Manage your workspace and preferences</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {[
          { id: "workspace" as Tab, label: "Workspace", icon: PieChart },
          { id: "profile" as Tab, label: "Profile", icon: User },
          { id: "members" as Tab, label: "Members", icon: Users },
          { id: "alerts" as Tab, label: "Alerts", icon: Bell },
          { id: "access" as Tab, label: "Access", icon: Shield },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors",
              activeTab === id ? "text-black border-b-2 border-black" : "text-black/50 hover:text-black/70"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
            {id === "members" && members.length > 0 && (
              <span className="ml-1 rounded-full bg-black/10 px-1.5 py-0.5 text-[10px]">
                {members.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="max-w-2xl">
        {activeTab === "workspace" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Workspace Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                    Workspace Name
                  </label>
                  <Input
                    value={workspaceSettings.name}
                    onChange={(e) => setWorkspaceSettings({ ...workspaceSettings, name: e.target.value })}
                    className="mt-1"
                    placeholder="My Workspace"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                    Benchmark
                  </label>
                  <Input
                    value={workspaceSettings.benchmark}
                    onChange={(e) => setWorkspaceSettings({ ...workspaceSettings, benchmark: e.target.value })}
                    className="mt-1"
                    placeholder="SPY"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                    Markets
                  </label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {workspaceSettings.markets.map((market) => (
                      <span
                        key={market}
                        className="inline-flex items-center gap-1 rounded-full border bg-white px-3 py-1 text-sm"
                      >
                        <Globe className="h-3 w-3" />
                        {market}
                        <button
                          onClick={() => removeMarket(market)}
                          className="ml-1 text-black/30 hover:text-black/60"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <Input
                      value={newMarket}
                      onChange={(e) => setNewMarket(e.target.value)}
                      placeholder="Add market..."
                      className="flex-1"
                      onKeyDown={(e) => e.key === "Enter" && addMarket()}
                    />
                    <Button size="sm" variant="outline" onClick={addMarket}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <Button onClick={saveWorkspace} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span className="ml-2">Save Changes</span>
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "profile" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Profile</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                    Name
                  </label>
                  <Input
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    className="mt-1"
                    placeholder="Your name"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                    Email
                  </label>
                  <Input
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    className="mt-1"
                    placeholder="your@email.com"
                    type="email"
                    disabled
                  />
                  <p className="text-xs text-black/30 mt-1">Email cannot be changed</p>
                </div>
                <Button onClick={saveWorkspace} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span className="ml-2">Save Profile</span>
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "members" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Invite Members</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="member@email.com"
                    className="flex-1"
                    type="email"
                    onKeyDown={(e) => e.key === "Enter" && inviteMember()}
                  />
                  <Button onClick={inviteMember} disabled={inviting}>
                    {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    <span className="ml-2">Invite</span>
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Workspace Members ({members.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {members.map((member) => (
                    <div
                      key={member.user_id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-black/[0.05]">
                          <User className="h-4 w-4 text-black/40" />
                        </div>
                        <div>
                          <div className="text-sm font-medium">{member.name}</div>
                          <div className="text-xs text-black/50">{member.email}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "text-xs px-2 py-0.5 rounded",
                            member.role === "owner" ? "bg-violet-100 text-violet-700" : "bg-black/5 text-black/50"
                          )}
                        >
                          {member.role}
                        </span>
                        {member.role !== "owner" && (
                          <button
                            onClick={() => removeMember(member.user_id)}
                            className="text-black/30 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "alerts" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Alert Preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <label className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Macro Pressure</div>
                    <div className="text-xs text-black/50">Alert on significant macro shifts</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={alertSettings.macro_pressure}
                    onChange={(e) => setAlertSettings({ ...alertSettings, macro_pressure: e.target.checked })}
                    className="h-4 w-4 rounded border-black/20"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Concentration Alert</div>
                    <div className="text-xs text-black/50">Alert when position exceeds threshold</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={alertSettings.concentration_threshold > 0}
                    onChange={(e) =>
                      setAlertSettings({ ...alertSettings, concentration_threshold: e.target.checked ? 0.15 : 0 })
                    }
                    className="h-4 w-4 rounded border-black/20"
                  />
                </label>
                {alertSettings.concentration_threshold > 0 && (
                  <div className="pl-4">
                    <label className="text-xs text-black/50">
                      Threshold: {(alertSettings.concentration_threshold * 100).toFixed(0)}%
                    </label>
                    <input
                      type="range"
                      min="5"
                      max="30"
                      value={alertSettings.concentration_threshold * 100}
                      onChange={(e) =>
                        setAlertSettings({ ...alertSettings, concentration_threshold: parseInt(e.target.value) / 100 })
                      }
                      className="w-full"
                    />
                  </div>
                )}
                <label className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Event Urgency</div>
                    <div className="text-xs text-black/50">Alert on high-urgency events</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={alertSettings.event_urgency_min > 0}
                    onChange={(e) =>
                      setAlertSettings({ ...alertSettings, event_urgency_min: e.target.checked ? 0.7 : 0 })
                    }
                    className="h-4 w-4 rounded border-black/20"
                  />
                </label>
                <label className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Approval Notifications</div>
                    <div className="text-xs text-black/50">Notify when approvals are needed</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={alertSettings.approval_notify}
                    onChange={(e) => setAlertSettings({ ...alertSettings, approval_notify: e.target.checked })}
                    className="h-4 w-4 rounded border-black/20"
                  />
                </label>
                <Button onClick={saveAlerts} disabled={saving}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  <span className="ml-2">Save Alerts</span>
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "access" && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Authentication</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-black/[0.05]">
                      <KeyRound className="h-5 w-5 text-black/40" />
                    </div>
                    <div>
                      <div className="text-sm font-medium">Local Authentication</div>
                      <div className="text-xs text-black/50">Email and password</div>
                    </div>
                  </div>
                  <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">Active</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Security</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Session Timeout</div>
                    <div className="text-xs text-black/50">Auto logout after inactivity</div>
                  </div>
                  <span className="text-sm text-black/50">8 hours</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium">Multi-factor Auth</div>
                    <div className="text-xs text-black/50">Add extra security layer</div>
                  </div>
                  <span className="text-sm text-black/30">Coming soon</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
