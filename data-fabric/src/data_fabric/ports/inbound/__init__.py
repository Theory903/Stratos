"""Inbound ports — driven by API layer, implemented by application use cases."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from data_fabric.domain.entities import CompanyProfile, CountryProfile, MarketTick, WorldState


@runtime_checkable
class IngestDataPort(Protocol):
    """Inbound port for data ingestion commands."""

    async def ingest_market_data(self, source: str, tickers: list[str]) -> int: ...
    async def ingest_macro_data(self, source: str, indicators: list[str]) -> int: ...


@runtime_checkable
class QueryDataPort(Protocol):
    """Inbound port for data queries."""

    async def get_company_profile(self, ticker: str) -> CompanyProfile: ...
    async def get_country_profile(self, country_code: str) -> CountryProfile: ...
    async def get_world_state(self) -> WorldState: ...
    async def get_market_history(self, ticker: str, limit: int) -> list[MarketTick]: ...
