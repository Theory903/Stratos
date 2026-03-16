"""Timescale/Postgres adapter for normalized feature and insight tables."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from data_fabric.adapters.database.models import (
    CompanyFactPointModel,
    CompanyFeatureSnapshotModel,
    CountryFeatureSnapshotModel,
    CountryIndicatorPointModel,
    MacroSeriesPointModel,
    MarketBarModel,
    MarketRegimeSnapshotModel,
    PolicyWatchSnapshotModel,
    WorldStateSnapshotModel,
)
from data_fabric.domain.entities import (
    AssetClass,
    CompanyProfile,
    CountryProfile,
    MarketTick,
    WorldState,
)
from data_fabric.domain.value_objects import SnapshotRecord


def _serialize_provider_set(provider_set: tuple[str, ...] | list[str] | None) -> str:
    return ",".join(sorted({item for item in (provider_set or []) if item}))


def _deserialize_provider_set(provider_set: str | None) -> tuple[str, ...]:
    if not provider_set:
        return ()
    return tuple(item for item in provider_set.split(",") if item)


class PostgresDataStore:
    """Async relational store for feature and insight snapshots."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_company(self, ticker: str, as_of: datetime | None = None) -> CompanyProfile | None:
        snapshot = await self.get_company_snapshot(ticker, as_of=as_of)
        return snapshot.data if snapshot else None

    async def get_country(self, country_code: str, as_of: datetime | None = None) -> CountryProfile | None:
        snapshot = await self.get_country_snapshot(country_code, as_of=as_of)
        return snapshot.data if snapshot else None

    async def get_world_state(self, as_of: datetime | None = None) -> WorldState | None:
        snapshot = await self.get_world_state_snapshot(as_of=as_of)
        return snapshot.data if snapshot else None

    async def get_company_snapshot(
        self,
        ticker: str,
        as_of: datetime | None = None,
    ) -> SnapshotRecord[CompanyProfile] | None:
        async with self._session_factory() as session:
            stmt = select(CompanyFeatureSnapshotModel).where(
                CompanyFeatureSnapshotModel.ticker == ticker.upper()
            )
            if as_of:
                stmt = stmt.where(CompanyFeatureSnapshotModel.stored_at <= as_of)
            stmt = stmt.order_by(
                desc(CompanyFeatureSnapshotModel.computed_at),
                desc(CompanyFeatureSnapshotModel.stored_at),
            )
            result = await session.execute(stmt.limit(1))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return SnapshotRecord(
                data=CompanyProfile(
                    ticker=model.ticker,
                    name=model.name,
                    earnings_quality=model.earnings_quality,
                    leverage_ratio=model.leverage_ratio,
                    free_cash_flow_stability=model.free_cash_flow_stability,
                    fraud_score=model.fraud_score,
                    moat_score=model.moat_score,
                    stored_at=model.stored_at,
                ),
                as_of=model.computed_at,
                computed_at=model.computed_at,
                stored_at=model.stored_at,
                feature_version=model.feature_version,
                source_window_start=model.source_window_start,
                source_window_end=model.source_window_end,
                provider_set=_deserialize_provider_set(model.provider_set),
            )

    async def get_country_snapshot(
        self,
        country_code: str,
        as_of: datetime | None = None,
    ) -> SnapshotRecord[CountryProfile] | None:
        async with self._session_factory() as session:
            stmt = select(CountryFeatureSnapshotModel).where(
                CountryFeatureSnapshotModel.country_code == country_code.upper()
            )
            if as_of:
                stmt = stmt.where(CountryFeatureSnapshotModel.stored_at <= as_of)
            stmt = stmt.order_by(
                desc(CountryFeatureSnapshotModel.computed_at),
                desc(CountryFeatureSnapshotModel.stored_at),
            )
            result = await session.execute(stmt.limit(1))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return SnapshotRecord(
                data=CountryProfile(
                    country_code=model.country_code,
                    debt_gdp=model.debt_gdp,
                    fx_reserves=model.fx_reserves,
                    fiscal_deficit=model.fiscal_deficit,
                    political_stability=model.political_stability,
                    currency_volatility=model.currency_volatility,
                    stored_at=model.stored_at,
                ),
                as_of=model.computed_at,
                computed_at=model.computed_at,
                stored_at=model.stored_at,
                feature_version=model.feature_version,
                source_window_start=model.source_window_start,
                source_window_end=model.source_window_end,
                provider_set=_deserialize_provider_set(model.provider_set),
            )

    async def get_world_state_snapshot(
        self,
        as_of: datetime | None = None,
    ) -> SnapshotRecord[WorldState] | None:
        async with self._session_factory() as session:
            stmt = select(WorldStateSnapshotModel)
            if as_of:
                stmt = stmt.where(WorldStateSnapshotModel.stored_at <= as_of)
            stmt = stmt.order_by(
                desc(WorldStateSnapshotModel.computed_at),
                desc(WorldStateSnapshotModel.stored_at),
            )
            result = await session.execute(stmt.limit(1))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return SnapshotRecord(
                data=WorldState(
                    interest_rate=model.interest_rate,
                    inflation=model.inflation,
                    liquidity_index=model.liquidity_index,
                    geopolitical_risk=model.geopolitical_risk,
                    volatility_index=model.volatility_index,
                    commodity_index=model.commodity_index,
                    timestamp=model.timestamp,
                    stored_at=model.stored_at,
                ),
                as_of=model.computed_at,
                computed_at=model.computed_at,
                stored_at=model.stored_at,
                feature_version=model.feature_version,
                source_window_start=model.source_window_start,
                source_window_end=model.source_window_end,
                provider_set=_deserialize_provider_set(model.provider_set),
            )

    async def get_market_ticks(
        self,
        ticker: str,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> list[MarketTick]:
        async with self._session_factory() as session:
            latest_versions = select(
                MarketBarModel.id.label("id"),
                func.row_number()
                .over(
                    partition_by=(MarketBarModel.ticker, MarketBarModel.timestamp),
                    order_by=desc(MarketBarModel.stored_at),
                )
                .label("version_rank"),
            ).where(MarketBarModel.ticker == ticker.upper())
            if as_of:
                latest_versions = latest_versions.where(MarketBarModel.stored_at <= as_of)

            latest_versions_subquery = latest_versions.subquery()
            stmt = (
                select(MarketBarModel)
                .join(latest_versions_subquery, MarketBarModel.id == latest_versions_subquery.c.id)
                .where(latest_versions_subquery.c.version_rank == 1)
                .order_by(desc(MarketBarModel.timestamp), desc(MarketBarModel.stored_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [self._to_tick_entity(model) for model in result.scalars().all()]

    async def get_market_snapshot(
        self,
        ticker: str,
        *,
        limit: int = 100,
    ) -> SnapshotRecord[list[MarketTick]] | None:
        ticks = await self.get_market_ticks(ticker, limit=limit)
        if not ticks:
            return None
        async with self._session_factory() as session:
            stmt = (
                select(MarketBarModel)
                .where(MarketBarModel.ticker == ticker.upper())
                .order_by(desc(MarketBarModel.stored_at))
            )
            result = await session.execute(stmt.limit(1))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return SnapshotRecord(
                data=ticks,
                as_of=model.stored_at,
                computed_at=model.stored_at,
                stored_at=model.stored_at,
                feature_version=model.feature_version,
                provider_set=_deserialize_provider_set(model.provider_set),
            )

    async def get_latest_macro_series(
        self,
        series_ids: list[str],
    ) -> dict[str, list[dict[str, object]]]:
        async with self._session_factory() as session:
            stmt = (
                select(MacroSeriesPointModel)
                .where(MacroSeriesPointModel.series_id.in_(series_ids))
                .order_by(
                    MacroSeriesPointModel.series_id,
                    desc(MacroSeriesPointModel.observed_at),
                    desc(MacroSeriesPointModel.stored_at),
                )
            )
            result = await session.execute(stmt)
            grouped: dict[str, list[dict[str, object]]] = {series_id: [] for series_id in series_ids}
            for row in result.scalars().all():
                grouped.setdefault(row.series_id, []).append(
                    {"date": row.observed_at.isoformat(), "value": float(row.value)}
                )
            return grouped

    async def get_market_regime_snapshot(self) -> SnapshotRecord[dict] | None:
        async with self._session_factory() as session:
            stmt = select(MarketRegimeSnapshotModel).order_by(
                desc(MarketRegimeSnapshotModel.computed_at),
                desc(MarketRegimeSnapshotModel.stored_at),
            )
            result = await session.execute(stmt.limit(1))
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return SnapshotRecord(
                data={
                    "regime_label": model.regime_label,
                    "confidence": model.confidence,
                    "factor_summary": model.factor_summary,
                },
                as_of=model.computed_at,
                computed_at=model.computed_at,
                stored_at=model.stored_at,
                feature_version=model.feature_version,
                source_window_start=model.source_window_start,
                source_window_end=model.source_window_end,
                provider_set=_deserialize_provider_set(model.provider_set),
            )

    async def save_company(self, profile: CompanyProfile) -> None:
        await self.save_company_snapshot(profile, feature_version="manual-company", provider_set=("manual",))

    async def save_country(self, profile: CountryProfile) -> None:
        await self.save_country_snapshot(profile, feature_version="manual-country", provider_set=("manual",))

    async def save_world_state(self, state: WorldState, feature_version: str = "manual-world-state", provider_set: tuple[str, ...] = ("manual",)) -> None:
        async with self._session_factory() as session:
            session.add(
                WorldStateSnapshotModel(
                    interest_rate=state.interest_rate,
                    inflation=state.inflation,
                    liquidity_index=state.liquidity_index,
                    geopolitical_risk=state.geopolitical_risk,
                    volatility_index=state.volatility_index,
                    commodity_index=state.commodity_index,
                    timestamp=state.timestamp,
                    computed_at=state.stored_at,
                    stored_at=state.stored_at,
                    feature_version=feature_version,
                    provider_set=_serialize_provider_set(provider_set),
                )
            )
            await session.commit()

    async def save_company_snapshot(
        self,
        profile: CompanyProfile,
        *,
        feature_version: str,
        provider_set: tuple[str, ...] = (),
        source_window_start: datetime | None = None,
        source_window_end: datetime | None = None,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                CompanyFeatureSnapshotModel(
                    ticker=profile.ticker.upper(),
                    name=profile.name,
                    earnings_quality=profile.earnings_quality,
                    leverage_ratio=profile.leverage_ratio,
                    free_cash_flow_stability=profile.free_cash_flow_stability,
                    fraud_score=profile.fraud_score,
                    moat_score=profile.moat_score,
                    computed_at=profile.stored_at,
                    stored_at=profile.stored_at,
                    feature_version=feature_version,
                    source_window_start=source_window_start,
                    source_window_end=source_window_end,
                    provider_set=_serialize_provider_set(provider_set),
                )
            )
            await session.commit()

    async def save_country_snapshot(
        self,
        profile: CountryProfile,
        *,
        feature_version: str,
        provider_set: tuple[str, ...] = (),
        source_window_start: datetime | None = None,
        source_window_end: datetime | None = None,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                CountryFeatureSnapshotModel(
                    country_code=profile.country_code.upper(),
                    debt_gdp=profile.debt_gdp,
                    fx_reserves=profile.fx_reserves,
                    fiscal_deficit=profile.fiscal_deficit,
                    political_stability=profile.political_stability,
                    currency_volatility=profile.currency_volatility,
                    computed_at=profile.stored_at,
                    stored_at=profile.stored_at,
                    feature_version=feature_version,
                    source_window_start=source_window_start,
                    source_window_end=source_window_end,
                    provider_set=_serialize_provider_set(provider_set),
                )
            )
            await session.commit()

    async def save_market_ticks(
        self,
        ticks: list[MarketTick],
        feature_version: str = "market-bars-v1",
        provider_set: tuple[str, ...] = (),
    ) -> None:
        async with self._session_factory() as session:
            session.add_all(
                [
                    MarketBarModel(
                        ticker=tick.ticker.upper(),
                        asset_class=tick.asset_class.value,
                        timestamp=tick.timestamp,
                        open=Decimal(str(tick.open)),
                        high=Decimal(str(tick.high)),
                        low=Decimal(str(tick.low)),
                        close=Decimal(str(tick.close)),
                        volume=tick.volume,
                        feature_version=feature_version,
                        provider_set=_serialize_provider_set(provider_set),
                        stored_at=tick.stored_at,
                    )
                    for tick in ticks
                ]
            )
            await session.commit()

    async def save_macro_series_points(
        self,
        observations: list[dict[str, object]],
        *,
        provider_set: tuple[str, ...] = (),
        feature_version: str = "macro-v1",
    ) -> None:
        async with self._session_factory() as session:
            session.add_all(
                [
                    MacroSeriesPointModel(
                        series_id=str(observation["series_id"]),
                        observed_at=self._coerce_date(str(observation["date"])),
                        value=float(observation["value"]),
                        provider_set=_serialize_provider_set(provider_set),
                        feature_version=feature_version,
                    )
                    for observation in observations
                ]
            )
            await session.commit()

    async def save_company_fact_points(
        self,
        *,
        ticker: str,
        facts: list[dict[str, object]],
        provider_set: tuple[str, ...] = (),
        feature_version: str = "company-facts-v1",
    ) -> None:
        async with self._session_factory() as session:
            session.add_all(
                [
                    CompanyFactPointModel(
                        ticker=ticker.upper(),
                        fact_name=str(fact["fact_name"]),
                        period_end=fact["period_end"],
                        value=float(fact["value"]),
                        unit=str(fact.get("unit", "USD")),
                        provider_set=_serialize_provider_set(provider_set),
                        feature_version=feature_version,
                    )
                    for fact in facts
                ]
            )
            await session.commit()

    async def save_country_indicator_points(
        self,
        *,
        country_code: str,
        indicators: dict[str, float],
        provider_set: tuple[str, ...] = (),
        feature_version: str = "country-indicators-v1",
    ) -> None:
        async with self._session_factory() as session:
            today = datetime.now(timezone.utc).date()
            session.add_all(
                [
                    CountryIndicatorPointModel(
                        country_code=country_code.upper(),
                        indicator_code=indicator_code,
                        observed_at=today,
                        value=value,
                        provider_set=_serialize_provider_set(provider_set),
                        feature_version=feature_version,
                    )
                    for indicator_code, value in indicators.items()
                ]
            )
            await session.commit()

    async def save_market_regime_snapshot(
        self,
        *,
        regime_label: str,
        confidence: float,
        factor_summary: dict,
        feature_version: str,
        provider_set: tuple[str, ...] = (),
        source_window_start: datetime | None = None,
        source_window_end: datetime | None = None,
    ) -> None:
        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            session.add(
                MarketRegimeSnapshotModel(
                    regime_label=regime_label,
                    confidence=confidence,
                    factor_summary=factor_summary,
                    computed_at=now,
                    stored_at=now,
                    feature_version=feature_version,
                    source_window_start=source_window_start,
                    source_window_end=source_window_end,
                    provider_set=_serialize_provider_set(provider_set),
                )
            )
            await session.commit()

    async def save_policy_watch_snapshot(
        self,
        *,
        scope: str,
        summary: str,
        events: list[dict],
        feature_version: str,
        provider_set: tuple[str, ...] = (),
    ) -> None:
        async with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            session.add(
                PolicyWatchSnapshotModel(
                    scope=scope,
                    summary=summary,
                    events=events,
                    computed_at=now,
                    stored_at=now,
                    feature_version=feature_version,
                    provider_set=_serialize_provider_set(provider_set),
                )
            )
            await session.commit()

    @staticmethod
    def _coerce_date(raw: str) -> date:
        return datetime.fromisoformat(raw).date() if "T" in raw else date.fromisoformat(raw)

    @staticmethod
    def _to_tick_entity(model: MarketBarModel) -> MarketTick:
        return MarketTick(
            ticker=model.ticker,
            asset_class=AssetClass(model.asset_class),
            timestamp=model.timestamp,
            open=model.open,
            high=model.high,
            low=model.low,
            close=model.close,
            volume=model.volume,
            stored_at=model.stored_at,
        )
