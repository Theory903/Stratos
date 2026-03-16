"""Dependency injection wiring for V1 and V2 data-fabric routes."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Request

from data_fabric.adapters.cache import RedisCacheStore
from data_fabric.adapters.database import PostgresDataStore
from data_fabric.adapters.document_store import MongoDocumentStore
from data_fabric.adapters.events import KafkaEventPublisher
from data_fabric.adapters.sources import FREDMacroSource, PolygonMarketSource, WorldBankCountrySource
from data_fabric.adapters.sources.oanda import OandaFXSource
from data_fabric.application import (
    IngestMarketDataUseCase,
    LegacyIngestMarketDataUseCase,
    LegacyQueryCompanyUseCase,
    LegacyQueryCountryUseCase,
    LegacyQueryWorldStateUseCase,
    QueryAnomalyUseCase,
    QueryCompanyFilingsUseCase,
    QueryCompanyNewsUseCase,
    QueryCompanyUseCase,
    QueryCompareEntityUseCase,
    QueryCompareMetricUseCase,
    QueryCountryUseCase,
    QueryDecisionQueueUseCase,
    QueryEventClustersUseCase,
    QueryEventPulseUseCase,
    QueryEventsFeedUseCase,
    QueryMarketHistoryUseCase,
    QueryMarketRegimeUseCase,
    QueryPortfolioDecisionLogUseCase,
    QueryPortfolioExposureUseCase,
    QueryPortfolioRiskUseCase,
    QueryPortfolioUseCase,
    QueryPolicyEventsUseCase,
    QuerySimilarRegimesUseCase,
    QueryWorldStateUseCase,
    RefreshRequestManager,
    RunPortfolioRebalanceUseCase,
    RunPortfolioScenarioUseCase,
    SearchPolicyUseCase,
    SearchEventsUseCase,
    UpsertPortfolioUseCase,
)
from data_fabric.config import Settings
from data_fabric.domain.services.validator import DataValidator


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_validator() -> DataValidator:
    return DataValidator()


def get_data_store(request: Request) -> PostgresDataStore:
    return request.app.state.data_store


def get_document_store(request: Request) -> MongoDocumentStore:
    return request.app.state.document_store


def get_cache(request: Request) -> RedisCacheStore:
    return request.app.state.cache


def get_event_publisher(request: Request) -> KafkaEventPublisher:
    return request.app.state.events


def get_market_source(request: Request) -> PolygonMarketSource:
    return request.app.state.market_source


def get_fred_source(request: Request) -> FREDMacroSource:
    return request.app.state.fred_source


def get_fx_source(request: Request) -> OandaFXSource:
    return request.app.state.fx_source


def get_country_source(request: Request) -> WorldBankCountrySource:
    return request.app.state.country_source


def get_refresh_manager(
    documents: MongoDocumentStore = Depends(get_document_store),
    events: KafkaEventPublisher = Depends(get_event_publisher),
) -> RefreshRequestManager:
    return RefreshRequestManager(documents=documents, events=events)


def get_v1_query_company_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    source: PolygonMarketSource = Depends(get_market_source),
) -> LegacyQueryCompanyUseCase:
    return LegacyQueryCompanyUseCase(reader=store, source=source, writer=store)


def get_v1_query_world_state_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    source: FREDMacroSource = Depends(get_fred_source),
) -> LegacyQueryWorldStateUseCase:
    return LegacyQueryWorldStateUseCase(reader=store, source=source, writer=store)


def get_v1_query_country_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    source: WorldBankCountrySource = Depends(get_country_source),
) -> LegacyQueryCountryUseCase:
    return LegacyQueryCountryUseCase(reader=store, source=source, writer=store)


def get_v1_ingest_use_case(
    source: PolygonMarketSource = Depends(get_market_source),
    store: PostgresDataStore = Depends(get_data_store),
    events: KafkaEventPublisher = Depends(get_event_publisher),
    validator: DataValidator = Depends(get_validator),
) -> LegacyIngestMarketDataUseCase:
    return LegacyIngestMarketDataUseCase(
        source=source,
        writer=store,
        events=events,
        validator=validator,
    )


def get_v2_query_company_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCompanyUseCase:
    return QueryCompanyUseCase(store=store, refreshes=refreshes)


def get_v2_query_world_state_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryWorldStateUseCase:
    return QueryWorldStateUseCase(store=store, refreshes=refreshes)


def get_v2_query_country_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCountryUseCase:
    return QueryCountryUseCase(store=store, refreshes=refreshes)


def get_v2_query_market_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryMarketHistoryUseCase:
    return QueryMarketHistoryUseCase(store=store, refreshes=refreshes)


def get_v2_query_filings_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCompanyFilingsUseCase:
    return QueryCompanyFilingsUseCase(documents=documents, refreshes=refreshes)


def get_v2_query_news_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCompanyNewsUseCase:
    return QueryCompanyNewsUseCase(documents=documents, refreshes=refreshes)


def get_v2_query_policy_events_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryPolicyEventsUseCase:
    return QueryPolicyEventsUseCase(documents=documents, refreshes=refreshes)


def get_v2_search_policy_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> SearchPolicyUseCase:
    return SearchPolicyUseCase(documents=documents, refreshes=refreshes)


def get_v2_market_regime_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryMarketRegimeUseCase:
    return QueryMarketRegimeUseCase(store=store, refreshes=refreshes)


def get_v2_events_feed_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryEventsFeedUseCase:
    return QueryEventsFeedUseCase(store=store, documents=documents, refreshes=refreshes)


def get_v2_events_search_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> SearchEventsUseCase:
    return SearchEventsUseCase(store=store, documents=documents, refreshes=refreshes)


def get_v2_event_clusters_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryEventClustersUseCase:
    return QueryEventClustersUseCase(store=store, documents=documents, refreshes=refreshes)


def get_v2_event_pulse_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryEventPulseUseCase:
    return QueryEventPulseUseCase(store=store, documents=documents, refreshes=refreshes)


def get_v2_compare_metric_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCompareMetricUseCase:
    return QueryCompareMetricUseCase(store=store, refreshes=refreshes)


def get_v2_compare_entity_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryCompareEntityUseCase:
    return QueryCompareEntityUseCase(store=store, refreshes=refreshes)


def get_v2_similar_regimes_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QuerySimilarRegimesUseCase:
    return QuerySimilarRegimesUseCase(store=store, refreshes=refreshes)


def get_v2_anomaly_use_case(
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryAnomalyUseCase:
    return QueryAnomalyUseCase(store=store, refreshes=refreshes)


def get_v2_portfolio_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryPortfolioUseCase:
    return QueryPortfolioUseCase(documents=documents, refreshes=refreshes)


def get_v2_upsert_portfolio_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
) -> UpsertPortfolioUseCase:
    return UpsertPortfolioUseCase(documents=documents)


def get_v2_portfolio_exposure_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryPortfolioExposureUseCase:
    return QueryPortfolioExposureUseCase(documents=documents, store=store, refreshes=refreshes)


def get_v2_portfolio_risk_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryPortfolioRiskUseCase:
    return QueryPortfolioRiskUseCase(documents=documents, store=store, refreshes=refreshes)


def get_v2_portfolio_scenario_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    store: PostgresDataStore = Depends(get_data_store),
) -> RunPortfolioScenarioUseCase:
    return RunPortfolioScenarioUseCase(documents=documents, store=store)


def get_v2_portfolio_rebalance_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    store: PostgresDataStore = Depends(get_data_store),
) -> RunPortfolioRebalanceUseCase:
    return RunPortfolioRebalanceUseCase(documents=documents, store=store)


def get_v2_portfolio_decision_log_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryPortfolioDecisionLogUseCase:
    return QueryPortfolioDecisionLogUseCase(documents=documents, refreshes=refreshes)


def get_v2_decision_queue_use_case(
    documents: MongoDocumentStore = Depends(get_document_store),
    store: PostgresDataStore = Depends(get_data_store),
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> QueryDecisionQueueUseCase:
    return QueryDecisionQueueUseCase(documents=documents, store=store, refreshes=refreshes)


def get_v2_ingest_use_case(
    refreshes: RefreshRequestManager = Depends(get_refresh_manager),
) -> IngestMarketDataUseCase:
    return IngestMarketDataUseCase(refreshes=refreshes)
