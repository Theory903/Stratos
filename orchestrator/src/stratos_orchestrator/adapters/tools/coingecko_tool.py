"""CoinGecko tool - free cryptocurrency data."""

from __future__ import annotations

import httpx

from stratos_orchestrator.config import Settings
from stratos_orchestrator.adapters.tools.base import HttpTool


class CoinGeckoTool(HttpTool):
    """Get cryptocurrency prices, market data, and coin info from CoinGecko.
    
    Free tier: 10-50 calls/minute, 10,000 calls/month.
    API key optional but recommended for higher rate limits.
    """

    def __init__(self) -> None:
        settings = Settings()
        api_key = settings.coingecko_api_key
        base_url = "https://api.coingecko.com/api/v3"
        if api_key:
            base_url += f"?x_cg_demo_api_key={api_key}"
        super().__init__(base_url)
        self._api_key = api_key
        self._settings = settings

    @property
    def name(self) -> str:
        return "coingecko"

    @property
    def description(self) -> str:
        return (
            "Get cryptocurrency prices, market data, and coin information from CoinGecko. "
            "Supports Bitcoin, Ethereum, and 10,000+ coins. "
            "Free tier available with optional API key for higher rate limits."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["price", "market", "coin", "history", "search"],
                    "description": "What data to fetch.",
                },
                "coin_id": {
                    "type": "string",
                    "description": "Coin ID on CoinGecko (e.g., bitcoin, ethereum).",
                },
                "symbol": {
                    "type": "string",
                    "description": "Trading pair symbol (e.g., BTC, ETH).",
                },
                "currency": {
                    "type": "string",
                    "description": "Quote currency (usd, eur, gbp, jpy, etc.).",
                    "default": "usd",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results for market/list actions.",
                    "default": 10,
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days for historical data.",
                    "default": 7,
                },
            },
            "required": ["action"],
        }

    async def execute(self, arguments: dict) -> dict:
        if not self._settings.is_data_source_enabled("coingecko") and self._settings.coingecko_budget == 0:
            return {"error": "CoinGecko data source is disabled. Set COINGECKO_BUDGET > 0 to enable."}

        self._settings.track_api_call("coingecko")
        action = arguments.get("action", "price")
        
        headers = {}
        if self._api_key:
            headers["x-cg-demo-api-key"] = self._api_key

        try:
            if action == "price":
                coin_id = arguments.get("coin_id")
                symbol = arguments.get("symbol")
                currency = arguments.get("currency", "usd")
                
                if coin_id:
                    ids = coin_id
                elif symbol:
                    ids = symbol.upper()
                else:
                    return {"error": "Either coin_id or symbol is required"}
                
                params = {"vs_currencies": currency, "include_24hr_change": "true"}
                url = "/simple/price"
                if not coin_id:
                    url += f"?ids={ids}"
                else:
                    url += f"?ids={coin_id}"
                
                data = await self._request("GET", url, params=params, headers=headers)
                return {
                    "action": "price",
                    "data": data,
                    "currency": currency,
                }

            elif action == "market":
                limit = arguments.get("limit", 10)
                currency = arguments.get("currency", "usd")
                url = f"/coins/markets?vs_currency={currency}&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
                data = await self._request("GET", url, headers=headers)
                return {
                    "action": "market",
                    "data": [
                        {
                            "id": c.get("id"),
                            "symbol": c.get("symbol"),
                            "name": c.get("name"),
                            "price": c.get("current_price"),
                            "change_24h": c.get("price_change_percentage_24h"),
                            "market_cap": c.get("market_cap"),
                            "volume_24h": c.get("total_volume"),
                            "rank": c.get("market_cap_rank"),
                        }
                        for c in data
                    ],
                }

            elif action == "coin":
                coin_id = arguments.get("coin_id")
                if not coin_id:
                    return {"error": "coin_id is required for coin action"}
                url = f"/coins/{coin_id}"
                params = {"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"}
                data = await self._request("GET", url, params=params, headers=headers)
                return {
                    "action": "coin",
                    "data": {
                        "id": data.get("id"),
                        "symbol": data.get("symbol"),
                        "name": data.get("name"),
                        "description": data.get("description", {}).get("en", ""),
                        "market_data": data.get("market_data"),
                        "links": data.get("links"),
                    },
                }

            elif action == "history":
                coin_id = arguments.get("coin_id")
                days = arguments.get("days", 7)
                currency = arguments.get("currency", "usd")
                if not coin_id:
                    return {"error": "coin_id is required for history action"}
                url = f"/coins/{coin_id}/market_chart?vs_currency={currency}&days={days}"
                data = await self._request("GET", url, headers=headers)
                return {
                    "action": "history",
                    "coin_id": coin_id,
                    "currency": currency,
                    "prices": data.get("prices", [])[-30:],
                    "market_caps": data.get("market_caps", [])[-30:],
                    "volumes": data.get("total_volumes", [])[-30:],
                }

            elif action == "search":
                query = arguments.get("coin_id") or arguments.get("symbol", "")
                url = f"/search?query={query}"
                data = await self._request("GET", url, headers=headers)
                return {
                    "action": "search",
                    "query": query,
                    "coins": [
                        {
                            "id": c.get("id"),
                            "name": c.get("name"),
                            "symbol": c.get("symbol"),
                            "rank": c.get("market_cap_rank"),
                        }
                        for c in data.get("coins", [])[:10]
                    ],
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except httpx.HTTPStatusError as e:
            return {"error": f"CoinGecko API error: {e.response.status_code}", "detail": str(e)}
        except Exception as e:
            return {"error": str(e)}
