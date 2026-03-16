"""SQLAlchemy ORM models for feature and insight snapshots."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from data_fabric.adapters.database.engine import Base


class CompanyProfileModel(Base):
    """Legacy company table retained for compatibility with existing data."""

    __tablename__ = "companies"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    name: Mapped[str] = mapped_column(String(255))
    earnings_quality: Mapped[float]
    leverage_ratio: Mapped[float]
    free_cash_flow_stability: Mapped[float]
    fraud_score: Mapped[float]
    moat_score: Mapped[float]


class CountryProfileModel(Base):
    """Legacy country table retained for compatibility with existing data."""

    __tablename__ = "countries"

    country_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    debt_gdp: Mapped[float]
    fx_reserves: Mapped[float]
    fiscal_deficit: Mapped[float]
    political_stability: Mapped[float]
    currency_volatility: Mapped[float]


class WorldStateModel(Base):
    """Legacy world_state table retained for compatibility with existing data."""

    __tablename__ = "world_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interest_rate: Mapped[float]
    inflation: Mapped[float]
    liquidity_index: Mapped[float]
    geopolitical_risk: Mapped[float]
    volatility_index: Mapped[float]
    commodity_index: Mapped[float]
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class MarketTickModel(Base):
    """Legacy market tick table retained for compatibility with existing data."""

    __tablename__ = "market_ticks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    asset_class: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int]

    __table_args__ = (
        Index("ix_market_ticks_ticker_valid_stored", "ticker", "timestamp", "stored_at"),
    )


class MacroSeriesPointModel(Base):
    """Normalized macroeconomic observations."""

    __tablename__ = "macro_series_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[date] = mapped_column(Date(), index=True)
    value: Mapped[float]
    provider_set: Mapped[str] = mapped_column(String(255), default="")
    feature_version: Mapped[str] = mapped_column(String(64), default="macro-v1")
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_macro_series_point_series_observed", "series_id", "observed_at", "stored_at"),
    )


class CompanyFactPointModel(Base):
    """Normalized company facts derived from SEC companyfacts."""

    __tablename__ = "company_fact_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    fact_name: Mapped[str] = mapped_column(String(128), index=True)
    period_end: Mapped[date] = mapped_column(Date(), index=True)
    value: Mapped[float]
    unit: Mapped[str] = mapped_column(String(32), default="USD")
    provider_set: Mapped[str] = mapped_column(String(255), default="")
    feature_version: Mapped[str] = mapped_column(String(64), default="company-facts-v1")
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_company_fact_point_ticker_period", "ticker", "fact_name", "period_end", "stored_at"),
    )


class CountryIndicatorPointModel(Base):
    """Normalized sovereign feature inputs."""

    __tablename__ = "country_indicator_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(3), index=True)
    indicator_code: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[date] = mapped_column(Date(), index=True)
    value: Mapped[float]
    provider_set: Mapped[str] = mapped_column(String(255), default="")
    feature_version: Mapped[str] = mapped_column(String(64), default="country-indicators-v1")
    stored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    __table_args__ = (
        Index("ix_country_indicator_point_country_observed", "country_code", "indicator_code", "observed_at", "stored_at"),
    )


class CompanyFeatureSnapshotModel(Base):
    """Served company feature snapshots."""

    __tablename__ = "company_feature_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255))
    earnings_quality: Mapped[float]
    leverage_ratio: Mapped[float]
    free_cash_flow_stability: Mapped[float]
    fraud_score: Mapped[float]
    moat_score: Mapped[float]
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature_version: Mapped[str] = mapped_column(String(64), default="company-v1")
    source_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_set: Mapped[str] = mapped_column(String(255), default="")

    __table_args__ = (
        Index("ix_company_snapshot_ticker_computed", "ticker", "computed_at", "stored_at"),
    )


class CountryFeatureSnapshotModel(Base):
    """Served country feature snapshots."""

    __tablename__ = "country_feature_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(3), index=True)
    debt_gdp: Mapped[float]
    fx_reserves: Mapped[float]
    fiscal_deficit: Mapped[float]
    political_stability: Mapped[float]
    currency_volatility: Mapped[float]
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature_version: Mapped[str] = mapped_column(String(64), default="country-v1")
    source_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_set: Mapped[str] = mapped_column(String(255), default="")

    __table_args__ = (
        Index("ix_country_snapshot_country_computed", "country_code", "computed_at", "stored_at"),
    )


class WorldStateSnapshotModel(Base):
    """Served world-state insight snapshots."""

    __tablename__ = "world_state_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interest_rate: Mapped[float]
    inflation: Mapped[float]
    liquidity_index: Mapped[float]
    geopolitical_risk: Mapped[float]
    volatility_index: Mapped[float]
    commodity_index: Mapped[float]
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature_version: Mapped[str] = mapped_column(String(64), default="world-state-v1")
    source_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_set: Mapped[str] = mapped_column(String(255), default="")


class MarketBarModel(Base):
    """Normalized market bars served by the market history API."""

    __tablename__ = "market_bars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    volume: Mapped[int]
    feature_version: Mapped[str] = mapped_column(String(64), default="market-bars-v1")
    provider_set: Mapped[str] = mapped_column(String(255), default="")
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_market_bars_ticker_timestamp_stored", "ticker", "timestamp", "stored_at"),
    )


class MarketRegimeSnapshotModel(Base):
    """Served market-regime insight snapshots."""

    __tablename__ = "market_regime_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    regime_label: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float]
    factor_summary: Mapped[dict] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature_version: Mapped[str] = mapped_column(String(64), default="market-regime-v1")
    source_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_set: Mapped[str] = mapped_column(String(255), default="")


class PolicyWatchSnapshotModel(Base):
    """Served policy-watch insight snapshots."""

    __tablename__ = "policy_watch_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(Text(), default="")
    events: Mapped[list[dict]] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    feature_version: Mapped[str] = mapped_column(String(64), default="policy-watch-v1")
    source_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_set: Mapped[str] = mapped_column(String(255), default="")
