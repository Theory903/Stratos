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


class SourceAuthority(StrEnum):
    """Relative authority of a source used in finance workflows."""

    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


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


@dataclass(frozen=True, slots=True)
class InstrumentProfile:
    """Tradable instrument metadata used by the finance council."""

    instrument_id: str
    ticker: str
    venue: str
    asset_class: AssetClass
    display_name: str
    currency: str = "USD"
    metadata: dict[str, str] = field(default_factory=dict)
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    """Top-of-book and depth summary for a tradable instrument."""

    instrument_id: str
    ticker: str
    venue: str
    bid_price: Decimal
    ask_price: Decimal
    bid_size: Decimal
    ask_size: Decimal
    spread_bps: float
    depth_notional: Decimal
    imbalance: float
    timestamp: datetime
    stored_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class NormalizedEvent:
    """Canonical event shape used by news, social, policy, and exchange feeds."""

    event_id: str
    asset_scope: str
    entity_ids: tuple[str, ...]
    headline: str
    summary: str
    source_type: str
    provider: str
    authority_grade: SourceAuthority
    published_at: datetime
    ingested_at: datetime
    relevance: float = 0.0
    novelty: float = 0.0
    sentiment: float = 0.0
    market_session: str = "continuous"
    source_url: str | None = None
    body_ref: str | None = None
    dedupe_hash: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
