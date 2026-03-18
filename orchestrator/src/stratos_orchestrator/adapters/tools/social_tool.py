"""Social sentiment intelligence tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class SocialTool(HttpTool):
    @property
    def name(self) -> str:
        return "social_analyze"

    @property
    def description(self) -> str:
        return "Read normalized social posts and sentiment context for an entity such as BTC, INFY, or NIFTY."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "entity": {
                    "type": "string",
                    "description": "Ticker, instrument, or entity identifier.",
                },
            },
            "required": ["entity"],
        }

    async def execute(self, arguments: dict) -> dict:
        entity = arguments["entity"]
        items = await self._request("GET", f"/social/{entity}")
        return {
            "entity": entity,
            "items": items if isinstance(items, list) else [],
        }
