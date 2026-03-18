"""Decision context tool for finance council workflows."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class DecisionContextTool(HttpTool):
    @property
    def name(self) -> str:
        return "decision_context_analyze"

    @property
    def description(self) -> str:
        return "Read the joined market, portfolio, news, social, exchange, and policy context for a finance decision."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Instrument or entity identifier.",
                },
                "portfolio_name": {
                    "type": "string",
                    "description": "Portfolio name.",
                    "default": "primary",
                },
            },
            "required": ["instrument"],
        }

    async def execute(self, arguments: dict) -> dict:
        instrument = arguments["instrument"]
        portfolio_name = arguments.get("portfolio_name", "primary")
        return await self._request(
            "GET",
            f"/decision/context/{instrument}?name={portfolio_name}",
        )
