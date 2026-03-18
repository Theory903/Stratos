"""Shared application-layer types and freshness policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Generic, Literal, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class SnapshotMeta:
    """Metadata attached to read results from the internal data platform."""

    entity_type: str
    entity_id: str
    as_of: datetime | None
    freshness: Literal["fresh", "stale", "pending"]
    refresh_enqueued: bool
    feature_version: str | None = None
    provider_set: tuple[str, ...] = ()
    computed_at: datetime | None = None
    suggested_retry_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class SnapshotRead(Generic[T]):
    """Result of a query against a served snapshot."""

    status: Literal["ready", "pending"]
    data: T | None
    meta: SnapshotMeta


class FreshnessPolicy:
    """Freshness windows for served entities."""

    _DEFAULT_WINDOWS: dict[str, timedelta] = {
        "world_state": timedelta(hours=6),
        "company": timedelta(hours=24),
        "country": timedelta(hours=24),
        "company_filings": timedelta(hours=24),
        "company_news": timedelta(hours=24),
        "news": timedelta(hours=6),
        "social": timedelta(minutes=20),
        "announcements": timedelta(minutes=20),
        "exchange_announcements": timedelta(minutes=20),
        "orderbook": timedelta(minutes=5),
        "order_book": timedelta(minutes=5),
        "instrument": timedelta(days=1),
        "decision_context": timedelta(minutes=10),
        "replay_decision": timedelta(minutes=10),
        "policy": timedelta(minutes=30),
        "events_feed": timedelta(minutes=30),
        "events_clusters": timedelta(minutes=30),
        "events_pulse": timedelta(minutes=30),
        "market_regime": timedelta(minutes=15),
        "history_regimes": timedelta(hours=6),
        "compare_metric": timedelta(hours=6),
        "compare_entity": timedelta(hours=6),
        "anomaly": timedelta(hours=6),
        "portfolio": timedelta(minutes=15),
        "portfolio_exposures": timedelta(minutes=15),
        "portfolio_risk": timedelta(minutes=15),
        "portfolio_decision_log": timedelta(minutes=15),
        "decision_queue": timedelta(minutes=15),
    }

    @classmethod
    def classify(cls, entity_type: str, as_of: datetime | None) -> Literal["fresh", "stale", "pending"]:
        if as_of is None:
            return "pending"
        now = datetime.now(timezone.utc)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)
        return "fresh" if now - as_of <= cls.window(entity_type, now=now) else "stale"

    @classmethod
    def window(cls, entity_type: str, *, now: datetime | None = None) -> timedelta:
        normalized = entity_type.lower()
        if normalized in {"market", "fx"}:
            moment = now or datetime.now(timezone.utc)
            active_open = time(hour=13, minute=30)
            active_close = time(hour=20, minute=0)
            if moment.weekday() < 5 and active_open <= moment.timetz().replace(tzinfo=None) <= active_close:
                return timedelta(minutes=15)
            return timedelta(hours=12)
        return cls._DEFAULT_WINDOWS.get(normalized, timedelta(hours=24))
