"""NLP application use cases."""

from __future__ import annotations

from typing import Protocol

from stratos_nlp.domain.entities import AnalyzedDocument, SentimentResult
from stratos_nlp.domain.ports import (
    DocumentRetriever,
    EntityExtractor,
    SentimentScorer,
    TextEmbedder,
)


class AnalyzeSentimentUseCase:
    """Analyze sentiment of a text or batch of texts."""

    def __init__(self, scorer: SentimentScorer) -> None:
        self.scorer = scorer

    def execute(self, text: str) -> SentimentResult:
        return self.scorer.score(text)


class ExtractEntitiesUseCase:
    """Extract named entities from text."""

    def __init__(self, extractor: EntityExtractor) -> None:
        self.extractor = extractor

    def execute(self, text: str) -> list[str]:
        return self.extractor.extract(text)


class IndexDocumentUseCase:
    """Process and index a document for RAG."""

    def __init__(
        self,
        embedder: TextEmbedder,
        retriever: DocumentRetriever,
        extractor: EntityExtractor,
        scorer: SentimentScorer,
    ) -> None:
        self.embedder = embedder
        self.retriever = retriever
        self.extractor = extractor
        self.scorer = scorer

    def execute(self, doc_id: str, content: str, source: str) -> AnalyzedDocument:
        # Pipelined processing
        entities = self.extractor.extract(content)
        sentiment = self.scorer.score(content)
        embedding = self.embedder.embed(content)
        
        doc = AnalyzedDocument(
            id=doc_id,
            content=content,
            source=source,
            published_at=datetime.now(),
            entities=entities,
            embedding=embedding,
            sentiment=sentiment,
        )
        
        self.retriever.index(doc)
        return doc


class RetrieveContextUseCase:
    """Retrieve relevant documents for a query."""

    def __init__(self, embedder: TextEmbedder, retriever: DocumentRetriever) -> None:
        self.embedder = embedder
        self.retriever = retriever

    def execute(self, query: str, limit: int = 5) -> list[AnalyzedDocument]:
        query_vec = self.embedder.embed(query)
        return self.retriever.search(query_vec, limit=limit)
