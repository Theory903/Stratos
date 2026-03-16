"""World Bank sovereign data adapter."""

from __future__ import annotations

import asyncio
from math import sqrt

import httpx


class WorldBankCountrySource:
    """Fetch sovereign indicator data from the World Bank Indicators API."""

    _SOURCE_ID = "2"
    _DEBT_INDICATORS = ("GC.DOD.TOTL.GD.ZS", "DT.DOD.DECT.GN.ZS")
    _RESERVE_INDICATORS = ("FI.RES.TOTL.CD", "BN.RES.INCL.CD")
    _FISCAL_BALANCE_INDICATORS = ("GC.NLD.TOTL.GD.ZS",)
    _POLITICAL_STABILITY_INDICATORS = ("PV.EST",)
    _EXCHANGE_RATE_INDICATORS = ("PA.NUS.FCRF",)

    def __init__(self, base_url: str = "https://api.worldbank.org/v2") -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            follow_redirects=True,
            headers={"User-Agent": "stratos-data-fabric/0.1"},
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
        )

    @property
    def source_name(self) -> str:
        return "world_bank"

    async def fetch(self, **params: object) -> list[dict]:
        country_code = str(params["country_code"]).upper()
        return await self._fetch_indicator_series(
            country_code=country_code,
            indicator=str(params["indicator"]),
            per_page=int(params.get("per_page", 20)),
        )

    async def fetch_country_profile(self, country_code: str) -> dict[str, float | str]:
        normalized_country = country_code.upper()

        (
            debt_gdp,
            fx_reserves,
            fiscal_balance,
            political_stability_raw,
            exchange_rates,
        ) = await asyncio.gather(
            self._fetch_latest_value(normalized_country, self._DEBT_INDICATORS),
            self._fetch_latest_value(normalized_country, self._RESERVE_INDICATORS),
            self._fetch_latest_value(normalized_country, self._FISCAL_BALANCE_INDICATORS),
            self._fetch_latest_value(normalized_country, self._POLITICAL_STABILITY_INDICATORS),
            self._fetch_indicator_series(
                country_code=normalized_country,
                indicator=self._EXCHANGE_RATE_INDICATORS[0],
                per_page=10,
            ),
            return_exceptions=True,
        )

        debt_gdp = self._coerce_optional_float(debt_gdp)
        fx_reserves = self._coerce_optional_float(fx_reserves)
        fiscal_balance = self._coerce_optional_float(fiscal_balance)
        political_stability_raw = self._coerce_optional_float(political_stability_raw)
        exchange_rates = self._coerce_series(exchange_rates)

        if debt_gdp is None and fx_reserves is None and political_stability_raw is None:
            raise ValueError(f"No World Bank data available for country '{normalized_country}'")

        return {
            "country_code": normalized_country,
            "debt_gdp": float(debt_gdp or 0.0),
            "fx_reserves": float(fx_reserves or 0.0),
            "fiscal_deficit": self._to_deficit_ratio(fiscal_balance),
            "political_stability": self._normalize_political_stability(political_stability_raw),
            "currency_volatility": self._compute_currency_volatility(exchange_rates),
        }

    async def health_check(self) -> bool:
        try:
            data = await self._fetch_indicator_series("IND", "FP.CPI.TOTL.ZG", per_page=1)
            return bool(data)
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    async def _fetch_latest_value(
        self, country_code: str, indicators: tuple[str, ...]
    ) -> float | None:
        results = await asyncio.gather(
            *[
                self._fetch_indicator_series(
                    country_code=country_code,
                    indicator=indicator,
                    per_page=10,
                )
                for indicator in indicators
            ],
            return_exceptions=True,
        )
        for series in results:
            if isinstance(series, Exception) or not series:
                continue
            return float(series[0]["value"])
        return None

    async def _fetch_indicator_series(
        self,
        country_code: str,
        indicator: str,
        per_page: int,
    ) -> list[dict[str, float | int]]:
        response = await self._client.get(
            f"{self._base_url}/country/{country_code}/indicator/{indicator}",
            params={
                "format": "json",
                "per_page": per_page,
                "source": self._SOURCE_ID,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            return []

        series: list[dict[str, float | int]] = []
        for row in payload[1]:
            value = row.get("value")
            if value is None:
                continue
            series.append(
                {
                    "date": int(row["date"]),
                    "value": float(value),
                }
            )
        return series

    @staticmethod
    def _to_deficit_ratio(fiscal_balance: float | None) -> float:
        if fiscal_balance is None:
            return 0.0
        return max(-float(fiscal_balance), 0.0)

    @staticmethod
    def _normalize_political_stability(value: float | None) -> float:
        if value is None:
            return 0.5
        return min(1.0, max(0.0, (float(value) + 2.5) / 5.0))

    @staticmethod
    def _compute_currency_volatility(exchange_rates: list[dict[str, float | int]]) -> float:
        values = [float(row["value"]) for row in exchange_rates if float(row["value"]) > 0]
        if len(values) < 2:
            return 0.0

        year_over_year_changes = [
            (current - previous) / previous
            for previous, current in zip(values[1:], values[:-1])
            if previous > 0
        ]
        if not year_over_year_changes:
            return 0.0

        mean_change = sum(year_over_year_changes) / len(year_over_year_changes)
        variance = sum((change - mean_change) ** 2 for change in year_over_year_changes)
        variance /= len(year_over_year_changes)
        return sqrt(variance)

    @staticmethod
    def _coerce_optional_float(value: object) -> float | None:
        if isinstance(value, Exception) or value is None:
            return None
        return float(value)

    @staticmethod
    def _coerce_series(value: object) -> list[dict[str, float | int]]:
        if isinstance(value, Exception) or not isinstance(value, list):
            return []
        return value
