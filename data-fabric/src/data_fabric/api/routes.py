"""V1 API routes retained for backward compatibility."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from data_fabric.adapters.cache import RedisCacheStore
from data_fabric.adapters.database import PostgresDataStore
from data_fabric.api.deps import (
    get_cache,
    get_data_store,
    get_v1_ingest_use_case,
    get_v1_query_company_use_case,
    get_v1_query_country_use_case,
    get_v1_query_world_state_use_case,
)
from data_fabric.application import (
    LegacyIngestMarketDataUseCase,
    LegacyQueryCompanyUseCase,
    LegacyQueryCountryUseCase,
    LegacyQueryWorldStateUseCase,
)
from data_fabric.domain.errors import EntityNotFoundError

router = APIRouter(tags=["Data Fabric V1"])


class IngestRequest(BaseModel):
    source: str = "massive"
    tickers: list[str]


class IngestResponse(BaseModel):
    ingested_count: int
    source: str


class CompanyResponse(BaseModel):
    ticker: str
    name: str
    earnings_quality: float
    leverage_ratio: float
    free_cash_flow_stability: float
    fraud_score: float
    moat_score: float


class WorldStateResponse(BaseModel):
    interest_rate: float
    inflation: float
    liquidity_index: float
    geopolitical_risk: float
    volatility_index: float
    commodity_index: float


class CountryResponse(BaseModel):
    country_code: str
    debt_gdp: float
    fx_reserves: float
    fiscal_deficit: float
    political_stability: float
    currency_volatility: float


class MarketTickResponse(BaseModel):
    ticker: str
    asset_class: str
    timestamp: str
    open: str
    high: str
    low: str
    close: str
    volume: int


@router.post("/ingest/market", response_model=IngestResponse)
async def ingest_market_data(
    request: IngestRequest,
    use_case: LegacyIngestMarketDataUseCase = Depends(get_v1_ingest_use_case),
) -> IngestResponse:
    count = await use_case.execute(request.tickers)
    return IngestResponse(ingested_count=count, source=request.source)


@router.get("/company/{ticker}", response_model=CompanyResponse)
async def get_company(
    ticker: str,
    cache: RedisCacheStore = Depends(get_cache),
    use_case: LegacyQueryCompanyUseCase = Depends(get_v1_query_company_use_case),
) -> CompanyResponse:
    cache_key = f"company:{ticker}"
    cached = await cache.get(cache_key)
    if cached:
        return CompanyResponse(**json.loads(cached))

    try:
        profile = await use_case.execute(ticker)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    response = CompanyResponse(
        ticker=profile.ticker,
        name=profile.name,
        earnings_quality=profile.earnings_quality,
        leverage_ratio=profile.leverage_ratio,
        free_cash_flow_stability=profile.free_cash_flow_stability,
        fraud_score=profile.fraud_score,
        moat_score=profile.moat_score,
    )
    await cache.set(cache_key, json.dumps(response.model_dump()), ttl_seconds=300)
    return response


@router.get("/world-state", response_model=WorldStateResponse)
async def get_world_state(
    use_case: LegacyQueryWorldStateUseCase = Depends(get_v1_query_world_state_use_case),
) -> WorldStateResponse:
    state = await use_case.execute()
    return WorldStateResponse(
        interest_rate=state.interest_rate,
        inflation=state.inflation,
        liquidity_index=state.liquidity_index,
        geopolitical_risk=state.geopolitical_risk,
        volatility_index=state.volatility_index,
        commodity_index=state.commodity_index,
    )


@router.get("/country/{country_code}", response_model=CountryResponse)
async def get_country(
    country_code: str,
    use_case: LegacyQueryCountryUseCase = Depends(get_v1_query_country_use_case),
) -> CountryResponse:
    try:
        profile = await use_case.execute(country_code)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CountryResponse(
        country_code=profile.country_code,
        debt_gdp=profile.debt_gdp,
        fx_reserves=profile.fx_reserves,
        fiscal_deficit=profile.fiscal_deficit,
        political_stability=profile.political_stability,
        currency_volatility=profile.currency_volatility,
    )


@router.get("/market/{ticker}", response_model=list[MarketTickResponse])
async def get_market_history(
    ticker: str,
    limit: int = 100,
    store: PostgresDataStore = Depends(get_data_store),
) -> list[MarketTickResponse]:
    ticks = await store.get_market_ticks(ticker, limit=limit)
    return [
        MarketTickResponse(
            ticker=tick.ticker,
            asset_class=tick.asset_class.value,
            timestamp=tick.timestamp.isoformat(),
            open=str(tick.open),
            high=str(tick.high),
            low=str(tick.low),
            close=str(tick.close),
            volume=tick.volume,
        )
        for tick in ticks
    ]
