"""Market snapshot tool."""

from __future__ import annotations

import httpx

from stratos_orchestrator.adapters.tools.base import HttpTool


class MarketTool(HttpTool):
    @property
    def name(self) -> str:
        return "market_analyze"

    @property
    def description(self) -> str:
        return "Read recent market bars for a market ticker such as X:BTCUSD, AAPL, INDEX:NIFTY50, or CMD:CRUDE."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Market ticker to read.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent bars to return.",
                    "default": 5,
                },
            },
            "required": ["ticker"],
        }

    async def execute(self, arguments: dict) -> dict:
        ticker = arguments["ticker"]
        limit = arguments.get("limit", 5)
        url = f"{self.base_url}/market/{ticker}?limit={limit}"
        if self._client:
            response = await self._client.request("GET", url)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.request("GET", url)

        if response.status_code == 202:
            payload = response.json()
            return {
                "ticker": ticker,
                "pending": True,
                "status": payload.get("status", "pending"),
                "suggested_retry_seconds": payload.get("suggested_retry_seconds"),
                "bars": [],
                "latest": None,
            }

        response.raise_for_status()
        bars = response.json()
        latest = bars[0] if isinstance(bars, list) and bars else None
        return {
            "ticker": ticker,
            "pending": False,
            "bars": bars,
            "latest": latest,
        }
