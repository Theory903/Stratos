"""Sentence transformer embedding adapter."""

from __future__ import annotations

import sys
import types

try:  # pragma: no cover - exercised when dependency is installed
    import sentence_transformers  # type: ignore
except ImportError:  # pragma: no cover - lightweight fallback for tests
    sentence_transformers = types.ModuleType("sentence_transformers")

    class _MissingSentenceTransformer:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("sentence-transformers is required to use SentenceTransformerEmbedder.")

    sentence_transformers.SentenceTransformer = _MissingSentenceTransformer  # type: ignore[attr-defined]
    sys.modules.setdefault("sentence_transformers", sentence_transformers)


class SentenceTransformerEmbedder:
    """Text embedding using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def name(self) -> str:
        return f"SentenceTransformer({self.model_name})"

    def _load(self) -> None:
        if self._model is not None:
            return
        self._model = sentence_transformers.SentenceTransformer(self.model_name)

    def embed(self, text: str) -> list[float]:
        self._load()
        return list(map(float, self._model.encode(text)))

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if not texts:
            return []
        return [list(map(float, vector)) for vector in self._model.encode(texts)]
