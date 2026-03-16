"""NLP domain ports — abstract interfaces."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from stratos_nlp.domain.entities import AnalyzedDocument, SentimentResult


@runtime_checkable
class SentimentScorer(Protocol):
    """Score sentiment of text (ISP: score only)."""

    def name(self) -> str: ...
    def score(self, text: str) -> SentimentResult: ...
    def score_batch(self, texts: list[str]) -> list[SentimentResult]: ...


@runtime_checkable
class EntityExtractor(Protocol):
    """Extract named entities from text (ISP: extract only)."""

    def name(self) -> str: ...
    def extract(self, text: str) -> list[str]: ...


@runtime_checkable
class TextEmbedder(Protocol):
    """Convert text to vector embeddings (ISP: embed only)."""

    def name(self) -> str: ...
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class DocumentRetriever(Protocol):
    """Retrieve documents from vector store (ISP: retrieve only)."""

    def index(self, document: AnalyzedDocument) -> None: ...
    def search(self, query_embedding: list[float], limit: int = 5) -> list[AnalyzedDocument]: ...
