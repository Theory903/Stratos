"""Unit tests for domain entities."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from data_fabric.domain.entities import AssetClass, CompanyProfile, CountryProfile, MarketTick, WorldState


class TestWorldState:
    def test_immutable(self) -> None:
        ws = WorldState(
            interest_rate=5.25,
            inflation=3.2,
            liquidity_index=0.7,
            geopolitical_risk=0.4,
            volatility_index=18.5,
            commodity_index=102.3,
        )
        with pytest.raises(AttributeError):
            ws.interest_rate = 6.0  # type: ignore[misc]

    def test_fields(self) -> None:
        ws = WorldState(
            interest_rate=5.25,
            inflation=3.2,
            liquidity_index=0.7,
            geopolitical_risk=0.4,
            volatility_index=18.5,
            commodity_index=102.3,
        )
        assert ws.interest_rate == 5.25
        assert ws.inflation == 3.2


class TestCompanyProfile:
    def test_creation(self) -> None:
        cp = CompanyProfile(
            ticker="AAPL",
            name="Apple Inc.",
            earnings_quality=0.95,
            leverage_ratio=0.3,
            free_cash_flow_stability=0.9,
            fraud_score=0.02,
            moat_score=0.85,
        )
        assert cp.ticker == "AAPL"
        assert cp.fraud_score == 0.02


class TestCountryProfile:
    def test_creation(self) -> None:
        c = CountryProfile(
            country_code="US",
            debt_gdp=123.4,
            fx_reserves=50.0,
            fiscal_deficit=-5.2,
            political_stability=0.7,
            currency_volatility=0.1,
        )
        assert c.country_code == "US"


class TestMarketTick:
    def test_creation(self) -> None:
        tick = MarketTick(
            ticker="AAPL",
            asset_class=AssetClass.EQUITY,
            timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc),
            open=Decimal("185.50"),
            high=Decimal("187.00"),
            low=Decimal("184.00"),
            close=Decimal("186.75"),
            volume=50_000_000,
        )
        assert tick.asset_class == AssetClass.EQUITY
        assert tick.close == Decimal("186.75")

    def test_asset_class_values(self) -> None:
        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.FX.value == "fx"
