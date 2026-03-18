"""Yahoo Finance tool - free stock/crypto/forex data via yfinance library."""

from __future__ import annotations

import asyncio

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class YahooFinanceTool:
    """Get stock quotes, historical data, and financial info from Yahoo Finance.
    
    This is a free data source - no API key required.
    """

    def __init__(self) -> None:
        self.name = "yahoo_finance"
        self.description = (
            "Get real-time stock quotes, historical prices, and financial data from Yahoo Finance. "
            "Supports stocks (AAPL, GOOGL), ETFs, indices, cryptocurrencies, and forex pairs. "
            "This is a free data source - no API key required."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["quote", "history", "info", " financials", "recommendations"],
                    "description": "What data to fetch.",
                },
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., AAPL, BTC-USD, EURUSD=X).",
                },
                "period": {
                    "type": "string",
                    "description": "Period for history (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max).",
                    "default": "1mo",
                },
                "interval": {
                    "type": "string",
                    "description": "Interval for history (1m, 2m, 5m, 15m, 30m, 60m, 1h, 1d, 1wk, 1mo).",
                    "default": "1d",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of rows for history.",
                    "default": 30,
                },
            },
            "required": ["action", "ticker"],
        }

    async def execute(self, arguments: dict) -> dict:
        if not YFINANCE_AVAILABLE:
            return {
                "error": "yfinance library not installed. Run: pip install yfinance",
                "ticker": arguments.get("ticker"),
            }

        action = arguments.get("action", "quote")
        ticker_str = arguments["ticker"]

        def _fetch():
            ticker = yf.Ticker(ticker_str)
            
            if action == "quote":
                info = ticker.info
                return {
                    "action": "quote",
                    "ticker": ticker_str,
                    "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "previous_close": info.get("previousClose"),
                    "open": info.get("open"),
                    "day_high": info.get("dayHigh"),
                    "day_low": info.get("dayLow"),
                    "volume": info.get("volume"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "dividend_yield": info.get("dividendYield"),
                    "52w_high": info.get("fiftyTwoWeekHigh"),
                    "52w_low": info.get("fiftyTwoWeekLow"),
                    "name": info.get("shortName") or info.get("longName"),
                    "currency": info.get("currency"),
                    "exchange": info.get("exchange"),
                    "timestamp": info.get("regularMarketTime"),
                }
            
            elif action == "history":
                period = arguments.get("period", "1mo")
                interval = arguments.get("interval", "1d")
                limit = arguments.get("limit", 30)
                hist = ticker.history(period=period, interval=interval, limit=limit)
                return {
                    "action": "history",
                    "ticker": ticker_str,
                    "data": hist.to_dict(orient="records"),
                    "columns": list(hist.columns),
                    "start": str(hist.index[0]) if len(hist) > 0 else None,
                    "end": str(hist.index[-1]) if len(hist) > 0 else None,
                }
            
            elif action == "info":
                info = ticker.info
                return {
                    "action": "info",
                    "ticker": ticker_str,
                    "data": {
                        "name": info.get("shortName") or info.get("longName"),
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                        "market_cap": info.get("marketCap"),
                        "pe_ratio": info.get("trailingPE"),
                        "forward_pe": info.get("forwardPE"),
                        "peg_ratio": info.get("pegRatio"),
                        "debt_to_equity": info.get("debtToEquity"),
                        "profit_margin": info.get("profitMargin"),
                        "operating_margin": info.get("operatingMargin"),
                        "roe": info.get("returnOnEquity"),
                        "revenue": info.get("totalRevenue"),
                        "revenue_growth": info.get("revenueGrowth"),
                        "earnings": info.get("totalIncome"),
                        "beta": info.get("beta"),
                        "analyst_target": info.get("targetMeanPrice"),
                        "analyst_count": info.get("numberOfAnalystOpinions"),
                    },
                }
            
            elif action == "financials":
                financials = ticker.financials
                return {
                    "action": "financials",
                    "ticker": ticker_str,
                    "data": financials.to_dict(orient="records") if financials is not None else [],
                    "columns": list(financials.columns) if financials is not None else [],
                }
            
            elif action == "recommendations":
                recs = ticker.recommendations
                return {
                    "action": "recommendations",
                    "ticker": ticker_str,
                    "data": recs.to_dict(orient="records") if recs is not None else [],
                }
            
            else:
                return {"error": f"Unknown action: {action}", "ticker": ticker_str}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch)
