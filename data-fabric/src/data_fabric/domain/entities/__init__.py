"""Domain entities — pure business objects with no external dependencies."""

from __future__ import annotations

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
    """Global macro state snapshot — immutable value object."""
    interest_rate: float
    inflation: float
    liquidity_index: float
    geopolitical_risk: float
    volatility_index: float
    commodity_index: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass(frozen=True, slots=True)
class CountryProfile:
    """Sovereign nation financial profile."""
    country_code: str
    debt_gdp: float
    fx_reserves: float
    fiscal_deficit: float
    political_stability: float
    currency_volatility: float


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Corporate financial profile."""
    ticker: str
    name: str
    earnings_quality: float
    leverage_ratio: float
    free_cash_flow_stability: float
    fraud_score: float
    moat_score: float


@dataclass(frozen=True, slots=True)
class MarketTick:
    """Single market data point."""
    ticker: str
    asset_class: AssetClass
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
