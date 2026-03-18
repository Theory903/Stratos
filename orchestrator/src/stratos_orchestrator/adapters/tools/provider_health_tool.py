"""Provider health tool for finance council workflows."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class ProviderHealthTool(HttpTool):
    @property
    def name(self) -> str:
        return "provider_health_analyze"

    @property
    def description(self) -> str:
        return "Read provider health coverage for the finance data stack."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    async def execute(self, arguments: dict) -> dict:
        return await self._request("GET", "/providers/health")
