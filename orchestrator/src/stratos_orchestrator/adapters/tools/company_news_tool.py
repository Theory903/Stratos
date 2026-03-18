"""Company news analysis tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class CompanyNewsTool(HttpTool):
    @property
    def name(self) -> str:
        return "company_news_analyze"

    @property
    def description(self) -> str:
        return (
            "Read the latest company news snapshot from STRATOS Data Fabric for a ticker "
            "such as AAPL or MSFT."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Company ticker symbol.",
                },
            },
            "required": ["ticker"],
        }

    async def execute(self, arguments: dict) -> dict:
        ticker = arguments["ticker"]
        items = await self._request("GET", f"/company/{ticker}/news")
        return {
            "ticker": ticker,
            "items": items if isinstance(items, list) else [],
        }
