"""V2 snapshot-only API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from data_fabric.api.deps import (
    get_v2_ingest_use_case,
    get_v2_market_regime_use_case,
    get_v2_query_company_use_case,
    get_v2_query_country_use_case,
    get_v2_query_filings_use_case,
    get_v2_query_market_use_case,
    get_v2_query_news_use_case,
    get_v2_query_policy_events_use_case,
    get_v2_query_world_state_use_case,
    get_v2_search_policy_use_case,
)
from data_fabric.application import (
    IngestMarketDataUseCase,
    QueryCompanyFilingsUseCase,
    QueryCompanyNewsUseCase,
    QueryCompanyUseCase,
    QueryCountryUseCase,
    QueryMarketHistoryUseCase,
    QueryMarketRegimeUseCase,
    QueryPolicyEventsUseCase,
    QueryWorldStateUseCase,
    SearchPolicyUseCase,
    SnapshotRead,
)
from data_fabric.domain.entities import CompanyProfile, CountryProfile, MarketTick, WorldState

router = APIRouter(tags=["Data Fabric V2"])


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
