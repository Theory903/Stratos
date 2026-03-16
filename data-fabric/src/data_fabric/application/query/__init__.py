"""Snapshot-only read use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from data_fabric.application.common import FreshnessPolicy, SnapshotMeta, SnapshotRead


@dataclass(slots=True)
class QueryCompanyUseCase:
    store: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[Any]:
        normalized = ticker.upper()
        snapshot = await self.store.get_company_snapshot(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="company",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCountryUseCase:
    store: Any
    refreshes: Any

    async def execute(self, country_code: str) -> SnapshotRead[Any]:
        normalized = country_code.upper()
        snapshot = await self.store.get_country_snapshot(normalized)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="country",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryWorldStateUseCase:
    store: Any
    refreshes: Any

    async def execute(self) -> SnapshotRead[Any]:
        snapshot = await self.store.get_world_state_snapshot()
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="world_state",
            entity_id="global",
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryMarketHistoryUseCase:
    store: Any
    refreshes: Any

    async def execute(self, ticker: str, *, limit: int = 100) -> SnapshotRead[list[Any]]:
        normalized = ticker.upper()
        snapshot = await self.store.get_market_snapshot(normalized, limit=limit)
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="market",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryMarketRegimeUseCase:
    store: Any
    refreshes: Any

    async def execute(self) -> SnapshotRead[dict[str, Any]]:
        snapshot = await self.store.get_market_regime_snapshot()
        return await _snapshot_response(
            snapshot=snapshot,
            entity_type="market_regime",
            entity_id="global",
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCompanyFilingsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = ticker.upper()
        record = await self.documents.get_company_filings(normalized)
        return await _collection_response(
            record=record,
            entity_type="company_filings",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryCompanyNewsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, ticker: str) -> SnapshotRead[list[dict[str, Any]]]:
        normalized = ticker.upper()
        record = await self.documents.get_company_news_snapshot(normalized)
        return await _collection_response(
            record=record,
            entity_type="company_news",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class QueryPolicyEventsUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.get_policy_documents(normalized)
        return await _collection_response(
            record=record,
            entity_type="policy",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


@dataclass(slots=True)
class SearchPolicyUseCase:
    documents: Any
    refreshes: Any

    async def execute(self, query: str, *, scope: str = "global") -> SnapshotRead[list[dict[str, Any]]]:
        normalized = scope.lower()
        record = await self.documents.search_policy_documents(normalized, query)
        return await _collection_response(
            record=record,
            entity_type="policy",
            entity_id=normalized,
            refreshes=self.refreshes,
        )


async def _snapshot_response(snapshot: Any, entity_type: str, entity_id: str, refreshes: Any) -> SnapshotRead[Any]:
    if snapshot is None:
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="cache_miss")
        return SnapshotRead(
            status="pending",
            data=None,
            meta=SnapshotMeta(
                entity_type=entity_type,
                entity_id=entity_id,
                as_of=None,
                computed_at=None,
                freshness="pending",
                refresh_enqueued=refresh_enqueued,
                suggested_retry_seconds=30,
            ),
        )

    freshness = FreshnessPolicy.classify(entity_type, snapshot.as_of)
    refresh_enqueued = False
    if freshness == "stale":
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="stale_snapshot")
    return SnapshotRead(
        status="ready",
        data=snapshot.data,
        meta=SnapshotMeta(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of=snapshot.as_of,
            computed_at=snapshot.computed_at,
            freshness=freshness,
            refresh_enqueued=refresh_enqueued,
            feature_version=snapshot.feature_version,
            provider_set=snapshot.provider_set,
        ),
    )


async def _collection_response(record: Any, entity_type: str, entity_id: str, refreshes: Any) -> SnapshotRead[list[dict[str, Any]]]:
    if record is None:
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="cache_miss")
        return SnapshotRead(
            status="pending",
            data=None,
            meta=SnapshotMeta(
                entity_type=entity_type,
                entity_id=entity_id,
                as_of=None,
                computed_at=None,
                freshness="pending",
                refresh_enqueued=refresh_enqueued,
                suggested_retry_seconds=30,
            ),
        )

    freshness = FreshnessPolicy.classify(entity_type, record.as_of)
    refresh_enqueued = False
    if freshness == "stale":
        refresh_enqueued = await refreshes.request_refresh(entity_type, entity_id, reason="stale_snapshot")
    return SnapshotRead(
        status="ready",
        data=list(record.items),
        meta=SnapshotMeta(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of=record.as_of,
            computed_at=record.computed_at,
            freshness=freshness,
            refresh_enqueued=refresh_enqueued,
            feature_version=record.feature_version,
            provider_set=record.provider_set,
        ),
    )
