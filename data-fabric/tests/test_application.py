"""Targeted application tests for V1 compatibility and V2 snapshot flow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from data_fabric.adapters.sources import PolygonMarketSource
from data_fabric.application import (
    FeatureBuilderUseCase,
    IngestMarketDataUseCase,
    InsightBuilderUseCase,
    LegacyQueryCompanyUseCase,
    QueryCompanyUseCase,
    QueryProviderHealthUseCase,
    ReplayDecisionUseCase,
    QueryWorldStateUseCase,
    RefreshRequestManager,
)
from data_fabric.domain.entities import AssetClass, CompanyProfile, MarketTick
from data_fabric.domain.value_objects import SnapshotRecord


@pytest.fixture
def mock_documents() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_events() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_store() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_refreshes() -> AsyncMock:
    refreshes = AsyncMock()
    refreshes.request_refresh.return_value = True
    return refreshes


class TestRefreshRequestManager:
    @pytest.mark.asyncio
    async def test_publishes_refresh_when_request_is_new(
        self,
        mock_documents: AsyncMock,
        mock_events: AsyncMock,
    ) -> None:
        mock_documents.enqueue_refresh_request.return_value = True

        manager = RefreshRequestManager(documents=mock_documents, events=mock_events)
        enqueued = await manager.request_refresh("company", "AAPL", reason="cache_miss")

        assert enqueued is True
        mock_events.publish.assert_awaited_once()


class TestV2QueryUseCases:
    @pytest.mark.asyncio
    async def test_company_query_returns_pending_when_snapshot_missing(
        self,
        mock_store: AsyncMock,
        mock_refreshes: AsyncMock,
    ) -> None:
        mock_store.get_company_snapshot.return_value = None

        use_case = QueryCompanyUseCase(store=mock_store, refreshes=mock_refreshes)
        result = await use_case.execute("AAPL")

        assert result.status == "pending"
        assert result.meta.refresh_enqueued is True
        assert result.meta.entity_id == "AAPL"

    @pytest.mark.asyncio
    async def test_company_query_returns_stale_snapshot_and_enqueues_refresh(
        self,
        mock_store: AsyncMock,
        mock_refreshes: AsyncMock,
    ) -> None:
        stored_at = datetime.now(UTC) - timedelta(days=2)
        mock_store.get_company_snapshot.return_value = SnapshotRecord(
            data=CompanyProfile(
                ticker="AAPL",
                name="Apple Inc.",
                earnings_quality=0.91,
                leverage_ratio=0.22,
                free_cash_flow_stability=0.85,
                fraud_score=0.08,
                moat_score=0.88,
                stored_at=stored_at,
            ),
            as_of=stored_at,
            computed_at=stored_at,
            stored_at=stored_at,
            feature_version="company-v1",
            provider_set=("sec",),
        )

        use_case = QueryCompanyUseCase(store=mock_store, refreshes=mock_refreshes)
        result = await use_case.execute("AAPL")

        assert result.status == "ready"
        assert result.meta.freshness == "stale"
        assert result.meta.refresh_enqueued is True

    @pytest.mark.asyncio
    async def test_world_state_query_returns_fresh_snapshot_without_refresh(
        self,
        mock_store: AsyncMock,
        mock_refreshes: AsyncMock,
    ) -> None:
        stored_at = datetime.now(UTC)
        mock_store.get_world_state_snapshot.return_value = SnapshotRecord(
            data=AsyncMock(),  # serialization is not under test here
            as_of=stored_at,
            computed_at=stored_at,
            stored_at=stored_at,
            feature_version="world-state-v1",
            provider_set=("fred",),
        )

        use_case = QueryWorldStateUseCase(store=mock_store, refreshes=mock_refreshes)
        result = await use_case.execute()

        assert result.status == "ready"
        assert result.meta.freshness == "fresh"
        mock_refreshes.request_refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_provider_health_query_summarizes_configured_and_degraded_sources(self) -> None:
        healthy_provider = SimpleNamespace(source_name="upstox", health_check=AsyncMock(return_value=True))
        degraded_provider = SimpleNamespace(source_name="coinapi", health_check=AsyncMock(return_value=False))
        settings = SimpleNamespace(
            market_api_key="massive-key",
            fred_api_key="fred-key",
            world_bank_base_url="https://api.worldbank.org/v2",
            oanda_api_key="",
            sec_user_agent="agent",
            upstox_api_key="upstox-key",
            coinapi_api_key="coin-key",
            gdelt_base_url="https://api.gdeltproject.org/api/v2",
            reddit_client_id="",
            reddit_client_secret="",
            x_bearer_token="",
            rbi_rss_url="https://www.rbi.org.in/Scripts/RSS.aspx?Id=4",
            sebi_rss_url="https://www.sebi.gov.in/sebirss.xml",
            nse_rss_url="https://www.nseindia.com/rss-feed",
            bse_rss_url="https://www.bseindia.com/rss-feed.xml",
        )

        use_case = QueryProviderHealthUseCase(
            providers={"upstox": healthy_provider, "coinapi": degraded_provider},
            settings=settings,
        )
        result = await use_case.execute()

        assert result.status == "ready"
        assert result.data["overview"]["healthy"] == 1
        assert result.data["overview"]["degraded"] == 1
        assert result.data["providers"][0]["provider"] == "upstox"

    @pytest.mark.asyncio
    async def test_replay_decision_returns_structured_shadow_packet(self, mock_store: AsyncMock, mock_documents: AsyncMock, mock_refreshes: AsyncMock) -> None:
        as_of = datetime.now(UTC)
        market_ticks = [
            MarketTick(
                ticker="X:BTCUSD",
                asset_class=AssetClass.CRYPTO,
                timestamp=as_of - timedelta(hours=index * 4),
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("95"),
                close=Decimal(str(value)),
                volume=1_000,
            )
            for index, value in enumerate([110, 108, 106, 104, 103, 102, 100, 98, 97, 96])
        ]
        portfolio_snapshot = SnapshotRecord(
            data={
                "name": "primary",
                "benchmark": "BTC",
                "positions": [
                    {"ticker": "X:BTCUSD", "quantity": 1.0, "average_cost": 100.0, "asset_class": "crypto"},
                ],
                "constraints": {"max_crypto_weight": 0.8},
            },
            as_of=as_of,
            computed_at=as_of,
            stored_at=as_of,
            feature_version="portfolio-v1",
            provider_set=("internal",),
        )
        order_book_snapshot = SnapshotRecord(
            data={"best_bid": 109.5, "best_ask": 110.5},
            as_of=as_of,
            computed_at=as_of,
            stored_at=as_of,
            feature_version="orderbook-v1",
            provider_set=("coinapi",),
        )
        mock_store.get_market_snapshot.return_value = SnapshotRecord(
            data=market_ticks,
            as_of=as_of,
            computed_at=as_of,
            stored_at=as_of,
            feature_version="market-v1",
            provider_set=("coinapi",),
        )
        mock_store.get_market_ticks.return_value = market_ticks
        mock_store.get_market_regime_snapshot.return_value = None
        mock_store.get_world_state_snapshot.return_value = None
        mock_documents.get_portfolio_snapshot.return_value = portfolio_snapshot
        mock_documents.get_order_book_snapshot.return_value = order_book_snapshot
        mock_documents.get_normalized_news.return_value = SimpleNamespace(items=[{"headline": "BTC demand holds"}])
        mock_documents.get_social_posts.return_value = SimpleNamespace(items=[{"headline": "BTC buzz"}])
        mock_documents.get_exchange_announcements.return_value = SimpleNamespace(items=[])
        mock_documents.get_policy_documents_as_of.return_value = SimpleNamespace(items=[{"headline": "RBI steady"}])

        use_case = ReplayDecisionUseCase(documents=mock_documents, store=mock_store, refreshes=mock_refreshes)
        result = await use_case.execute("X:BTCUSD", as_of=as_of.isoformat(), portfolio_name="primary")

        assert result.status == "ready"
        assert result.data["decision_packet"]["action"] in {"BUY", "NO_TRADE"}
        assert "freshness_summary" in result.data
        assert "risk_verdict" in result.data
        assert "score_breakdown" in result.data


class TestLegacyCompatibility:
    @pytest.mark.asyncio
    async def test_legacy_company_query_hydrates_from_live_source(
        self,
        mock_store: AsyncMock,
    ) -> None:
        source = AsyncMock()
        source.fetch_company_details.return_value = {"name": "Infosys Limited"}
        mock_store.get_company.return_value = None

        use_case = LegacyQueryCompanyUseCase(reader=mock_store, source=source, writer=mock_store)
        result = await use_case.execute("INFY")

        assert result.name == "Infosys Limited"
        mock_store.save_company.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_v2_ingest_market_use_case_enqueues_refreshes(
        self,
        mock_refreshes: AsyncMock,
    ) -> None:
        use_case = IngestMarketDataUseCase(refreshes=mock_refreshes)
        enqueued = await use_case.execute(["AAPL", "MSFT"])

        assert enqueued == 2
        assert mock_refreshes.request_refresh.await_count == 2


class TestBuilders:
    @pytest.mark.asyncio
    async def test_feature_builder_persists_fred_macro_points(
        self,
        mock_store: AsyncMock,
        mock_documents: AsyncMock,
        mock_events: AsyncMock,
    ) -> None:
        mock_documents.get_latest_provider_document.return_value = {
            "payload": {
                "observations": [
                    {"series_id": "DFF", "date": "2026-03-15", "value": "4.5"},
                ]
            }
        }

        use_case = FeatureBuilderUseCase(store=mock_store, documents=mock_documents, events=mock_events)
        await use_case.execute({"provider": "fred", "entity_type": "world_state", "entity_id": "global"})

        mock_store.save_macro_series_points.assert_awaited_once()
        mock_events.publish.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_insight_builder_creates_world_state_snapshot(
        self,
        mock_store: AsyncMock,
        mock_documents: AsyncMock,
        mock_events: AsyncMock,
    ) -> None:
        mock_store.get_latest_macro_series.return_value = {
            "DFF": [{"date": "2026-03-15", "value": 4.5}],
            "CPIAUCSL": [{"date": "2026-03-15", "value": 312.0}] * 13,
            "VIXCLS": [{"date": "2026-03-15", "value": 18.0}],
            "WALCL": [{"date": "2026-03-15", "value": 8_800_000.0}, {"date": "2026-03-14", "value": 8_000_000.0}],
            "DCOILWTICO": [{"date": "2026-03-15", "value": 70.0}, {"date": "2026-03-14", "value": 60.0}],
        }

        use_case = InsightBuilderUseCase(store=mock_store, documents=mock_documents, events=mock_events)
        await use_case.execute({"domain": "world_state", "entity_id": "global"})

        mock_store.save_world_state.assert_awaited_once()
        mock_documents.update_refresh_status.assert_awaited_once_with("world_state", "global", "ready")


class TestEntitiesStillBehaveAsExpected:
    def test_market_tick_normalization_shape(self) -> None:
        from data_fabric.application.ingestion import normalize_market_bars

        bars = normalize_market_bars(
            [
                {
                    "ticker": "AAPL",
                    "asset_class": "equity",
                    "timestamp": "2024-01-15T00:00:00+00:00",
                    "open": Decimal("185.50"),
                    "high": Decimal("187.00"),
                    "low": Decimal("184.00"),
                    "close": Decimal("186.75"),
                    "volume": 50_000_000,
                }
            ]
        )

        assert bars[0].ticker == "AAPL"
        assert bars[0].close == Decimal("186.75")


class TestPolygonMarketSource:
    @pytest.mark.asyncio
    async def test_skips_unsupported_internal_market_symbols_without_network_call(self) -> None:
        source = PolygonMarketSource(api_key="test-key")
        source._client.get = AsyncMock()  # type: ignore[method-assign]

        bars = await source.fetch(tickers=["INDEX:NIFTY50", "CMD:CRUDE", "MACRO:US10Y"])

        assert bars == []
        source._client.get.assert_not_awaited()  # type: ignore[attr-defined]
        await source.close()

    @pytest.mark.asyncio
    async def test_treats_provider_404_as_empty_result(self) -> None:
        source = PolygonMarketSource(api_key="test-key")
        request = httpx.Request("GET", "https://api.massive.com/test")
        response = httpx.Response(status_code=404, request=request)
        source._client.get = AsyncMock(return_value=response)  # type: ignore[method-assign]

        bars = await source.fetch(tickers=["AAPL"])

        assert bars == []
        source._client.get.assert_awaited_once()  # type: ignore[attr-defined]
        await source.close()
