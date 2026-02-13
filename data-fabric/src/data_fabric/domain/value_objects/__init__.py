"""Domain value objects — immutable, self-validating types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Currency:
    """ISO 4217 currency code."""
    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 3 or not self.code.isalpha():
            raise ValueError(f"Invalid currency code: {self.code}")


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """Calibrated confidence score in [0, 1]."""
    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.value}")

    @property
    def calibration(self) -> str:
        if self.value >= 0.8:
            return "high"
        if self.value >= 0.5:
            return "medium"
        return "low"


@dataclass(frozen=True, slots=True)
class DateRange:
    """Immutable date range with validation."""
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be <= end ({self.end})")
