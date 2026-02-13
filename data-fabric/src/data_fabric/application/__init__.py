"""Application layer — use cases that orchestrate domain + ports."""

from __future__ import annotations

from data_fabric.domain.entities import CompanyProfile, MarketTick
from data_fabric.domain.errors import EntityNotFoundError
from data_fabric.ports.outbound import DataReader, DataWriter, EventPublisher, ExternalDataSource


class IngestMarketDataUseCase:
    """Ingest market data from an external source, normalize, and persist."""

    def __init__(
        self,
        source: ExternalDataSource,
        writer: DataWriter,
        events: EventPublisher,
    ) -> None:
        self._source = source
        self._writer = writer
        self._events = events

    async def execute(self, tickers: list[str]) -> int:
        raw = await self._source.fetch(tickers=tickers)
        ticks = [self._to_tick(r) for r in raw]
        await self._writer.save_market_ticks(ticks)
        await self._events.publish(
            topic="data.ingested",
            key=self._source.source_name,
            payload={"count": len(ticks), "source": self._source.source_name},
        )
        return len(ticks)

    @staticmethod
    def _to_tick(raw: dict) -> MarketTick:
        """Map raw API response to domain entity."""
        raise NotImplementedError("Implement per-source normalization")


class QueryCompanyUseCase:
    """Query a company profile from storage."""

    def __init__(self, reader: DataReader) -> None:
        self._reader = reader

    async def execute(self, ticker: str) -> CompanyProfile:
        profile = await self._reader.get_company(ticker)
        if profile is None:
            raise EntityNotFoundError("CompanyProfile", ticker)
        return profile
