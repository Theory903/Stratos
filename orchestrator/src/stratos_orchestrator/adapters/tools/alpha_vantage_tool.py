"""Alpha Vantage tool - stock, forex, and crypto data via Alpha Vantage API."""

from __future__ import annotations

import httpx

from stratos_orchestrator.config import Settings
from stratos_orchestrator.adapters.tools.base import HttpTool


class AlphaVantageTool(HttpTool):
    """Get stock quotes, forex rates, and crypto data from Alpha Vantage.
    
    Free tier: 5 calls/minute, 500 calls/day.
    API key required.
    """

    def __init__(self) -> None:
        settings = Settings()
        self._api_key = settings.alpha_vantage_api_key
        self._settings = settings
        super().__init__("https://www.alphavantage.co/query")

    @property
    def name(self) -> str:
        return "alpha_vantage"

    @property
    def description(self) -> str:
        return (
            "Get real-time stock quotes, forex rates, and cryptocurrency data from Alpha Vantage. "
            "Requires API key (free tier available: 5 calls/min, 500 calls/day)."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["quote", "intraday", "daily", "weekly", "monthly", "forex", "crypto"],
                    "description": "What data to fetch.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker (e.g., AAPL, IBM) or crypto (e.g., BTC).",
                },
                "market": {
                    "type": "string",
                    "description": "Market for forex/crypto (e.g., USD, EUR).",
                    "default": "USD",
                },
                "interval": {
                    "type": "string",
                    "description": "Interval for intraday (1min, 5min, 15min, 30min, 60min).",
                    "default": "5min",
                },
                "output_size": {
                    "type": "string",
                    "enum": ["compact", "full"],
                    "description": "Compact=100 latest, full=20+ years.",
                    "default": "compact",
                },
            },
            "required": ["action", "symbol"],
        }

    async def execute(self, arguments: dict) -> dict:
        if not self._settings.is_data_source_enabled("alpha_vantage"):
            return {"error": "Alpha Vantage is disabled. Set ALPHA_VANTAGE_API_KEY and ALPHA_VANTAGE_BUDGET > 0 to enable."}

        if not self._api_key:
            return {"error": "Alpha Vantage API key not configured. Set ALPHA_VANTAGE_API_KEY in settings."}

        self._settings.track_api_call("alpha_vantage")
        action = arguments.get("action", "quote")
        symbol = arguments.get("symbol", "").upper()
        market = arguments.get("market", "USD")

        try:
            if action == "quote":
                params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": self._api_key}
                data = await self._request("GET", "", params=params)
                quote = data.get("Global Quote", {})
                return {
                    "action": "quote",
                    "symbol": symbol,
                    "price": quote.get("05. price"),
                    "volume": quote.get("06. volume"),
                    "change": quote.get("09. change"),
                    "change_pct": quote.get("10. change %"),
                    "high": quote.get("03. high"),
                    "low": quote.get("04. low"),
                    "open": quote.get("02. open"),
                    "previous_close": quote.get("08. previous close"),
                }

            elif action in ("intraday", "daily", "weekly", "monthly"):
                func_map = {
                    "intraday": "TIME_SERIES_INTRADAY",
                    "daily": "TIME_SERIES_DAILY",
                    "weekly": "TIME_SERIES_WEEKLY",
                    "monthly": "TIME_SERIES_MONTHLY",
                }
                func = func_map.get(action, "TIME_SERIES_DAILY")
                params = {"function": func, "symbol": symbol, "apikey": self._api_key}
                
                if action == "intraday":
                    params["interval"] = arguments.get("interval", "5min")
                params["outputsize"] = arguments.get("output_size", "compact")
                
                data = await self._request("GET", "", params=params)
                
                series_key = [k for k in data.keys() if "Time Series" in k][0]
                time_series = data.get(series_key, {})
                
                return {
                    "action": action,
                    "symbol": symbol,
                    "data": time_series,
                    "count": len(time_series),
                }

            elif action == "forex":
                from_curr = symbol
                to_curr = market
                params = {
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "apikey": self._api_key,
                }
                data = await self._request("GET", "", params=params)
                rate = data.get("Realtime Currency Exchange Rate", {})
                return {
                    "action": "forex",
                    "from": from_curr,
                    "to": to_curr,
                    "rate": rate.get("5. Exchange Rate"),
                    "refreshed": rate.get("6. Last Refreshed"),
                }

            elif action == "crypto":
                params = {
                    "function": "CRYPTO_INTRADAY",
                    "symbol": symbol,
                    "market": market,
                    "apikey": self._api_key,
                }
                data = await self._request("GET", "", params=params)
                return {
                    "action": "crypto",
                    "symbol": symbol,
                    "market": market,
                    "data": data,
                }

            else:
                return {"error": f"Unknown action: {action}"}

        except httpx.HTTPStatusError as e:
            return {"error": f"Alpha Vantage API error: {e.response.status_code}", "detail": str(e)}
        except Exception as e:
            return {"error": str(e)}
