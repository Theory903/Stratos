"""OANDA FX adapter — provides real yield spread and rate differential data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class OandaFXSource:
    """OANDA REST API adapter for real FX and interest rate proxies."""

    def __init__(self, api_key: str, account_id: str = "", base_url: str = "https://api-fxtrade.oanda.com") -> None:
        self._api_key = api_key
        self._account_id = account_id
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0
        )

    @property
    def source_name(self) -> str:
        return "oanda"

    async def fetch(self, **params: object) -> list[dict]:
        """Fetch latest candles for FX pairs."""
        if not self._api_key:
            return []
        instruments = params.get("instruments", ["EUR_USD", "USD_JPY", "GBP_USD"])
        if not isinstance(instruments, list):
            instruments = [instruments]

        results = []
        for instrument in instruments:
            try:
                data = await self._fetch_instrument(str(instrument))
                results.extend(data)
            except Exception:
                logger.exception("Failed to fetch %s from OANDA", instrument)
        return results

    async def _fetch_instrument(self, instrument: str) -> list[dict]:
        url = f"{self._base_url}/v3/instruments/{instrument}/candles"
        response = await self._client.get(
            url,
            params={"count": 10, "granularity": "D"}
        )
        response.raise_for_status()
        data = response.json()

        return [
            {
                "ticker": instrument,
                "asset_class": "fx",
                "timestamp": candle["time"],
                "open": candle["mid"]["o"],
                "high": candle["mid"]["h"],
                "low": candle["mid"]["l"],
                "close": candle["mid"]["c"],
                "volume": int(float(candle["volume"])),
            }
            for candle in data.get("candles", [])
            if candle.get("complete")
        ]

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            # Simple ping to test auth
            resp = await self._client.get(f"{self._base_url}/v3/accounts")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()
