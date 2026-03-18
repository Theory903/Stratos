"""Policy and central-bank events tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class PolicyEventsTool(HttpTool):
    @property
    def name(self) -> str:
        return "policy_events_analyze"

    @property
    def description(self) -> str:
        return (
            "Read STRATOS policy and central-bank event snapshots, or search them for "
            "topics like Fed, FOMC, RBI, inflation, or regulation."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "description": "Policy scope such as global, us, or india.",
                    "default": "global",
                },
                "query": {
                    "type": "string",
                    "description": "Optional search query for policy documents and events.",
                },
            },
            "required": [],
        }

    async def execute(self, arguments: dict) -> dict:
        scope = arguments.get("scope", "global")
        query = arguments.get("query")
        if query:
            items = await self._request("GET", f"/policy/search?q={query}&scope={scope}")
        else:
            items = await self._request("GET", f"/policy/events?scope={scope}")
        return {
            "scope": scope,
            "items": items if isinstance(items, list) else [],
            "query": query,
        }
