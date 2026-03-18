"""World macro integration tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class MacroWorldTool(HttpTool):
    """Tool for analyzing global macro conditions."""

    @property
    def name(self) -> str:
        return "macro_analyze_world"

    @property
    def description(self) -> str:
        return (
            "Analyze the current global macro state. Returns world inflation, rates, liquidity, "
            "commodity pressure, and other cross-asset regime signals."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, arguments: dict) -> dict:
        world_state = await self._request("GET", "/world-state")
        return {"world_state": world_state}
