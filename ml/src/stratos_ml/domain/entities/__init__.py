"""ML domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MarketRegime(StrEnum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    CRISIS = "crisis"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class Prediction:
    """Model prediction with metadata."""
    model_name: str
    value: float
    confidence: float
    horizon_days: int


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    """Anomaly detection result."""
    score: float
    is_anomaly: bool
    description: str
