"""Simple in-memory retriever for RAG tests and lightweight service use."""

from __future__ import annotations

from math import sqrt

from stratos_nlp.domain.entities import AnalyzedDocument
from stratos_nlp.domain.ports import TextEmbedder


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _norm(values: list[float]) -> float:
    return sqrt(sum(value * value for value in values))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    denominator = _norm(left) * _norm(right)
    if denominator == 0:
        return 0.0
    return _dot(left, right) / denominator


class InMemoryRetriever:
    """Protocol-compatible in-memory retriever without FAISS dependency."""

    def __init__(self, embedder: TextEmbedder) -> None:
        self.embedder = embedder
        self._documents: list[AnalyzedDocument] = []

    def index(self, document: AnalyzedDocument) -> None:
        embedding = document.embedding or self.embedder.embed(document.content)
        self._documents.append(
            AnalyzedDocument(
                id=document.id,
                content=document.content,
                source=document.source,
                published_at=document.published_at,
                entities=document.entities,
                sentiment=document.sentiment,
                embedding=embedding,
            )
        )

    def search(self, query_embedding: list[float], limit: int = 5) -> list[AnalyzedDocument]:
        ranked = sorted(
            self._documents,
            key=lambda document: _cosine_similarity(query_embedding, document.embedding or []),
            reverse=True,
        )
        return ranked[:limit]
