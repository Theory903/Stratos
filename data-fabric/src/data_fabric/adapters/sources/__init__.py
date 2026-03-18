"""External data source adapters — implement ExternalDataSource port.

Open/Closed: add new sources by creating new classes, not modifying existing ones.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)


class PolygonMarketSource:
    """Polygon.io market data adapter (implements ExternalDataSource).

    Fetches OHLCV data for given tickers.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.massive.com") -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_name(self) -> str:
        return "massive" if "massive.com" in self._base_url else "polygon"

    async def fetch(self, **params: object) -> list[dict]:
        """Fetch daily OHLCV bars for given tickers."""
        if not self._api_key:
            return []
        tickers = params.get("tickers", [])
        if not isinstance(tickers, list):
            tickers = [tickers]

        results: list[dict] = []
         for ticker in tickers:
            normalized_ticker = self._normalize_provider_ticker(str(ticker))
            if normalized_ticker is None:
                logger.info(
                    "Skipping unsupported market ticker for %s provider: %s",
                    self.source_name,
                    ticker,
                )
                continue
            try:
                data = await self._fetch_ticker(str(ticker), normalized_ticker)
                results.extend(data)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.warning(
                        "Provider %s does not support ticker %s (normalized=%s)",
                        self.source_name,
                        ticker,
                        normalized_ticker,
                    )
                    continue
                logger.exception("Failed to fetch %s from Polygon", ticker)
            except Exception:
                logger.exception("Failed to fetch %s from Polygon", ticker)
        return results

    async def _fetch_ticker(self, ticker: str, provider_ticker: str) -> list[dict]:
        """Fetch recent daily bars for a single ticker."""
        asset_class = self._infer_asset_class(ticker)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=90)
        url = (
            f"{self._base_url}/v2/aggs/ticker/{provider_ticker}/range/1/day/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )
        response = await self._client.get(
            url, params={"apiKey": self._api_key, "limit": 365}
        )
        response.raise_for_status()
        data = response.json()

        return [
            {
                "ticker": ticker,
                "asset_class": asset_class,
                "timestamp": datetime.fromtimestamp(bar["t"] / 1000, tz=timezone.utc).isoformat(),
                "open": str(bar["o"]),
                "high": str(bar["h"]),
                "low": str(bar["l"]),
                "close": str(bar["c"]),
                "volume": bar["v"],
            }
            for bar in data.get("results", [])
        ]

    @staticmethod
    def _infer_asset_class(ticker: str) -> str:
        normalized = ticker.upper()
        if normalized.startswith("X:"):
            return "crypto"
        if normalized.startswith(("C:", "FX:")):
            return "fx"
        return "equity"

    @staticmethod
    def _normalize_provider_ticker(ticker: str) -> str | None:
        normalized = ticker.upper().strip()
        if not normalized:
            return None
        if normalized.startswith(("INDEX:", "CMD:", "MACRO:")):
            return None
        if normalized.startswith("FX:"):
            pair = normalized.removeprefix("FX:")
            return f"C:{pair}" if len(pair) == 6 and pair.isalpha() else None
        if normalized.startswith(("X:", "C:")):
            return normalized
        if normalized.isalnum() and 1 < len(normalized) <= 8:
            return normalized
        return None

    async def fetch_company_details(self, ticker: str) -> dict:
        """Fetch company details from Massive/Polygon reference endpoints."""
        if not self._api_key:
            raise ValueError("Market data API key is not configured")
        normalized_ticker = ticker.upper()
        reference_url = f"{self._base_url}/v3/reference/tickers"
        response = await self._client.get(
            reference_url,
            params={
                "apiKey": self._api_key,
                "ticker": normalized_ticker,
                "market": "stocks",
                "active": "true",
                "limit": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            raise ValueError(f"Ticker '{normalized_ticker}' not found")

        company = {
            "ticker": normalized_ticker,
            "name": results[0].get("name", normalized_ticker),
            "description": "",
            "homepage_url": "",
            "market_cap": 0,
        }

        # Try the richer ticker-details endpoint when the plan allows it.
        detail_url = f"{self._base_url}/v3/reference/tickers/{normalized_ticker}"
        detail_response = await self._client.get(
            detail_url,
            params={"apiKey": self._api_key},
        )
        if detail_response.status_code == 200:
            details = detail_response.json().get("results", {})
            company["description"] = details.get("description", "")
            company["homepage_url"] = details.get("homepage_url", "")
            company["market_cap"] = details.get("market_cap", 0)

        return company

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = await self._client.get(
                f"{self._base_url}/v1/marketstatus/now",
                params={"apiKey": self._api_key},
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class FREDMacroSource:
    """FRED (Federal Reserve Economic Data) adapter for macro indicators.

    Fetches GDP, CPI, interest rates, etc.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.stlouisfed.org") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def source_name(self) -> str:
        return "fred"

    async def fetch(self, **params: object) -> list[dict]:
        """Fetch macro indicators by series IDs."""
        if not self._api_key:
            return []
        indicators = params.get("indicators", [])
        if not isinstance(indicators, list):
            indicators = [indicators]

        results: list[dict] = []
        for series_id in indicators:
            try:
                data = await self._fetch_series(str(series_id))
                results.extend(data)
            except Exception:
                logger.exception("Failed to fetch FRED series %s", series_id)
        return results

    async def _fetch_series(self, series_id: str) -> list[dict]:
        """Fetch a single FRED series."""
        url = f"{self._base_url}/fred/series/observations"
        response = await self._client.get(
            url,
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": 100,
            },
        )
        response.raise_for_status()
        data = response.json()

        return [
            {
                "series_id": series_id,
                "date": obs["date"],
                "value": obs["value"],
            }
            for obs in data.get("observations", [])
            if obs.get("value") != "."
        ]

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            resp = await self._client.get(
                f"{self._base_url}/fred/series",
                params={
                    "series_id": "GDP",
                    "api_key": self._api_key,
                    "file_type": "json",
                },
            )
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


from data_fabric.adapters.sources.world_bank import WorldBankCountrySource

__all__ = ["FREDMacroSource", "PolygonMarketSource", "WorldBankCountrySource"]
