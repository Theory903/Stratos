"""Ingestion and refresh orchestration use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from data_fabric.adapters.sources import PolygonMarketSource
from data_fabric.domain.entities import AssetClass, MarketTick
from data_fabric.domain.errors import DataIngestionError


@dataclass(slots=True)
class RefreshRequestManager:
    """Persist and publish refresh requests."""

    documents: Any
    events: Any

    async def request_refresh(
        self,
        entity_type: str,
        entity_id: str,
        *,
        reason: str,
        providers: list[str] | None = None,
    ) -> bool:
        enqueued = await self.documents.enqueue_refresh_request(
            entity_type=entity_type,
            entity_id=entity_id,
            reason=reason,
            providers=providers or [],
        )
        if enqueued:
            await self.events.publish(
                topic="refresh.requested",
                key=f"{entity_type}:{entity_id}",
                payload={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "reason": reason,
                    "providers": providers or [],
                    "requested_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        return enqueued


class IngestMarketDataUseCase:
    """Explicit market-ingest endpoint: enqueue internal refreshes only."""

    def __init__(self, refreshes: RefreshRequestManager) -> None:
        self._refreshes = refreshes

    async def execute(self, tickers: list[str]) -> int:
        enqueued = 0
        for ticker in tickers:
            normalized = ticker.upper()
            provider = "coinapi" if normalized.startswith("X:") else "upstox" if "|" in normalized or normalized.startswith(("NSE", "BSE")) else "massive"
            requested = await self._refreshes.request_refresh(
                "market",
                normalized,
                reason="manual_ingest",
                providers=[provider],
            )
            enqueued += int(requested)
        return enqueued


class RefreshRouterUseCase:
    """Expand high-level refresh requests into provider-specific ingest jobs."""

    _PROVIDER_MAP: dict[str, list[str]] = {
        "world_state": ["fred"],
        "company": ["sec"],
        "country": ["world_bank"],
        "market": ["upstox", "coinapi", "massive"],
        "policy": ["rbi_rss", "sebi_rss"],
        "news": ["gdelt"],
        "social": ["reddit", "x"],
        "announcements": ["nse_rss", "bse_rss"],
        "orderbook": ["coinapi", "upstox"],
        "instrument": ["upstox"],
    }

    def __init__(self, events: Any, documents: Any) -> None:
        self._events = events
        self._documents = documents

    async def execute(self, refresh_request: dict[str, Any]) -> list[str]:
        entity_type = str(refresh_request["entity_type"])
        entity_id = str(refresh_request["entity_id"])
        providers = refresh_request.get("providers") or self._PROVIDER_MAP.get(entity_type, [])
        await self._documents.update_refresh_status(entity_type, entity_id, "routing")

        published: list[str] = []
        for provider in providers:
            await self._events.publish(
                topic="ingest.requested",
                key=f"{provider}:{entity_type}:{entity_id}",
                payload={
                    "provider": provider,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "reason": refresh_request.get("reason", "scheduled"),
                },
            )
            published.append(provider)
        return published


class ProviderIngestUseCase:
    """Fetch provider data and persist raw + normalized documents."""

    def __init__(
        self,
        providers: dict[str, Any],
        documents: Any,
        object_store: Any,
        events: Any,
    ) -> None:
        self._providers = providers
        self._documents = documents
        self._object_store = object_store
        self._events = events

    async def execute(self, message: dict[str, Any]) -> None:
        provider_name = str(message["provider"])
        entity_type = str(message["entity_type"])
        entity_id = str(message["entity_id"])

        provider = self._providers.get(provider_name)
        if provider is None:
            raise DataIngestionError(provider_name, "Provider is not registered")

        await self._documents.update_refresh_status(entity_type, entity_id, "ingesting")
        payload, document_type = await self._fetch_payload(provider_name, provider, entity_type, entity_id)

        request_hash = sha256(repr(payload).encode("utf-8")).hexdigest()
        stored_key = await self._object_store.put_raw_payload(
            provider=provider_name,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            request_hash=request_hash,
        )
        await self._documents.save_raw_ingest_run(
            provider=provider_name,
            entity_type=entity_type,
            entity_id=entity_id,
            document_type=document_type,
            request_hash=request_hash,
            object_key=stored_key,
        )
        await self._documents.save_provider_document(
            provider=provider_name,
            entity_type=entity_type,
            entity_id=entity_id,
            document_type=document_type,
            payload=payload,
            object_key=stored_key,
            request_hash=request_hash,
        )

        if provider_name == "sec":
            filings = payload.get("filings", [])
            await self._documents.save_company_filings(entity_id, filings)
            await self._documents.save_company_news_snapshot(entity_id, [], provider_set=())
        elif provider_name in {"rbi_rss", "sebi_rss"}:
            await self._documents.save_policy_documents(
                scope="india",
                documents=payload.get("documents", []),
            )
        elif provider_name == "gdelt":
            items = payload.get("items", [])
            await self._documents.save_company_news_snapshot(entity_id, items, provider_set=(provider_name,))
            await self._documents.save_normalized_news(entity_id, items, provider_set=(provider_name,))
        elif provider_name in {"reddit", "x"}:
            await self._documents.save_social_posts(entity_id, payload.get("items", []), provider_set=(provider_name,))
        elif provider_name in {"nse_rss", "bse_rss"}:
            await self._documents.save_exchange_announcements(entity_id, payload.get("items", []), provider_set=(provider_name,))
        elif provider_name == "upstox" and entity_type == "instrument":
            await self._documents.save_instrument_master(entity_id, payload.get("instrument", {}), provider_set=(provider_name,))
        elif provider_name in {"coinapi", "upstox"} and entity_type == "orderbook":
            await self._documents.save_order_book_snapshot(
                instrument_id=entity_id,
                data=payload.get("snapshot", {}),
                provider_set=(provider_name,),
            )

        await self._events.publish(
            topic="ingest.completed",
            key=f"{provider_name}:{entity_type}:{entity_id}",
            payload={
                "provider": provider_name,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "document_type": document_type,
            },
        )
        await self._documents.update_refresh_status(entity_type, entity_id, "ingested")

    async def _fetch_payload(
        self,
        provider_name: str,
        provider: Any,
        entity_type: str,
        entity_id: str,
    ) -> tuple[dict[str, Any], str]:
        if provider_name == "fred":
            observations = await provider.fetch(
                indicators=["DFF", "CPIAUCSL", "VIXCLS", "WALCL", "DCOILWTICO"]
            )
            return {"observations": observations, "entity_id": entity_id}, "macro_series"
        if provider_name == "world_bank":
            profile = await provider.fetch_country_profile(entity_id)
            return profile, "country_profile"
        if provider_name == "sec":
            bundle = await provider.fetch_company_bundle(entity_id)
            return bundle, "company_bundle"
        if provider_name == "massive":
            bars = await provider.fetch(tickers=[entity_id])
            return {"bars": bars, "ticker": entity_id}, "market_bars"
        if provider_name == "upstox":
            if entity_type == "orderbook":
                snapshot = await provider.fetch_order_book(entity_id)
                return {"snapshot": snapshot, "instrument_id": entity_id}, "order_book"
            if entity_type == "instrument":
                instrument = await provider.fetch_instrument_master(entity_id)
                return {"instrument": instrument, "instrument_id": entity_id}, "instrument_master"
            bars = await provider.fetch(tickers=[entity_id])
            return {"bars": bars, "ticker": entity_id}, "market_bars"
        if provider_name == "coinapi":
            if entity_type == "orderbook":
                snapshot = await provider.fetch_order_book(entity_id)
                return {"snapshot": snapshot, "instrument_id": entity_id}, "order_book"
            bars = await provider.fetch(tickers=[entity_id])
            return {"bars": bars, "ticker": entity_id}, "market_bars"
        if provider_name in {"rbi_rss", "sebi_rss", "nse_rss", "bse_rss"}:
            items = await provider.fetch(entity_id=entity_id)
            return {"documents": items, "scope": entity_id, "items": items}, "normalized_events"
        if provider_name == "gdelt":
            items = await provider.fetch(entity_id=entity_id)
            return {"items": items, "entity_id": entity_id}, "normalized_events"
        if provider_name in {"reddit", "x"}:
            items = await provider.fetch(entity_id=entity_id)
            return {"items": items, "entity_id": entity_id}, "normalized_events"
        raise DataIngestionError(provider_name, f"Unsupported ingest route for {entity_type}")


def normalize_market_bars(raw_bars: list[dict[str, Any]]) -> list[MarketTick]:
    """Convert provider market bars into domain entities."""

    normalized: list[MarketTick] = []
    for raw in raw_bars:
        asset_class = AssetClass(raw.get("asset_class", "equity"))
        normalized.append(
            MarketTick(
                ticker=str(raw["ticker"]).upper(),
                asset_class=asset_class,
                timestamp=datetime.fromisoformat(str(raw["timestamp"])),
                open=raw["open"],
                high=raw["high"],
                low=raw["low"],
                close=raw["close"],
                volume=int(raw["volume"]),
            )
        )
    return normalized
