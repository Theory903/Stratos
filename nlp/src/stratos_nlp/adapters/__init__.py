"""NLP adapters export.

Keep imports lazy so optional model dependencies do not break lightweight
test runs or service startup paths that do not need every adapter.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["FinBERTScorer", "SpacyExtractor", "SentenceTransformerEmbedder", "InMemoryRetriever"]

_ADAPTER_MODULES = {
    "FinBERTScorer": "stratos_nlp.adapters.sentiment.finbert",
    "SpacyExtractor": "stratos_nlp.adapters.extraction.spacy_ner",
    "SentenceTransformerEmbedder": "stratos_nlp.adapters.embeddings.sbert",
    "InMemoryRetriever": "stratos_nlp.adapters.rag.memory_store",
}


def __getattr__(name: str) -> Any:
    module_name = _ADAPTER_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name)
    return getattr(module, name)
