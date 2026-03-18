"""Finnhub tool - stock data, news, and market sentiment from Finnhub."""

from __future__ import annotations

import httpx

from stratos_orchestrator.config import Settings
from stratos_orchestrator.adapters.tools.base import HttpTool


class FinnhubTool(HttpTool):
    """Get stock quotes, company news, and market data from Finnhub.
    
    Free tier: 60 calls/minute.
    API key required.
    """

    def __init__(self) -> None:
        settings = Settings()
        self._api_key = settings.finnhub_api_key
        self._settings = settings
        super().__init__("https://finnhub.io/api/v1")

    @property
    def name(self) -> str:
        return "finnhub"

    @property
    def description(self) -> str:
        return (
            "Get real-time stock quotes, company news, financial statements, and market data from Finnhub. "
            "Requires API key (free tier available: 60 calls/min)."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["quote", "news", "sentiment", "profile", "peers", "recommendation"],
                    "description": "What data to fetch.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, GOOGL).",
                },
                "category": {
                    "type": "string",
                    "description": "News category (general, forex, crypto, merger).",
                    "default": "general",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of news articles.",
                    "default": 10,
                },
            },
            "required": ["action"],
        }

    def _get_params(self, base_params: dict) -> dict:
        if self._api_key:
            base_params["token"] = self._api_key
        return base_params

    async def execute(self, arguments: dict) -> dict:
        if not self._settings.is_data_source_enabled("finnhub"):
            return {"error": "Finnhub is disabled. Set FINNHUB_API_KEY and FINNHUB_BUDGET > 0 to enable."}

        if not self._api_key:
            return {"error": "Finnhub API key not configured. Set FINNHUB_API_KEY in settings."}

        self._settings.track_api_call("finnhub")
        action = arguments.get("action", "quote")
        symbol = arguments.get("symbol", "").upper()

        try:
            if action == "quote":
                params = self._get_params({"symbol": symbol})
                data = await self._request("GET", "/quote", params=params)
                return {
                    "action": "quote",
                    "symbol": symbol,
                    "current_price": data.get("c"),
                    "high": data.get("h"),
                    "low": data.get("l"),
                    "open": data.get("o"),
                    "previous_close": data.get("pc"),
                    "timestamp": data.get("t"),
                }

            elif action == "news":
                category = arguments.get("category", "general")
                limit = arguments.get("limit", 10)
                params = self._get_params({"category": category, "minId": 0})
                data = await self._request("GET", "/news", params=params)
                return {
                    "action": "news",
                    "category": category,
                    "articles": [
                        {
                            "id": item.get("id"),
                            "headline": item.get("headline"),
                            "summary": item.get("summary"),
                            "source": item.get("source"),
                            "url": item.get("url"),
                            "datetime": item.get("datetime"),
                        }
                        for item in data[:limit]
                    ],
                }

            elif action == "sentiment":
                if not symbol:
                    return {"error": "symbol is required for sentiment action"}
                params = self._get_params({"symbol": symbol})
                data = await self._request("GET", "/news-sentiment", params=params)
                return {
                    "action": "sentiment",
                    "symbol": symbol,
                    "sentiment_score": data.get("sentimentScore"),
                    "sentiment_label": data.get("sentimentLabel"),
                    "reddit_score": data.get("redditScore"),
                    "twitter_score": data.get("twitterScore"),
                }

            elif action == "profile":
                if not symbol:
                    return {"error": "symbol is required for profile action"}
                params = self._get_params({"symbol": symbol})
                data = await self._request("GET", "/stock/profile2", params=params)
                return {
                    "action": "profile",
                    "symbol": symbol,
                    "name": data.get("name"),
                    "ticker": data.get("ticker"),
                    "exchange": data.get("exchange"),
                    "industry": data.get("finnhubIndustry"),
                    "weburl": data.get("weburl"),
                    "logo": data.get("logo"),
                    "country": data.get("country"),
                }

            elif action == "peers":
                if not symbol:
                    return {"error": "symbol is required for peers action"}
                params = self._get_params({"symbol": symbol})
                data = await self._request("GET", "/stock/peers", params=params)
                return {
                    "action": "peers",
                    "symbol": symbol,
                    "peers": data,
                }

            elif action == "recommendation":
                if not symbol:
                    return {"error": "symbol is required for recommendation action"}
                params = self._get_params({"symbol": symbol})
                data = await self._request("GET", "/stock/recommendation", params=params)
                return {
                    "action": "recommendation",
                    "symbol": symbol,
                    "data": data,
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except httpx.HTTPStatusError as e:
            return {"error": f"Finnhub API error: {e.response.status_code}", "detail": str(e)}
        except Exception as e:
            return {"error": str(e)}
