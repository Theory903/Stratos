"""NLP domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class SentimentResult:
    """Sentiment analysis result."""
    label: SentimentLabel
    score: float  # [0, 1] confidence
    logits: dict[str, float]


@dataclass(frozen=True, slots=True)
class AnalyzedDocument:
    """Processed document with embeddings and metadata."""
    id: str
    content: str
    source: str
    published_at: datetime
    entities: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    sentiment: SentimentResult | None = None
