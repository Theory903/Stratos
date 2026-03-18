"""FinBERT sentiment analysis adapter."""

from __future__ import annotations

from stratos_nlp.domain.entities import SentimentLabel, SentimentResult


class FinBERTScorer:
    """Financial sentiment analysis using ProsusAI/finbert."""

    def __init__(self, model_name: str = "ProsusAI/finbert", pipeline_factory=None) -> None:
        self.model_name = model_name
        self._pipeline_factory = pipeline_factory
        self._pipeline = None

    def name(self) -> str:
        return f"FinBERT({self.model_name})"

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        if self._pipeline_factory is None:
            try:
                import torch
            except ImportError:  # pragma: no cover - optional dependency
                torch = None
            from transformers import pipeline as transformers_pipeline

            device = -1
            if torch is not None and torch.cuda.is_available():
                device = 0
            if torch is not None and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
                device = "mps"
            self._pipeline_factory = lambda *args, **kwargs: transformers_pipeline(*args, **kwargs)
        self._pipeline = self._pipeline_factory(
            "sentiment-analysis",
            model=self.model_name,
            device=device if "device" in locals() else -1,
            top_k=None,
        )

    def score(self, text: str) -> SentimentResult:
        self._load()
        result = self._pipeline(text[:2000])[0]
        scores = {item["label"]: item["score"] for item in result}
        logits = {
            SentimentLabel.POSITIVE: scores.get("positive", 0.0),
            SentimentLabel.NEGATIVE: scores.get("negative", 0.0),
            SentimentLabel.NEUTRAL: scores.get("neutral", 0.0),
        }
        best_label = max(logits, key=logits.get)
        return SentimentResult(label=best_label, score=logits[best_label], logits=logits)

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        return [self.score(text) for text in texts]
