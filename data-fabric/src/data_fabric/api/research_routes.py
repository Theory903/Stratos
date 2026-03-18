"""Research and RAG API routes for documents, briefs, evidence, and retrieval."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

router = APIRouter(prefix="/research", tags=["Research"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _encode_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536


class BriefCreate(BaseModel):
    workspace_id: str
    title: str
    thesis: str = ""
    status: str = "draft"
    linked_positions: list[str] = Field(default_factory=list)
    linked_events: list[str] = Field(default_factory=list)
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BriefUpdate(BaseModel):
    title: str | None = None
    thesis: str | None = None
    status: str | None = None
    linked_positions: list[str] | None = None
    linked_events: list[str] | None = None
    metadata: dict[str, Any] | None = None


class BriefResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    thesis: str
    status: str
    linked_positions: list[str]
    linked_events: list[str]
    evidence_count: int
    created_by: str | None
    created_at: str
    updated_at: str
    metadata: dict[str, Any]


class DocumentResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    mime_type: str | None
    size_bytes: int
    chunk_count: int
    indexed: bool
    created_by: str | None
    created_at: str
    metadata: dict[str, Any]


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]


class EvidenceCreate(BaseModel):
    chunk_id: str
    brief_id: str
    note: str | None = None


class EvidenceResponse(BaseModel):
    id: str
    brief_id: str
    chunk_id: str
    content: str
    citation: str
    relevance_score: float
    note: str | None
    created_at: str


class RetrievalQuery(BaseModel):
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 10
    workspace_id: str


class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    citation: str
    score: float
    metadata: dict[str, Any]


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalResult]
    total: int
    processing_time_ms: float


class ResearchRouter:
    """In-memory research store with mock embeddings for development."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._documents: dict[str, dict] = {}
        self._chunks: dict[str, dict] = {}
        self._briefs: dict[str, dict] = {}
        self._evidence: dict[str, dict] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._initialized = True

    def _generate_mock_embedding(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding based on text hash."""
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        import random
        random.seed(hash_val)
        return [random.uniform(-1, 1) for _ in range(EMBEDDING_DIMENSIONS)]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b + 1e-8)

    async def _get_embedding(self, text: str) -> list[float]:
        """Get embedding for text, using OpenAI if available."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return self._generate_mock_embedding(text)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current = ""
        current_tokens = 0

        for sentence in sentences:
            words = sentence.split()
            current_tokens += len(words)
            current += sentence + " "

            if current_tokens >= chunk_size:
                chunks.append(current.strip())
                words_in_current = current.split()
                overlap_words = " ".join(words_in_current[-overlap:] if len(words_in_current) > overlap else words_in_current)
                current = overlap_words + " "
                current_tokens = len(overlap_words.split())

        if current.strip():
            chunks.append(current.strip())

        return chunks

    async def create_document(
        self,
        workspace_id: str,
        file: UploadFile,
        user_id: str | None = None,
    ) -> DocumentResponse:
        """Create document, chunk, embed, store."""
        doc_id = str(uuid4())
        now = _encode_datetime(_utcnow())

        content = await file.read()
        text = content.decode("utf-8", errors="replace")

        chunks = self._chunk_text(text)
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid4())
            embedding = await self._get_embedding(chunk)

            self._chunks[chunk_id] = {
                "id": chunk_id,
                "document_id": doc_id,
                "chunk_index": i,
                "content": chunk,
                "metadata": {"page": i // 10 + 1, "section": f"chunk_{i}"},
                "created_at": now,
            }
            self._embeddings[chunk_id] = embedding
            chunk_ids.append(chunk_id)

        self._documents[doc_id] = {
            "id": doc_id,
            "workspace_id": workspace_id,
            "name": file.filename or "unknown",
            "mime_type": file.content_type,
            "size_bytes": len(content),
            "chunk_count": len(chunks),
            "indexed": True,
            "created_by": user_id,
            "created_at": now,
            "metadata": {},
        }

        return DocumentResponse(**self._documents[doc_id])

    def list_documents(self, workspace_id: str, limit: int = 50, offset: int = 0) -> list[DocumentResponse]:
        """List documents for workspace."""
        docs = [d for d in self._documents.values() if d["workspace_id"] == workspace_id]
        docs.sort(key=lambda d: d["created_at"], reverse=True)
        return [DocumentResponse(**d) for d in docs[offset : offset + limit]]

    def get_document(self, document_id: str) -> DocumentResponse | None:
        """Get document with chunks."""
        doc = self._documents.get(document_id)
        if not doc:
            return None
        return DocumentResponse(**doc)

    def get_document_chunks(self, document_id: str) -> list[ChunkResponse]:
        """Get all chunks for a document."""
        chunks = [c for c in self._chunks.values() if c["document_id"] == document_id]
        chunks.sort(key=lambda c: c["chunk_index"])
        return [ChunkResponse(**c) for c in chunks]

    def create_brief(self, data: BriefCreate) -> BriefResponse:
        """Create new research brief."""
        brief_id = str(uuid4())
        now = _encode_datetime(_utcnow())

        brief = {
            "id": brief_id,
            "workspace_id": data.workspace_id,
            "title": data.title,
            "thesis": data.thesis,
            "status": data.status,
            "linked_positions": data.linked_positions,
            "linked_events": data.linked_events,
            "evidence_count": 0,
            "created_by": data.created_by,
            "created_at": now,
            "updated_at": now,
            "metadata": data.metadata,
        }

        self._briefs[brief_id] = brief
        return BriefResponse(**brief, evidence_count=0)

    def list_briefs(
        self,
        workspace_id: str,
        status: str | None = None,
        linked_position: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BriefResponse]:
        """List briefs with filtering."""
        briefs = [b for b in self._briefs.values() if b["workspace_id"] == workspace_id]

        if status:
            briefs = [b for b in briefs if b["status"] == status]
        if linked_position:
            briefs = [b for b in briefs if linked_position in b["linked_positions"]]

        briefs.sort(key=lambda b: b["updated_at"], reverse=True)
        return [BriefResponse(**b, evidence_count=self._count_evidence(b["id"])) for b in briefs[offset : offset + limit]]

    def _count_evidence(self, brief_id: str) -> int:
        return len([e for e in self._evidence.values() if e["brief_id"] == brief_id])

    def get_brief(self, brief_id: str) -> BriefResponse | None:
        """Get brief with evidence and citations."""
        brief = self._briefs.get(brief_id)
        if not brief:
            return None
        return BriefResponse(**brief, evidence_count=self._count_evidence(brief_id))

    def update_brief(self, brief_id: str, data: BriefUpdate) -> BriefResponse | None:
        """Update brief thesis, status, links."""
        brief = self._briefs.get(brief_id)
        if not brief:
            return None

        now = _encode_datetime(_utcnow())
        if data.title is not None:
            brief["title"] = data.title
        if data.thesis is not None:
            brief["thesis"] = data.thesis
        if data.status is not None:
            brief["status"] = data.status
        if data.linked_positions is not None:
            brief["linked_positions"] = data.linked_positions
        if data.linked_events is not None:
            brief["linked_events"] = data.linked_events
        if data.metadata is not None:
            brief["metadata"] = data.metadata
        brief["updated_at"] = now

        return BriefResponse(**brief, evidence_count=self._count_evidence(brief_id))

    async def query_evidence(
        self,
        query: RetrievalQuery,
    ) -> RetrievalResponse:
        """Hybrid retrieval: vector + keyword, reranked."""
        import time
        start = time.time()

        query_embedding = await self._get_embedding(query.query)

        similarities = []
        for chunk_id, embedding in self._embeddings.items():
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue

            doc = self._documents.get(chunk["document_id"])
            if not doc or doc["workspace_id"] != query.workspace_id:
                continue

            score = self._cosine_similarity(query_embedding, embedding)

            if query.filters.get("positions"):
                positions = query.filters["positions"]
                if isinstance(positions, list):
                    in_doc = any(p.lower() in chunk["content"].lower() for p in positions)
                    if not in_doc and query.filters.get("strict_positions"):
                        continue
                    score *= 1.2 if in_doc else 1.0

            similarities.append((chunk_id, score))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[: query.top_k]

        results = []
        for chunk_id, score in top_results:
            chunk = self._chunks[chunk_id]
            doc = self._documents[chunk["document_id"]]

            citation = f"{doc['name']}, chunk {chunk['chunk_index'] + 1}"

            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    document_id=doc["id"],
                    document_name=doc["name"],
                    content=chunk["content"],
                    citation=citation,
                    score=score,
                    metadata=chunk["metadata"],
                )
            )

        processing_time = (time.time() - start) * 1000

        return RetrievalResponse(
            query=query.query,
            results=results,
            total=len(results),
            processing_time_ms=processing_time,
        )

    def add_evidence(self, brief_id: str, chunk_id: str, note: str | None = None) -> EvidenceResponse | None:
        """Add evidence citation to brief."""
        brief = self._briefs.get(brief_id)
        chunk = self._chunks.get(chunk_id)
        if not brief or not chunk:
            return None

        evidence_id = str(uuid4())
        now = _encode_datetime(_utcnow())
        doc = self._documents.get(chunk["document_id"])

        evidence = {
            "id": evidence_id,
            "brief_id": brief_id,
            "chunk_id": chunk_id,
            "content": chunk["content"],
            "citation": f"{doc['name'] if doc else 'unknown'}, chunk {chunk['chunk_index'] + 1}",
            "relevance_score": 1.0,
            "note": note,
            "created_at": now,
        }

        self._evidence[evidence_id] = evidence
        return EvidenceResponse(**evidence)

    def get_evidence(self, evidence_id: str) -> EvidenceResponse | None:
        """Get evidence with full context."""
        evidence = self._evidence.get(evidence_id)
        if not evidence:
            return None
        return EvidenceResponse(**evidence)

    def get_brief_evidence(self, brief_id: str) -> list[EvidenceResponse]:
        """Get all evidence for a brief."""
        evidence_list = [e for e in self._evidence.values() if e["brief_id"] == brief_id]
        evidence_list.sort(key=lambda e: e["created_at"])
        return [EvidenceResponse(**e) for e in evidence_list]


