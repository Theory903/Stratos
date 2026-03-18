"""Historical replay tool for finance council workflows."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class ReplayDecisionTool(HttpTool):
    @property
    def name(self) -> str:
        return "replay_decision_analyze"

    @property
    def description(self) -> str:
        return "Run a historical replay snapshot for a finance instrument."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Instrument identifier.",
                },
                "as_of": {
                    "type": "string",
                    "description": "Replay timestamp in ISO-8601 format.",
                },
                "portfolio_name": {
                    "type": "string",
                    "default": "primary",
                },
            },
            "required": ["instrument", "as_of"],
        }

    async def execute(self, arguments: dict) -> dict:
        instrument = arguments["instrument"]
        as_of = arguments["as_of"]
        portfolio_name = arguments.get("portfolio_name", "primary")
        return await self._request(
            "GET",
            f"/replay/decision/{instrument}?as_of={as_of}&name={portfolio_name}",
        )
