"""MongoDB-backed document store for raw docs, filings, policy, and refreshes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from data_fabric.domain.value_objects import CollectionRecord, SnapshotRecord

try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
except ImportError:  # pragma: no cover
    AsyncIOMotorClient = None  # type: ignore[assignment]
    AsyncIOMotorDatabase = Any  # type: ignore[misc,assignment]


class MongoDocumentStore:
    """Async MongoDB helper for document-heavy storage."""

    def __init__(self, url: str, database: str) -> None:
        if AsyncIOMotorClient is None:
            raise RuntimeError("motor is required to use MongoDocumentStore")
        self._client = AsyncIOMotorClient(url)
        self._db: AsyncIOMotorDatabase = self._client[database]

    async def close(self) -> None:
        self._client.close()

    async def enqueue_refresh_request(
        self,
        *,
        entity_type: str,
        entity_id: str,
        reason: str,
        providers: list[str],
    ) -> bool:
        now = datetime.now(timezone.utc)
        active = await self._db.refresh_requests.find_one(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": {"$in": ["queued", "routing", "ingesting"]},
            }
        )
        if active is not None:
            return False
        await self._db.refresh_requests.insert_one(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "reason": reason,
                "providers": providers,
                "status": "queued",
                "requested_at": now,
                "updated_at": now,
            }
        )
        return True

    async def update_refresh_status(self, entity_type: str, entity_id: str, status: str) -> None:
        await self._db.refresh_requests.update_many(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": {"$ne": "ready"},
            },
            {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}},
        )

    async def save_raw_ingest_run(
        self,
        *,
        provider: str,
        entity_type: str,
        entity_id: str,
        document_type: str,
        request_hash: str,
        object_key: str,
    ) -> None:
        await self._db.raw_ingest_runs.insert_one(
            {
                "provider": provider,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "document_type": document_type,
                "request_hash": request_hash,
                "object_key": object_key,
                "ingested_at": datetime.now(timezone.utc),
            }
        )

    async def save_provider_document(
        self,
        *,
        provider: str,
        entity_type: str,
        entity_id: str,
        document_type: str,
        payload: dict[str, Any],
        object_key: str,
        request_hash: str,
    ) -> None:
        await self._db.raw_provider_documents.insert_one(
            {
                "provider": provider,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "document_type": document_type,
                "payload": payload,
                "object_key": object_key,
                "request_hash": request_hash,
                "ingested_at": datetime.now(timezone.utc),
            }
        )

    async def get_latest_provider_document(
        self,
        provider: str,
        entity_type: str,
        entity_id: str,
        document_type: str,
    ) -> dict[str, Any] | None:
        return await self._db.raw_provider_documents.find_one(
            {
                "provider": provider,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "document_type": document_type,
            },
            sort=[("ingested_at", -1)],
        )

    async def save_company_filings(self, ticker: str, filings: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        await self._db.company_filings.insert_one(
            {
                "ticker": ticker.upper(),
                "items": filings,
                "as_of": now,
                "computed_at": now,
                "feature_version": "sec-filings-v1",
                "provider_set": ["sec"],
            }
        )

    async def get_company_filings(self, ticker: str) -> CollectionRecord[dict[str, Any]] | None:
        doc = await self._db.company_filings.find_one(
            {"ticker": ticker.upper()},
            sort=[("computed_at", -1)],
        )
        return self._to_collection_record(doc)

    async def save_company_news_snapshot(
        self,
        ticker: str,
        items: list[dict[str, Any]],
        *,
        provider_set: tuple[str, ...],
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.news_events.insert_one(
            {
                "ticker": ticker.upper(),
                "items": items,
                "as_of": now,
                "computed_at": now,
                "feature_version": "company-news-v1",
                "provider_set": list(provider_set),
            }
        )

    async def get_company_news_snapshot(
        self,
        ticker: str,
    ) -> CollectionRecord[dict[str, Any]] | None:
        doc = await self._db.news_events.find_one(
            {"ticker": ticker.upper()},
            sort=[("computed_at", -1)],
        )
        return self._to_collection_record(doc)

    async def save_policy_documents(
        self,
        *,
        scope: str,
        documents: list[dict[str, Any]],
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.policy_documents.insert_one(
            {
                "scope": scope.lower(),
                "items": documents,
                "as_of": now,
                "computed_at": now,
                "feature_version": "policy-v1",
                "provider_set": [],
            }
        )

    async def get_policy_documents(self, scope: str) -> CollectionRecord[dict[str, Any]] | None:
        doc = await self._db.policy_documents.find_one(
            {"scope": scope.lower()},
            sort=[("computed_at", -1)],
        )
        return self._to_collection_record(doc)

    async def search_policy_documents(
        self,
        scope: str,
        query: str,
    ) -> CollectionRecord[dict[str, Any]] | None:
        record = await self.get_policy_documents(scope)
        if record is None:
            return None
        needle = query.lower().strip()
        if not needle:
            return record
        matches = tuple(
            item
            for item in record.items
            if needle in str(item.get("title", "")).lower()
            or needle in str(item.get("summary", "")).lower()
            or needle in str(item.get("content", "")).lower()
        )
        return CollectionRecord(
            items=matches,
            as_of=record.as_of,
            computed_at=record.computed_at,
            feature_version=record.feature_version,
            provider_set=record.provider_set,
        )

    async def save_event_feed(
        self,
        *,
        scope: str,
        items: list[dict[str, Any]],
        provider_set: tuple[str, ...] = (),
        feature_version: str = "event-feed-v1",
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.event_feeds.insert_one(
            {
                "scope": scope.lower(),
                "items": items,
                "as_of": now,
                "computed_at": now,
                "feature_version": feature_version,
                "provider_set": list(provider_set),
            }
        )

    async def get_event_feed(self, scope: str) -> CollectionRecord[dict[str, Any]] | None:
        doc = await self._db.event_feeds.find_one(
            {"scope": scope.lower()},
            sort=[("computed_at", -1)],
        )
        return self._to_collection_record(doc)

    async def save_event_clusters(
        self,
        *,
        scope: str,
        items: list[dict[str, Any]],
        provider_set: tuple[str, ...] = (),
        feature_version: str = "event-clusters-v1",
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.event_clusters.insert_one(
            {
                "scope": scope.lower(),
                "items": items,
                "as_of": now,
                "computed_at": now,
                "feature_version": feature_version,
                "provider_set": list(provider_set),
            }
        )

    async def get_event_clusters(self, scope: str) -> CollectionRecord[dict[str, Any]] | None:
        doc = await self._db.event_clusters.find_one(
            {"scope": scope.lower()},
            sort=[("computed_at", -1)],
        )
        return self._to_collection_record(doc)

    async def save_event_pulse(
        self,
        *,
        scope: str,
        data: dict[str, Any],
        provider_set: tuple[str, ...] = (),
        feature_version: str = "event-pulse-v1",
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.event_pulses.insert_one(
            {
                "scope": scope.lower(),
                "data": data,
                "as_of": now,
                "computed_at": now,
                "feature_version": feature_version,
                "provider_set": list(provider_set),
            }
        )

    async def get_event_pulse(self, scope: str) -> SnapshotRecord[dict[str, Any]] | None:
        doc = await self._db.event_pulses.find_one(
            {"scope": scope.lower()},
            sort=[("computed_at", -1)],
        )
        return self._to_snapshot_record(doc)

    async def search_event_feed(
        self,
        scope: str,
        query: str,
    ) -> CollectionRecord[dict[str, Any]] | None:
        record = await self.get_event_feed(scope)
        if record is None:
            return None
        needle = query.lower().strip()
        if not needle:
            return record
        matches = tuple(
            item
            for item in record.items
            if needle in str(item.get("title", "")).lower()
            or needle in str(item.get("summary", "")).lower()
            or needle in str(item.get("region", "")).lower()
            or needle in " ".join(item.get("entities", [])).lower()
        )
        return CollectionRecord(
            items=matches,
            as_of=record.as_of,
            computed_at=record.computed_at,
            feature_version=record.feature_version,
            provider_set=record.provider_set,
        )

    async def save_portfolio_snapshot(
        self,
        *,
        name: str,
        data: dict[str, Any],
        provider_set: tuple[str, ...] = ("manual",),
        feature_version: str = "portfolio-v1",
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.portfolio_snapshots.insert_one(
            {
                "name": name,
                "data": data,
                "as_of": now,
                "computed_at": now,
                "feature_version": feature_version,
                "provider_set": list(provider_set),
            }
        )

    async def get_portfolio_snapshot(self, name: str = "primary") -> SnapshotRecord[dict[str, Any]] | None:
        doc = await self._db.portfolio_snapshots.find_one(
            {"name": name},
            sort=[("computed_at", -1)],
        )
        return self._to_snapshot_record(doc)

    async def append_portfolio_decision(
        self,
        *,
        name: str,
        decision: dict[str, Any],
        feature_version: str = "portfolio-decision-log-v1",
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._db.portfolio_decisions.insert_one(
            {
                "name": name,
                "decision": decision,
                "computed_at": now,
                "as_of": now,
                "feature_version": feature_version,
                "provider_set": ["internal"],
            }
        )

    async def get_portfolio_decision_log(self, name: str = "primary") -> CollectionRecord[dict[str, Any]] | None:
        cursor = self._db.portfolio_decisions.find({"name": name}).sort("computed_at", -1).limit(50)
        docs = await cursor.to_list(length=50)
        if not docs:
            return None
        latest = docs[0]
        return CollectionRecord(
            items=tuple(doc["decision"] for doc in docs),
            as_of=latest["as_of"],
            computed_at=latest["computed_at"],
            feature_version=latest.get("feature_version"),
            provider_set=tuple(latest.get("provider_set", [])),
        )

    @staticmethod
    def _to_collection_record(
        doc: dict[str, Any] | None,
    ) -> CollectionRecord[dict[str, Any]] | None:
        if doc is None:
            return None
        return CollectionRecord(
            items=tuple(doc.get("items", [])),
            as_of=doc["as_of"],
            computed_at=doc["computed_at"],
            feature_version=doc.get("feature_version"),
            provider_set=tuple(doc.get("provider_set", [])),
        )

    @staticmethod
    def _to_snapshot_record(
        doc: dict[str, Any] | None,
    ) -> SnapshotRecord[dict[str, Any]] | None:
        if doc is None:
            return None
        return SnapshotRecord(
            data=doc.get("data", {}),
            as_of=doc["as_of"],
            computed_at=doc["computed_at"],
            stored_at=doc.get("as_of", doc["computed_at"]),
            feature_version=doc.get("feature_version"),
            provider_set=tuple(doc.get("provider_set", [])),
        )
