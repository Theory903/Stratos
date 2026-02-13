"""Outbound ports — abstract interfaces that adapters MUST implement.

These protocols define the contracts between domain/application
and infrastructure. Domain never imports adapters directly (D in SOLID).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from data_fabric.domain.entities import CompanyProfile, CountryProfile, MarketTick, WorldState


# ── Storage Port (I: segregated into read/write) ──


@runtime_checkable
class DataReader(Protocol):
    """Read-only data access — Interface Segregation."""

    async def get_company(self, ticker: str) -> CompanyProfile | None: ...
    async def get_country(self, country_code: str) -> CountryProfile | None: ...
    async def get_world_state(self) -> WorldState | None: ...
    async def get_market_ticks(self, ticker: str, limit: int = 100) -> list[MarketTick]: ...


@runtime_checkable
class DataWriter(Protocol):
    """Write-only data access — Interface Segregation."""

    async def save_company(self, profile: CompanyProfile) -> None: ...
    async def save_country(self, profile: CountryProfile) -> None: ...
    async def save_world_state(self, state: WorldState) -> None: ...
    async def save_market_ticks(self, ticks: list[MarketTick]) -> None: ...


# ── Cache Port ──


@runtime_checkable
class CacheStore(Protocol):
    """Caching abstraction."""

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl_seconds: int = 300) -> None: ...
    async def delete(self, key: str) -> None: ...


# ── Event Port ──


@runtime_checkable
class EventPublisher(Protocol):
    """Publish domain events to message bus."""

    async def publish(self, topic: str, key: str, payload: dict) -> None: ...


# ── External Data Source Port (O/C: add new sources without modifying existing) ──


@runtime_checkable
class ExternalDataSource(Protocol):
    """Abstract interface for any external data provider."""

    @property
    def source_name(self) -> str: ...

    async def fetch(self, **params: object) -> list[dict]: ...
    async def health_check(self) -> bool: ...
