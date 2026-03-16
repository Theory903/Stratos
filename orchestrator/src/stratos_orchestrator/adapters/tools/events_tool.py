"""Event intelligence tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class EventsTool(HttpTool):
    @property
    def name(self) -> str:
        return "events_analyze"

    @property
    def description(self) -> str:
        return (
            "Read STRATOS event pulse, event feed, and event clusters for a scope such as "
            "global, india, us, or btc."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "Event scope such as global, india, us, or btc.",
                },
                "query": {
                    "type": "string",
                    "description": "Optional search query over stored event feed.",
                },
            },
            "required": ["scope"],
        }

    async def execute(self, arguments: dict) -> dict:
        scope = arguments["scope"]
        query = arguments.get("query")

        pulse = await self._request("GET", f"/events/pulse/{scope}")
        clusters = await self._request("GET", f"/events/clusters?scope={scope}")

        if query:
            feed = await self._request("POST", "/events/search", json={"query": query, "scope": scope})
        else:
            feed = await self._request("GET", f"/events/feed?scope={scope}")

        return {
            "scope": scope,
            "pulse": pulse,
            "clusters": clusters,
            "feed": feed,
        }
