"""Legacy V1 use cases kept for backward-compatible API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from data_fabric.domain.entities import AssetClass, CompanyProfile, CountryProfile, MarketTick, WorldState
from data_fabric.domain.errors import EntityNotFoundError, ValidationError
from data_fabric.domain.services.validator import DataValidator

logger = logging.getLogger(__name__)


class LegacyIngestMarketDataUseCase:
    """Original synchronous market ingest used by V1 endpoints."""

    def __init__(
        self,
        source: Any,
        writer: Any,
        events: Any,
        validator: DataValidator | None = None,
    ) -> None:
        self._source = source
        self._writer = writer
        self._events = events
        self._validator = validator or DataValidator()

    async def execute(self, tickers: list[str]) -> int:
        raw = await self._source.fetch(tickers=tickers)
        ticks = [self._to_tick(item) for item in raw]
        valid_ticks: list[MarketTick] = []
        for tick in ticks:
            self._validator.validate_tick(tick)
            valid_ticks.append(tick)

        if not valid_ticks:
            return 0

        await self._writer.save_market_ticks(valid_ticks)
        await self._events.publish(
            topic="data.market.ingested",
            key=self._source.source_name,
            payload={"count": len(valid_ticks), "tickers": tickers},
        )
        return len(valid_ticks)

    @staticmethod
    def _to_tick(raw: dict[str, Any]) -> MarketTick:
        return MarketTick(
            ticker=raw["ticker"],
            asset_class=AssetClass(raw.get("asset_class", "equity")),
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            open=Decimal(raw["open"]),
            high=Decimal(raw["high"]),
            low=Decimal(raw["low"]),
            close=Decimal(raw["close"]),
            volume=int(raw["volume"]),
        )


class LegacyQueryCompanyUseCase:
    """V1 company query with live fallback."""

    def __init__(self, reader: Any, source: Any, writer: Any) -> None:
        self._reader = reader
        self._source = source
        self._writer = writer

    async def execute(self, ticker: str) -> CompanyProfile:
        profile = await self._reader.get_company(ticker.upper())
        if profile is not None:
            return profile

        try:
            details = await self._source.fetch_company_details(ticker.upper())
            profile = CompanyProfile(
                ticker=ticker.upper(),
                name=details["name"],
                earnings_quality=0.5,
                leverage_ratio=0.5,
                free_cash_flow_stability=0.5,
                fraud_score=0.1,
                moat_score=0.5,
            )
            await self._writer.save_company(profile)
            return profile
        except Exception as exc:
            logger.exception("legacy company fallback failed for %s", ticker)
            raise EntityNotFoundError("CompanyProfile", ticker) from exc


class LegacyQueryCountryUseCase:
    """V1 country query with live fallback."""

    def __init__(self, reader: Any, source: Any, writer: Any) -> None:
        self._reader = reader
        self._source = source
        self._writer = writer

    async def execute(self, country_code: str) -> CountryProfile:
        normalized = country_code.upper()
        profile = await self._reader.get_country(normalized)
        if profile is not None:
            return profile

        try:
            details = await self._source.fetch_country_profile(normalized)
            profile = CountryProfile(
                country_code=normalized,
                debt_gdp=float(details["debt_gdp"]),
                fx_reserves=float(details["fx_reserves"]),
                fiscal_deficit=float(details["fiscal_deficit"]),
                political_stability=float(details["political_stability"]),
                currency_volatility=float(details["currency_volatility"]),
            )
            await self._writer.save_country(profile)
            return profile
        except Exception as exc:
            logger.exception("legacy country fallback failed for %s", normalized)
            raise EntityNotFoundError("CountryProfile", normalized) from exc


class LegacyQueryWorldStateUseCase:
    """V1 world-state query with live fallback."""

    def __init__(self, reader: Any, source: Any, writer: Any) -> None:
        self._reader = reader
        self._source = source
        self._writer = writer

    async def execute(self) -> WorldState:
        state = await self._reader.get_world_state()
        if state is not None:
            return state

        raw_indicators = await self._source.fetch(
            indicators=["DFF", "CPIAUCSL", "VIXCLS", "WALCL", "DCOILWTICO"]
        )
        grouped = self._group_indicator_series(raw_indicators)
        now = datetime.now(UTC)
        state = WorldState(
            interest_rate=(self._latest_value(grouped, "DFF") or 0.0) / 100.0,
            inflation=self._compute_year_over_year_change(grouped, "CPIAUCSL"),
            volatility_index=self._latest_value(grouped, "VIXCLS") or 0.0,
            liquidity_index=self._normalize_latest_value(grouped, "WALCL"),
            geopolitical_risk=self._risk_proxy_from_vix(self._latest_value(grouped, "VIXCLS")),
            commodity_index=self._normalize_latest_value(grouped, "DCOILWTICO"),
            timestamp=now,
            stored_at=now,
        )
        await self._writer.save_world_state(state)
        return state

    @staticmethod
    def _group_indicator_series(raw_indicators: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for observation in raw_indicators:
            grouped.setdefault(str(observation["series_id"]), []).append(
                {"date": str(observation["date"]), "value": float(observation["value"])}
            )
        return grouped

    @staticmethod
    def _latest_value(grouped: dict[str, list[dict[str, Any]]], series_id: str) -> float | None:
        values = grouped.get(series_id, [])
        if not values:
            return None
        return float(values[0]["value"])

    @staticmethod
    def _compute_year_over_year_change(
        grouped: dict[str, list[dict[str, Any]]],
        series_id: str,
    ) -> float:
        values = grouped.get(series_id, [])
        if len(values) < 13:
            return 0.0
        latest = float(values[0]["value"])
        trailing_year = float(values[12]["value"])
        if trailing_year == 0:
            return 0.0
        return (latest / trailing_year) - 1.0

    @staticmethod
    def _normalize_latest_value(
        grouped: dict[str, list[dict[str, Any]]],
        series_id: str,
    ) -> float:
        values = [float(item["value"]) for item in grouped.get(series_id, [])]
        if not values:
            return 0.5
        latest = values[0]
        lower = min(values)
        upper = max(values)
        if upper == lower:
            return 0.5
        return max(0.0, min(1.0, (latest - lower) / (upper - lower)))

    @staticmethod
    def _risk_proxy_from_vix(latest_vix: float | None) -> float:
        if latest_vix is None:
            return 0.5
        return max(0.0, min(1.0, latest_vix / 40.0))


class SaveCompanyUseCase:
    """Persist a company profile with basic validation."""

    def __init__(self, writer: Any, events: Any) -> None:
        self._writer = writer
        self._events = events

    async def execute(self, profile: CompanyProfile) -> None:
        if not profile.ticker:
            raise ValidationError("ticker", "Ticker cannot be empty")
        if not 0.0 <= profile.fraud_score <= 1.0:
            raise ValidationError("fraud_score", "Must be between 0 and 1")
        await self._writer.save_company(profile)
        await self._events.publish(
            topic="data.company.updated",
            key=profile.ticker,
            payload={"ticker": profile.ticker, "name": profile.name},
        )


class SaveCountryUseCase:
    """Persist a country profile with basic validation."""

    def __init__(self, writer: Any, events: Any) -> None:
        self._writer = writer
        self._events = events

    async def execute(self, profile: CountryProfile) -> None:
        if not profile.country_code or len(profile.country_code) > 3:
            raise ValidationError("country_code", "Must be 1-3 character country code")
        await self._writer.save_country(profile)
        await self._events.publish(
            topic="data.country.updated",
            key=profile.country_code,
            payload={"country_code": profile.country_code},
        )


class SaveWorldStateUseCase:
    """Persist a world-state snapshot."""

    def __init__(self, writer: Any, events: Any) -> None:
        self._writer = writer
        self._events = events

    async def execute(self, state: WorldState) -> None:
        await self._writer.save_world_state(state)
        await self._events.publish(
            topic="data.worldstate.updated",
            key="global",
            payload={"interest_rate": state.interest_rate, "inflation": state.inflation},
        )
