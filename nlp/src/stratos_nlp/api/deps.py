"""NLP service dependency injection."""

from stratos_nlp.adapters import (
    FinBERTScorer,
    InMemoryRetriever,
    SentenceTransformerEmbedder,
    SpacyExtractor,
)
from stratos_nlp.application import (
    AnalyzeSentimentUseCase,
    ExtractEntitiesUseCase,
    IndexDocumentUseCase,
    RetrieveContextUseCase,
)

# ── Singletons ─────────────────────────────────────────────────────

_scorer = FinBERTScorer()
_extractor = SpacyExtractor()
_embedder = SentenceTransformerEmbedder()
_retriever = InMemoryRetriever(embedder=_embedder)  # Uses embedder for internal embedding if needed


# ── Dependency Factories ───────────────────────────────────────────

def get_sentiment_analyzer() -> AnalyzeSentimentUseCase:
    return AnalyzeSentimentUseCase(scorer=_scorer)


def get_entity_extractor() -> ExtractEntitiesUseCase:
    return ExtractEntitiesUseCase(extractor=_extractor)


def get_document_indexer() -> IndexDocumentUseCase:
    return IndexDocumentUseCase(
        embedder=_embedder,
        retriever=_retriever,
        extractor=_extractor,
        scorer=_scorer,
    )


def get_context_retriever() -> RetrieveContextUseCase:
    return RetrieveContextUseCase(
        embedder=_embedder,
        retriever=_retriever,
    )