_research_router: ResearchRouter | None = None


def get_research_router() -> ResearchRouter:
    global _research_router
    if _research_router is None:
        _research_router = ResearchRouter()
    return _research_router


ResearchRouterDep = Annotated[ResearchRouter, Depends(get_research_router)]


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    user_id: str | None = None,
    router: ResearchRouter = Depends(get_research_router),
) -> DocumentResponse:
    """Upload document, chunk, embed, store."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    allowed_types = [
        "text/plain",
        "text/markdown",
        "text/html",
        "application/pdf",
        "application/json",
    ]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    return await router.create_document(workspace_id, file, user_id)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
    router: ResearchRouter = Depends(get_research_router),
) -> list[DocumentResponse]:
    """List documents for workspace."""
    return router.list_documents(workspace_id, limit, offset)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    router: ResearchRouter = Depends(get_research_router),
) -> DocumentResponse:
    """Get document."""
    doc = router.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: str,
    router: ResearchRouter = Depends(get_research_router),
) -> list[ChunkResponse]:
    """Get all chunks for a document."""
    return router.get_document_chunks(document_id)


@router.post("/briefs", response_model=BriefResponse)
async def create_brief(
    data: BriefCreate,
    router: ResearchRouter = Depends(get_research_router),
) -> BriefResponse:
    """Create new research brief."""
    return router.create_brief(data)


@router.get("/briefs", response_model=list[BriefResponse])
async def list_briefs(
    workspace_id: str,
    status: str | None = None,
    linked_position: str | None = None,
    limit: int = 50,
    offset: int = 0,
    router: ResearchRouter = Depends(get_research_router),
) -> list[BriefResponse]:
    """List briefs with filtering."""
    return router.list_briefs(workspace_id, status, linked_position, limit, offset)


@router.get("/briefs/{brief_id}", response_model=BriefResponse)
async def get_brief(
    brief_id: str,
    router: ResearchRouter = Depends(get_research_router),
) -> BriefResponse:
    """Get brief with evidence and citations."""
    brief = router.get_brief(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@router.put("/briefs/{brief_id}", response_model=BriefResponse)
async def update_brief(
    brief_id: str,
    data: BriefUpdate,
    router: ResearchRouter = Depends(get_research_router),
) -> BriefResponse:
    """Update brief thesis, status, links."""
    brief = router.update_brief(brief_id, data)
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief


@router.get("/briefs/{brief_id}/evidence", response_model=list[EvidenceResponse])
async def get_brief_evidence(
    brief_id: str,
    router: ResearchRouter = Depends(get_research_router),
) -> list[EvidenceResponse]:
    """Get all evidence for a brief."""
    return router.get_brief_evidence(brief_id)


@router.post("/retrieval/query", response_model=RetrievalResponse)
async def query_evidence(
    query: RetrievalQuery,
    router: ResearchRouter = Depends(get_research_router),
) -> RetrievalResponse:
    """Hybrid retrieval: vector + keyword, reranked."""
    return await router.query_evidence(query)


@router.post("/evidence", response_model=EvidenceResponse)
async def add_evidence(
    data: EvidenceCreate,
    router: ResearchRouter = Depends(get_research_router),
) -> EvidenceResponse:
    """Add evidence citation to brief."""
    evidence = router.add_evidence(data.brief_id, data.chunk_id, data.note)
    if not evidence:
        raise HTTPException(status_code=404, detail="Brief or chunk not found")
    return evidence


@router.get("/evidence/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: str,
    router: ResearchRouter = Depends(get_research_router),
) -> EvidenceResponse:
    """Get evidence with full context."""
    evidence = router.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence
