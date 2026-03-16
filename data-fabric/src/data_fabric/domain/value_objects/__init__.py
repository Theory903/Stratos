"""Domain value objects — immutable, self-validating types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generic, TypeVar

T = TypeVar("T")


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


@dataclass(frozen=True, slots=True)
class SnapshotRecord(Generic[T]):
    """Immutable stored snapshot plus freshness metadata."""

    data: T
    as_of: datetime
    computed_at: datetime
    stored_at: datetime
    feature_version: str | None = None
    source_window_start: datetime | None = None
    source_window_end: datetime | None = None
    provider_set: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class CollectionRecord(Generic[T]):
    """Collection snapshot returned from document storage."""

    items: tuple[T, ...]
    as_of: datetime
    computed_at: datetime
    feature_version: str | None = None
    provider_set: tuple[str, ...] = field(default_factory=tuple)
