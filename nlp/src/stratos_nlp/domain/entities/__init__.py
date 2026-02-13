"""NLP domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Sentiment(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class SentimentResult:
    text: str
    sentiment: Sentiment
    score: float
    model: str


@dataclass(frozen=True, slots=True)
class AnalyzedDocument:
    document_id: str
    entities: list[dict[str, str]]
    summary: str
    key_metrics: dict[str, float]


@dataclass(frozen=True, slots=True)
class NarrativeShift:
    topic: str
    previous_sentiment: float
    current_sentiment: float
    shift_magnitude: float
    description: str
