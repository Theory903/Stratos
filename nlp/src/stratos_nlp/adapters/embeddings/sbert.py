"""LangChain HuggingFace embedding adapter.

Implements `TextEmbedder` protocol using LangChain's HuggingFaceEmbeddings.
"""

from __future__ import annotations

from langchain_huggingface import HuggingFaceEmbeddings


class SentenceTransformerEmbedder:
    """Text embedding using LangChain's HuggingFaceEmbeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def name(self) -> str:
        return f"LangChain-HF({self.model_name})"

    def _load(self) -> None:
        """Lazy load model."""
        if self._model is None:
            # device="cpu" is default, can be set to "cuda" or "mps" if available
            self._model = HuggingFaceEmbeddings(model_name=self.model_name)

    def embed(self, text: str) -> list[float]:
        """Embed single text."""
        self._load()
        return self._model.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed batch of texts."""
        self._load()
        if not texts:
            return []
        return self._model.embed_documents(texts)
