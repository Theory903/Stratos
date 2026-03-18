"""NLP service dependency injection."""

from __future__ import annotations

from functools import lru_cache

from stratos_nlp.application import (
    AnalyzeSentimentUseCase,
    ExtractEntitiesUseCase,
    IndexDocumentUseCase,
    RetrieveContextUseCase,
)


@lru_cache
def _get_scorer():
    from stratos_nlp.adapters.sentiment.finbert import FinBERTScorer

    return FinBERTScorer()


@lru_cache
def _get_extractor():
    from stratos_nlp.adapters.extraction.spacy_ner import SpacyExtractor

    return SpacyExtractor()


@lru_cache
def _get_embedder():
    from stratos_nlp.adapters.embeddings.sbert import SentenceTransformerEmbedder

    return SentenceTransformerEmbedder()


@lru_cache
def _get_retriever():
    from stratos_nlp.adapters.rag.memory_store import InMemoryRetriever

    return InMemoryRetriever(embedder=_get_embedder())


def get_sentiment_analyzer() -> AnalyzeSentimentUseCase:
    return AnalyzeSentimentUseCase(scorer=_get_scorer())


def get_entity_extractor() -> ExtractEntitiesUseCase:
    return ExtractEntitiesUseCase(extractor=_get_extractor())


def get_document_indexer() -> IndexDocumentUseCase:
    return IndexDocumentUseCase(
        embedder=_get_embedder(),
        retriever=_get_retriever(),
        extractor=_get_extractor(),
        scorer=_get_scorer(),
    )


def get_context_retriever() -> RetrieveContextUseCase:
    return RetrieveContextUseCase(
        embedder=_get_embedder(),
        retriever=_get_retriever(),
    )
