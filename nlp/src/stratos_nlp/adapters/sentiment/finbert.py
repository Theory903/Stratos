"""FinBERT sentiment analysis adapter.

Implements `SentimentScorer` protocol.
Uses Hugging Face Transformers pipeline for financial sentiment.
"""

from __future__ import annotations

import torch
from transformers import pipeline

from stratos_nlp.domain.entities import SentimentLabel, SentimentResult


class FinBERTScorer:
    """Financial sentiment analysis using ProsusAI/finbert."""

    def __init__(self, model_name: str = "ProsusAI/finbert", pipeline_factory=None) -> None:
        self.model_name = model_name
        self._pipeline_factory = pipeline_factory or pipeline
        self._pipeline = None

    def name(self) -> str:
        return f"FinBERT({self.model_name})"

    def _load(self) -> None:
        """Lazy load the pipeline."""
        if self._pipeline is None:
            device = 0 if torch.cuda.is_available() else -1
            if torch.backends.mps.is_available():
                device = "mps"
            
            self._pipeline = self._pipeline_factory(
                "sentiment-analysis",
                model=self.model_name,
                device=device,
                top_k=None,  # Return all scores
            )

    def score(self, text: str) -> SentimentResult:
        """Score a single text."""
        self._load()
        # Truncate to 512 tokens approx
        truncated = text[:2000]
        result = self._pipeline(truncated)[0]
        
        # Result is list of dicts: [{'label': 'positive', 'score': 0.9}, ...]
        scores = {item["label"]: item["score"] for item in result}
        
        # Map to domain labels
        # FinBERT labels: positive, negative, neutral
        logits = {
            SentimentLabel.POSITIVE: scores.get("positive", 0.0),
            SentimentLabel.NEGATIVE: scores.get("negative", 0.0),
            SentimentLabel.NEUTRAL: scores.get("neutral", 0.0),
        }
        
        # Determine winner
        best_label = max(logits, key=logits.get)
        
        return SentimentResult(
            label=best_label,
            score=logits[best_label],
            logits=logits,
        )

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        """Score a batch of texts."""
        return [self.score(t) for t in texts]
