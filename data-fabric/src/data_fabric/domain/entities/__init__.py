"""Domain entities — pure business objects with no external dependencies."""

from __future__ import annotations

from datetime import UTC
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class AssetClass(StrEnum):
    """Classification of financial assets."""
    EQUITY = "equity"
    BOND = "bond"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    FX = "fx"


@dataclass(frozen=True, slots=True)
class WorldState:
    """Global macro state snapshot with Bi-Temporal support."""
    interest_rate: float
    inflation: float
    liquidity_index: float
    geopolitical_risk: float
    volatility_index: float
    commodity_index: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class CountryProfile:
    """Sovereign nation financial profile with Bi-Temporal support."""
    country_code: str
    debt_gdp: float
    fx_reserves: float
    fiscal_deficit: float
    political_stability: float
    currency_volatility: float
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Corporate financial profile with Bi-Temporal support."""
    ticker: str
    name: str
    earnings_quality: float
    leverage_ratio: float
    free_cash_flow_stability: float
    fraud_score: float
    moat_score: float
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class MarketTick:
    """Single market data point with Bi-Temporal support."""
    ticker: str
    asset_class: AssetClass
    timestamp: datetime # Valid Time
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))
