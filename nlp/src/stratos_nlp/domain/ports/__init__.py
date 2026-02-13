"""NLP domain ports — narrow interfaces for NLP capabilities.

Each protocol is deliberately minimal (Interface Segregation).
Concrete adapters (FinBERT, spaCy, etc.) implement these.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SentimentScorer(Protocol):
    """Score text for financial sentiment."""
    def score(self, text: str) -> float: ...
    def score_batch(self, texts: list[str]) -> list[float]: ...


@runtime_checkable
class EntityExtractor(Protocol):
    """Extract named entities from text."""
    def extract(self, text: str) -> list[dict[str, str]]: ...


@runtime_checkable
class TextEmbedder(Protocol):
    """Embed text into vector space."""
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class DocumentRetriever(Protocol):
    """Retrieve relevant documents from vector store (RAG)."""
    def retrieve(self, query: str, top_k: int = 5) -> list[dict]: ...
    def index(self, document_id: str, text: str, metadata: dict) -> None: ...
