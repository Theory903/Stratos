"use client"

import { useEffect, useState } from "react"
import {
  FileText,
  Loader2,
  Plus,
  Search,
  Quote,
  ChevronRight,
  Upload,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { useHandoff } from "@/lib/handoff-context"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

interface Brief {
  id: string
  workspace_id: string
  title: string
  thesis: string
  status: string
  linked_positions: string[]
  linked_events: string[]
  evidence_count: number
  created_by: string | null
  created_at: string
  updated_at: string
}

interface Document {
  id: string
  workspace_id: string
  name: string
  mime_type: string | null
  size_bytes: number
  chunk_count: number
  indexed: boolean
  created_by: string | null
  created_at: string
}

interface RetrievalResult {
  chunk_id: string
  document_id: string
  document_name: string
  content: string
  citation: string
  score: number
}

interface RetrievalResponse {
  query: string
  results: RetrievalResult[]
  total: number
  processing_time_ms: number
}

type Tab = "briefs" | "documents" | "retrieval"

export default function ResearchPage() {
  const [activeTab, setActiveTab] = useState<Tab>("briefs")
  const [loading, setLoading] = useState(true)
  const [briefs, setBriefs] = useState<Brief[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedBrief, setSelectedBrief] = useState<Brief | null>(null)
  const [briefTitle, setBriefTitle] = useState("")
  const [briefThesis, setBriefThesis] = useState("")
  const [query, setQuery] = useState("")
  const [retrievalResults, setRetrievalResults] = useState<RetrievalResponse | null>(null)
  const [retrieving, setRetrieving] = useState(false)
  const [saving, setSaving] = useState(false)
  const [workspaceId] = useState("default")

  const { type, id: handoffId } = useHandoff()

  useEffect(() => {
    loadBriefs()
    loadDocuments()
  }, [workspaceId])

  const loadBriefs = async () => {
    try {
      const data = await api.research.listBriefs(workspaceId)
      setBriefs(data)
    } catch (error) {
      console.error("Failed to load briefs:", error)
      setBriefs([])
    } finally {
      setLoading(false)
    }
  }

  const loadDocuments = async () => {
    try {
      const data = await api.research.listDocuments(workspaceId)
      setDocuments(data)
    } catch (error) {
      console.error("Failed to load documents:", error)
      setDocuments([])
    }
  }

  const createBrief = async () => {
    if (!briefTitle.trim()) return
    setSaving(true)
    try {
      const newBrief = await api.research.createBrief({
        workspace_id: workspaceId,
        title: briefTitle,
        thesis: briefThesis,
        status: "draft",
      })
      if (newBrief) {
        setBriefs([newBrief, ...briefs])
        setSelectedBrief(newBrief)
        setBriefTitle("")
        setBriefThesis("")
      }
    } catch (error) {
      console.error("Failed to create brief:", error)
    } finally {
      setSaving(false)
    }
  }

  const updateBrief = async (briefId: string, data: Partial<Brief>) => {
    try {
      const updated = await api.research.updateBrief(briefId, data)
      if (updated) {
        setBriefs(briefs.map((b) => (b.id === briefId ? updated : b)))
        if (selectedBrief?.id === briefId) {
          setSelectedBrief(updated)
        }
      }
    } catch (error) {
      console.error("Failed to update brief:", error)
    }
  }

  const performRetrieval = async () => {
    if (!query.trim()) return
    setRetrieving(true)
    try {
      const results = await api.research.queryEvidence({
        query,
        workspace_id: workspaceId,
        top_k: 10,
      })
      setRetrievalResults(results)
    } catch (error) {
      console.error("Failed to retrieve:", error)
    } finally {
      setRetrieving(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      await api.research.uploadDocument(workspaceId, file)
      await loadDocuments()
    } catch (error) {
      console.error("Failed to upload document:", error)
    }
  }

  const addEvidenceToBrief = async (briefId: string, chunkId: string) => {
    try {
      await api.research.addEvidence({
        brief_id: briefId,
        chunk_id: chunkId,
      })
      await loadBriefs()
    } catch (error) {
      console.error("Failed to add evidence:", error)
    }
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold">Research</h1>
          <p className="text-sm text-black/50">Evidence, briefs, and thesis layer</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setActiveTab("retrieval")}>
            <Search className="h-4 w-4 mr-2" />
            Retrieval
          </Button>
          <Button size="sm" onClick={() => {
            setActiveTab("briefs")
          }}>
            <Plus className="h-4 w-4 mr-2" />
            New Brief
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(["briefs", "documents", "retrieval"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors",
              activeTab === tab
                ? "text-black border-b-2 border-black"
                : "text-black/50 hover:text-black/70"
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "briefs" && briefs.length > 0 && (
              <span className="ml-2 text-xs bg-black/10 px-1.5 py-0.5 rounded">
                {briefs.length}
              </span>
            )}
            {tab === "documents" && documents.length > 0 && (
              <span className="ml-2 text-xs bg-black/10 px-1.5 py-0.5 rounded">
                {documents.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === "briefs" && (
          <BriefsTab
            briefs={briefs}
            selectedBrief={selectedBrief}
            onSelectBrief={setSelectedBrief}
            onCreateBrief={createBrief}
            onUpdateBrief={updateBrief}
            briefTitle={briefTitle}
            setBriefTitle={setBriefTitle}
            briefThesis={briefThesis}
            setBriefThesis={setBriefThesis}
            saving={saving}
            loading={loading}
          />
        )}

        {activeTab === "documents" && (
          <DocumentsTab
            documents={documents}
            onUpload={handleFileUpload}
          />
        )}

        {activeTab === "retrieval" && (
          <RetrievalTab
            query={query}
            setQuery={setQuery}
            results={retrievalResults}
            retrieving={retrieving}
            onSearch={performRetrieval}
            onAddEvidence={addEvidenceToBrief}
            selectedBrief={selectedBrief}
          />
        )}
      </div>
    </div>
  )
}

function BriefsTab({
  briefs,
  selectedBrief,
  onSelectBrief,
  onCreateBrief,
  onUpdateBrief,
  briefTitle,
  setBriefTitle,
  briefThesis,
  setBriefThesis,
  saving,
  loading,
}: {
  briefs: Brief[]
  selectedBrief: Brief | null
  onSelectBrief: (b: Brief | null) => void
  onCreateBrief: () => void
  onUpdateBrief: (id: string, data: Partial<Brief>) => void
  briefTitle: string
  setBriefTitle: (v: string) => void
  briefThesis: string
  setBriefThesis: (v: string) => void
  saving: boolean
  loading: boolean
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[300px_1fr] h-full">
      {/* Brief List */}
      <div className="space-y-3">
        {/* New Brief Form */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">New Brief</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Brief title..."
              value={briefTitle}
              onChange={(e) => setBriefTitle(e.target.value)}
              className="text-sm"
            />
            <Button
              size="sm"
              className="w-full"
              onClick={onCreateBrief}
              disabled={!briefTitle.trim() || saving}
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Create
            </Button>
          </CardContent>
        </Card>

        {/* Brief List */}
        <div className="space-y-1">
          {loading ? (
            <div className="flex items-center justify-center py-8 text-sm text-black/50">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Loading...
            </div>
          ) : briefs.length === 0 ? (
            <div className="py-8 text-center text-sm text-black/50">
              No briefs yet
            </div>
          ) : (
            briefs.map((brief) => (
              <button
                key={brief.id}
                onClick={() => onSelectBrief(brief)}
                className={cn(
                  "w-full text-left p-3 rounded-lg border transition-colors",
                  selectedBrief?.id === brief.id
                    ? "bg-black/[0.05] border-black/20"
                    : "bg-white border-transparent hover:bg-black/[0.02]"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{brief.title}</div>
                    <div className="text-xs text-black/50 mt-0.5">
                      {brief.evidence_count} evidence · {brief.status}
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-black/30 shrink-0" />
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Brief Editor */}
      <Card>
        {selectedBrief ? (
          <>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="flex-1">
                  <input
                    type="text"
                    value={selectedBrief.title}
                    onChange={(e) =>
                      onUpdateBrief(selectedBrief.id, { title: e.target.value })
                    }
                    className="w-full bg-transparent text-sm font-semibold focus:outline-none"
                  />
                </CardTitle>
                <select
                  value={selectedBrief.status}
                  onChange={(e) =>
                    onUpdateBrief(selectedBrief.id, { status: e.target.value })
                  }
                  className="text-xs border rounded px-2 py-1"
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                  <option value="archived">Archived</option>
                </select>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                  Thesis
                </label>
                <textarea
                  value={selectedBrief.thesis}
                  onChange={(e) =>
                    onUpdateBrief(selectedBrief.id, { thesis: e.target.value })
                  }
                  placeholder="Write your thesis here..."
                  className="w-full mt-1 p-3 text-sm border rounded-lg resize-none h-32 focus:outline-none focus:ring-2 focus:ring-black/10"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-black/50 uppercase tracking-wider">
                  Linked Positions
                </label>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedBrief.linked_positions.map((p) => (
                    <span
                      key={p}
                      className="text-xs bg-black/[0.05] px-2 py-1 rounded"
                    >
                      {p}
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder="Add..."
                    className="text-xs border-dashed border rounded px-2 py-1 w-20"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && e.currentTarget.value) {
                        onUpdateBrief(selectedBrief.id, {
                          linked_positions: [
                            ...selectedBrief.linked_positions,
                            e.currentTarget.value,
                          ],
                        })
                        e.currentTarget.value = ""
                      }
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </>
        ) : (
          <CardContent className="flex items-center justify-center h-64 text-sm text-black/50">
            Select a brief to edit or create a new one
          </CardContent>
        )}
      </Card>
    </div>
  )
}

function DocumentsTab({
  documents,
  onUpload,
}: {
  documents: Document[]
  onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <div className="space-y-4">
      {/* Upload */}
      <Card>
        <CardContent className="p-4">
          <label className="flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-8 cursor-pointer hover:bg-black/[0.02] transition-colors">
            <Upload className="h-8 w-8 text-black/30 mb-2" />
            <span className="text-sm text-black/50">Click to upload documents</span>
            <span className="text-xs text-black/30 mt-1">PDF, TXT, MD supported</span>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.txt,.md,.html,.json"
              onChange={onUpload}
            />
          </label>
        </CardContent>
      </Card>

      {/* Document List */}
      <div className="grid gap-2">
        {documents.length === 0 ? (
          <div className="text-center py-12 text-sm text-black/50">
            No documents uploaded
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 p-3 border rounded-lg"
            >
              <FileText className="h-5 w-5 text-black/30" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{doc.name}</div>
                <div className="text-xs text-black/50">
                  {(doc.size_bytes / 1024).toFixed(1)} KB · {doc.chunk_count} chunks
                </div>
              </div>
              <span
                className={cn(
                  "text-xs px-2 py-0.5 rounded",
                  doc.indexed ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                )}
              >
                {doc.indexed ? "Indexed" : "Pending"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function RetrievalTab({
  query,
  setQuery,
  results,
  retrieving,
  onSearch,
  onAddEvidence,
  selectedBrief,
}: {
  query: string
  setQuery: (v: string) => void
  results: RetrievalResponse | null
  retrieving: boolean
  onSearch: () => void
  onAddEvidence: (briefId: string, chunkId: string) => void
  selectedBrief: Brief | null
}) {
  return (
    <div className="space-y-4">
      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ask a question about your research..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearch()}
              className="flex-1"
            />
            <Button onClick={onSearch} disabled={retrieving || !query.trim()}>
              {retrieving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </div>
          {results && (
            <div className="mt-2 text-xs text-black/50">
              Found {results.total} results in {results.processing_time_ms.toFixed(0)}ms
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {results && (
        <div className="space-y-3">
          {results.results.map((result) => (
            <Card key={result.chunk_id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="text-xs text-black/50 mb-1">
                      {result.document_name} · {(result.score * 100).toFixed(0)}% match
                    </div>
                    <p className="text-sm">{result.content}</p>
                    <div className="text-xs text-black/30 mt-2">
                      {result.citation}
                    </div>
                  </div>
                  {selectedBrief && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAddEvidence(selectedBrief.id, result.chunk_id)}
                    >
                      <Quote className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!results && !retrieving && (
        <div className="text-center py-12 text-sm text-black/50">
          Enter a query to search your research documents
        </div>
      )}
    </div>
  )
}
