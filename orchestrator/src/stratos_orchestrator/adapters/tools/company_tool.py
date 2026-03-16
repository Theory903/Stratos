"""Company analysis tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class CompanyTool(HttpTool):
    """Tool for analyzing company fundamentals and market data."""

    @property
    def name(self) -> str:
        return "company_analyze"

    @property
    def description(self) -> str:
        return (
            "Analyze a company's fundamentals, fraud risk, and recent market performance. "
            "Returns financial metrics and recent price history."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL)",
                },
            },
            "required": ["ticker"],
        }

    async def execute(self, arguments: dict) -> dict:
        ticker = arguments["ticker"]

        # Fetch profile
        try:
            profile = await self._request("GET", f"/company/{ticker}")
        except Exception as e:
            return {"error": f"Failed to fetch company profile: {e}"}

        # Fetch recent market data (last 5 days)
        try:
            ticks = await self._request("GET", f"/market/{ticker}?limit=5")
        except Exception:
            ticks = []

        return {
            "profile": profile,
            "recent_market_data": ticks,
        }
