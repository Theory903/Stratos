"""Macro integration tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class MacroTool(HttpTool):
    """Tool for analyzing macroeconomic conditions and sovereign risk."""

    @property
    def name(self) -> str:
        return "macro_analyze_country"

    @property
    def description(self) -> str:
        return (
            "Analyze macroeconomic state and sovereign risk for a specific country. "
            "Returns GDP, inflation, debt metrics, and world state."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "country_code": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-3 code (e.g., USA, JPN)",
                },
                "include_world_state": {
                    "type": "boolean",
                    "description": "Include global macro state",
                    "default": True,
                },
            },
            "required": ["country_code"],
        }

    async def execute(self, arguments: dict) -> dict:
        country_code = arguments["country_code"]
        include_world = arguments.get("include_world_state", True)
        result: dict = {}

        try:
            country_data = await self._request("GET", f"/country/{country_code}")
            result["country"] = country_data
        except Exception as e:
            result["country_error"] = f"Failed to fetch country data: {e}"

        if include_world:
            try:
                world_state = await self._request("GET", "/world-state")
                result["world_state"] = world_state
            except Exception:
                result["world_state"] = "Unavailable"

        return result
