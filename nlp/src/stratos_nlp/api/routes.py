"""NLP service API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from stratos_nlp.api.deps import (
    get_context_retriever,
    get_document_indexer,
    get_entity_extractor,
    get_sentiment_analyzer,
)
from stratos_nlp.application import (
    AnalyzeSentimentUseCase,
    ExtractEntitiesUseCase,
    IndexDocumentUseCase,
    RetrieveContextUseCase,
)
from stratos_nlp.domain.entities import SentimentLabel

router = APIRouter(prefix="/nlp", tags=["NLP"])


# ── Request / Response Models ──────────────────────────────────────

class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)

class SentimentResponse(BaseModel):
    label: str
    score: float
    logits: dict[str, float]

class EntityResponse(BaseModel):
    entities: list[str]

class IndexRequest(BaseModel):
    doc_id: str
    content: str
    source: str

class RetrieveRequest(BaseModel):
    query: str
    limit: int = 5

class DocumentResponse(BaseModel):
    id: str
    content: str
    score: float | None = None  # Similarity score if available


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/sentiment", response_model=SentimentResponse)
async def analyze_sentiment(
    request: TextRequest,
    use_case: Annotated[AnalyzeSentimentUseCase, Depends(get_sentiment_analyzer)],
) -> SentimentResponse:
    """Analyze financial sentiment of text."""
    result = use_case.execute(request.text)
    return SentimentResponse(
        label=result.label,
        score=result.score,
        logits=result.logits,
    )


@router.post("/entities", response_model=EntityResponse)
async def extract_entities(
    request: TextRequest,
    use_case: Annotated[ExtractEntitiesUseCase, Depends(get_entity_extractor)],
) -> EntityResponse:
    """Extract named entities (ORG, PERSON, etc.)."""
    entities = use_case.execute(request.text)
    return EntityResponse(entities=entities)


@router.post("/rag/index")
async def index_document(
    request: IndexRequest,
    use_case: Annotated[IndexDocumentUseCase, Depends(get_document_indexer)],
) -> dict[str, str]:
    """Index a document for RAG (extracts entities/sentiment + embeds)."""
    doc = use_case.execute(request.doc_id, request.content, request.source)
    return {"status": "indexed", "id": doc.id}


@router.post("/rag/search", response_model=list[DocumentResponse])
async def search_context(
    request: RetrieveRequest,
    use_case: Annotated[RetrieveContextUseCase, Depends(get_context_retriever)],
) -> list[DocumentResponse]:
    """Retrieve relevant documents for query."""
    docs = use_case.execute(request.query, request.limit)
    return [
        DocumentResponse(id=d.id, content=d.content)
        for d in docs
    ]
