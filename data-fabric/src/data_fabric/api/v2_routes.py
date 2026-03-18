"""V2 snapshot-only API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from data_fabric.api.deps import (
    get_v2_anomaly_use_case,
    get_v2_compare_entity_use_case,
    get_v2_compare_metric_use_case,
    get_v2_decision_queue_use_case,
    get_v2_decision_context_use_case,
    get_v2_event_clusters_use_case,
    get_v2_event_pulse_use_case,
    get_v2_events_feed_use_case,
    get_v2_query_exchange_announcements_use_case,
    get_v2_events_search_use_case,
    get_v2_ingest_use_case,
    get_v2_market_regime_use_case,
    get_v2_portfolio_decision_log_use_case,
    get_v2_portfolio_exposure_use_case,
    get_v2_portfolio_rebalance_use_case,
    get_v2_portfolio_risk_use_case,
    get_v2_portfolio_scenario_use_case,
    get_v2_provider_health_use_case,
    get_v2_portfolio_use_case,
    get_v2_query_company_use_case,
    get_v2_query_country_use_case,
    get_v2_query_filings_use_case,
    get_v2_query_market_use_case,
    get_v2_query_news_use_case,
    get_v2_query_order_book_use_case,
    get_v2_query_policy_events_use_case,
    get_v2_query_social_use_case,
    get_v2_replay_decision_use_case,
    get_v2_similar_regimes_use_case,
    get_v2_upsert_portfolio_use_case,
    get_v2_query_world_state_use_case,
    get_v2_search_policy_use_case,
)
from data_fabric.application import (
    IngestMarketDataUseCase,
    QueryAnomalyUseCase,
    QueryCompanyFilingsUseCase,
    QueryCompanyNewsUseCase,
    QueryCompanyUseCase,
    QueryCompareEntityUseCase,
    QueryCompareMetricUseCase,
    QueryCountryUseCase,
    QueryDecisionQueueUseCase,
    QueryDecisionContextUseCase,
    QueryEventClustersUseCase,
    QueryEventPulseUseCase,
    QueryExchangeAnnouncementsUseCase,
    QueryEventsFeedUseCase,
    QueryMarketHistoryUseCase,
    QueryMarketRegimeUseCase,
    QueryOrderBookUseCase,
    QueryPortfolioDecisionLogUseCase,
    QueryPortfolioExposureUseCase,
    QueryPortfolioRiskUseCase,
    QueryPortfolioUseCase,
    QueryPolicyEventsUseCase,
    QueryProviderHealthUseCase,
    QuerySocialFeedUseCase,
    QuerySimilarRegimesUseCase,
    QueryWorldStateUseCase,
    ReplayDecisionUseCase,
    RunPortfolioRebalanceUseCase,
    RunPortfolioScenarioUseCase,
    SearchPolicyUseCase,
    SearchEventsUseCase,
    SnapshotRead,
    UpsertPortfolioUseCase,
)
from data_fabric.domain.entities import CompanyProfile, CountryProfile, MarketTick, WorldState

router = APIRouter(tags=["Data Fabric V2"])


class EventsSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    scope: str = "global"


class PortfolioPositionsRequest(BaseModel):
    name: str = "primary"
    benchmark: str = "SPY"
    positions: list[dict[str, Any]]
    constraints: dict[str, Any] | None = None


class PortfolioScenarioRequest(BaseModel):
    name: str = "primary"
    scenario: str = "oil_sticky_india_btc"


@router.post("/ingest/market")
async def ingest_market_data_v2(
    tickers: list[str],
    use_case: IngestMarketDataUseCase = Depends(get_v2_ingest_use_case),
) -> dict[str, Any]:
    enqueued = await use_case.execute(tickers)
    return {"status": "accepted", "enqueued_count": enqueued}


@router.get("/world-state", response_model=None)
async def get_world_state_v2(
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryWorldStateUseCase = Depends(get_v2_query_world_state_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute()
    return _snapshot_http_response(response, result, _serialize_world_state, include_meta=include_meta)


@router.get("/company/{ticker}", response_model=None)
async def get_company_v2(
    ticker: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryCompanyUseCase = Depends(get_v2_query_company_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(ticker)
    return _snapshot_http_response(response, result, _serialize_company, include_meta=include_meta)


@router.get("/country/{country_code}", response_model=None)
async def get_country_v2(
    country_code: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryCountryUseCase = Depends(get_v2_query_country_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(country_code)
    return _snapshot_http_response(response, result, _serialize_country, include_meta=include_meta)


@router.get("/market/regime", response_model=None)
async def get_market_regime_v2(
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryMarketRegimeUseCase = Depends(get_v2_market_regime_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute()
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/market/{ticker}", response_model=None)
async def get_market_history_v2(
    ticker: str,
    response: Response,
    limit: int = 100,
    include_meta: bool = Query(default=False),
    use_case: QueryMarketHistoryUseCase = Depends(get_v2_query_market_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(ticker, limit=limit)
    return _snapshot_http_response(
        response,
        result,
        lambda items: [_serialize_market_tick(item) for item in items],
        include_meta=include_meta,
    )


@router.get("/company/{ticker}/filings", response_model=None)
async def get_company_filings_v2(
    ticker: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryCompanyFilingsUseCase = Depends(get_v2_query_filings_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(ticker)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/company/{ticker}/news", response_model=None)
async def get_company_news_v2(
    ticker: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryCompanyNewsUseCase = Depends(get_v2_query_news_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(ticker)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/news/{entity}", response_model=None)
async def get_news_v2(
    entity: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryCompanyNewsUseCase = Depends(get_v2_query_news_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(entity)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/social/{entity}", response_model=None)
async def get_social_v2(
    entity: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QuerySocialFeedUseCase = Depends(get_v2_query_social_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(entity)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/exchange/announcements/{entity}", response_model=None)
async def get_exchange_announcements_v2(
    entity: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryExchangeAnnouncementsUseCase = Depends(get_v2_query_exchange_announcements_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(entity)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/orderbook/{instrument}", response_model=None)
async def get_order_book_v2(
    instrument: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryOrderBookUseCase = Depends(get_v2_query_order_book_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(instrument)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/policy/events", response_model=None)
async def get_policy_events_v2(
    response: Response,
    scope: str = "global",
    include_meta: bool = Query(default=False),
    use_case: QueryPolicyEventsUseCase = Depends(get_v2_query_policy_events_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(scope)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/policy/search", response_model=None)
async def search_policy_v2(
    response: Response,
    q: str,
    scope: str = "global",
    include_meta: bool = Query(default=False),
    use_case: SearchPolicyUseCase = Depends(get_v2_search_policy_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(q, scope=scope)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/events/feed", response_model=None)
async def get_events_feed_v2(
    response: Response,
    scope: str = "global",
    include_meta: bool = Query(default=False),
    use_case: QueryEventsFeedUseCase = Depends(get_v2_events_feed_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(scope)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.post("/events/search", response_model=None)
async def search_events_v2(
    payload: EventsSearchRequest,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: SearchEventsUseCase = Depends(get_v2_events_search_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(payload.query, scope=payload.scope)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/events/clusters", response_model=None)
async def get_event_clusters_v2(
    response: Response,
    scope: str = "global",
    include_meta: bool = Query(default=False),
    use_case: QueryEventClustersUseCase = Depends(get_v2_event_clusters_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(scope)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/events/pulse/{scope}", response_model=None)
async def get_event_pulse_v2(
    scope: str,
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryEventPulseUseCase = Depends(get_v2_event_pulse_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(scope)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/compare/metric", response_model=None)
async def compare_metric_v2(
    response: Response,
    entity_type: str,
    metric: str,
    entity_id: str = "global",
    limit: int = 24,
    include_meta: bool = Query(default=False),
    use_case: QueryCompareMetricUseCase = Depends(get_v2_compare_metric_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(
        entity_type=entity_type,
        metric=metric,
        entity_id=entity_id,
        limit=limit,
    )
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/compare/entity", response_model=None)
async def compare_entity_v2(
    response: Response,
    entity_type: str,
    entity_id: str,
    include_meta: bool = Query(default=False),
    use_case: QueryCompareEntityUseCase = Depends(get_v2_compare_entity_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(entity_type=entity_type, entity_id=entity_id)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/history/similar-regimes", response_model=None)
async def similar_regimes_v2(
    response: Response,
    limit: int = 6,
    include_meta: bool = Query(default=False),
    use_case: QuerySimilarRegimesUseCase = Depends(get_v2_similar_regimes_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(limit=limit)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/anomalies/{entity}", response_model=None)
async def get_anomaly_v2(
    entity: str,
    response: Response,
    entity_type: str = "market",
    metric: str | None = None,
    include_meta: bool = Query(default=False),
    use_case: QueryAnomalyUseCase = Depends(get_v2_anomaly_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(entity=entity, entity_type=entity_type, metric=metric)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/portfolio", response_model=None)
async def get_portfolio_v2(
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryPortfolioUseCase = Depends(get_v2_portfolio_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.post("/portfolio/positions", response_model=None)
async def upsert_portfolio_positions_v2(
    payload: PortfolioPositionsRequest,
    use_case: UpsertPortfolioUseCase = Depends(get_v2_upsert_portfolio_use_case),
) -> dict[str, Any]:
    snapshot = await use_case.execute(
        name=payload.name,
        benchmark=payload.benchmark,
        positions=payload.positions,
        constraints=payload.constraints,
    )
    return {"status": "ok", "portfolio": snapshot}


@router.get("/portfolio/exposures", response_model=None)
async def get_portfolio_exposures_v2(
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryPortfolioExposureUseCase = Depends(get_v2_portfolio_exposure_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/portfolio/risk", response_model=None)
async def get_portfolio_risk_v2(
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryPortfolioRiskUseCase = Depends(get_v2_portfolio_risk_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.post("/portfolio/scenario", response_model=None)
async def run_portfolio_scenario_v2(
    payload: PortfolioScenarioRequest,
    use_case: RunPortfolioScenarioUseCase = Depends(get_v2_portfolio_scenario_use_case),
) -> dict[str, Any]:
    result = await use_case.execute(name=payload.name, scenario=payload.scenario)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Portfolio '{payload.name}' is not configured")
    return {"status": "ok", "scenario": result}


@router.post("/portfolio/rebalance", response_model=None)
async def run_portfolio_rebalance_v2(
    name: str = "primary",
    use_case: RunPortfolioRebalanceUseCase = Depends(get_v2_portfolio_rebalance_use_case),
) -> dict[str, Any]:
    result = await use_case.execute(name=name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Portfolio '{name}' is not configured")
    return {"status": "ok", "rebalance": result}


@router.get("/portfolio/decision-log", response_model=None)
async def get_portfolio_decision_log_v2(
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryPortfolioDecisionLogUseCase = Depends(get_v2_portfolio_decision_log_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(name)
    return _snapshot_http_response(response, result, list, include_meta=include_meta)


@router.get("/decision/queue", response_model=None)
async def get_decision_queue_v2(
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryDecisionQueueUseCase = Depends(get_v2_decision_queue_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/decision/context/{instrument}", response_model=None)
async def get_decision_context_v2(
    instrument: str,
    response: Response,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: QueryDecisionContextUseCase = Depends(get_v2_decision_context_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(instrument, portfolio_name=name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/providers/health", response_model=None)
async def get_provider_health_v2(
    response: Response,
    include_meta: bool = Query(default=False),
    use_case: QueryProviderHealthUseCase = Depends(get_v2_provider_health_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute()
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


@router.get("/replay/decision/{instrument}", response_model=None)
async def replay_decision_v2(
    instrument: str,
    response: Response,
    as_of: str,
    name: str = "primary",
    include_meta: bool = Query(default=False),
    use_case: ReplayDecisionUseCase = Depends(get_v2_replay_decision_use_case),
) -> JSONResponse | dict[str, Any]:
    result = await use_case.execute(instrument, as_of=as_of, portfolio_name=name)
    return _snapshot_http_response(response, result, lambda value: value, include_meta=include_meta)


def _snapshot_http_response(
    response: Response,
    result: SnapshotRead[Any],
    serializer,
    *,
    include_meta: bool,
) -> JSONResponse | dict[str, Any]:
    if result.status == "pending":
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "entity_type": result.meta.entity_type,
                "entity_id": result.meta.entity_id,
                "refresh_enqueued": result.meta.refresh_enqueued,
                "suggested_retry_seconds": result.meta.suggested_retry_seconds or 30,
            },
        )

    if result.meta.as_of is not None:
        response.headers["X-Data-As-Of"] = result.meta.as_of.isoformat()
    response.headers["X-Data-Freshness"] = result.meta.freshness
    response.headers["X-Refresh-Enqueued"] = str(result.meta.refresh_enqueued).lower()
    response.headers["X-Feature-Version"] = result.meta.feature_version or ""

    serialized = serializer(result.data)
    if not include_meta:
        return serialized
    return {
        "data": serialized,
        "meta": {
            "entity_type": result.meta.entity_type,
            "entity_id": result.meta.entity_id,
            "as_of": result.meta.as_of.isoformat() if result.meta.as_of else None,
            "freshness": result.meta.freshness,
            "refresh_enqueued": result.meta.refresh_enqueued,
            "feature_version": result.meta.feature_version,
            "provider_set": list(result.meta.provider_set),
        },
    }


def _serialize_company(profile: CompanyProfile) -> dict[str, Any]:
    return {
        "ticker": profile.ticker,
        "name": profile.name,
        "earnings_quality": profile.earnings_quality,
        "leverage_ratio": profile.leverage_ratio,
        "free_cash_flow_stability": profile.free_cash_flow_stability,
        "fraud_score": profile.fraud_score,
        "moat_score": profile.moat_score,
    }


def _serialize_country(profile: CountryProfile) -> dict[str, Any]:
    return {
        "country_code": profile.country_code,
        "debt_gdp": profile.debt_gdp,
        "fx_reserves": profile.fx_reserves,
        "fiscal_deficit": profile.fiscal_deficit,
        "political_stability": profile.political_stability,
        "currency_volatility": profile.currency_volatility,
    }


def _serialize_world_state(state: WorldState) -> dict[str, Any]:
    return {
        "interest_rate": state.interest_rate,
        "inflation": state.inflation,
        "liquidity_index": state.liquidity_index,
        "geopolitical_risk": state.geopolitical_risk,
        "volatility_index": state.volatility_index,
        "commodity_index": state.commodity_index,
    }


def _serialize_market_tick(tick: MarketTick) -> dict[str, Any]:
    return {
        "ticker": tick.ticker,
        "asset_class": tick.asset_class.value,
        "timestamp": tick.timestamp.isoformat(),
        "open": str(tick.open),
        "high": str(tick.high),
        "low": str(tick.low),
        "close": str(tick.close),
        "volume": tick.volume,
    }
