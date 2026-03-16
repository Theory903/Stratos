"""Portfolio decision tool for PM-first workflows."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class PortfolioStateTool(HttpTool):
    @property
    def name(self) -> str:
        return "portfolio_analyze"

    @property
    def description(self) -> str:
        return (
            "Read portfolio state, exposures, risk, decision queue, and optional scenario impact "
            "from the internal STRATOS portfolio domain."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Portfolio name.",
                },
                "scenario": {
                    "type": "string",
                    "description": "Optional scenario identifier to run against the portfolio.",
                },
            },
            "required": ["name"],
        }

    async def execute(self, arguments: dict) -> dict:
        name = arguments["name"]
        scenario = arguments.get("scenario")

        portfolio = await self._request("GET", f"/portfolio?name={name}")
        exposures = await self._request("GET", f"/portfolio/exposures?name={name}")
        risk = await self._request("GET", f"/portfolio/risk?name={name}")
        queue = await self._request("GET", f"/decision/queue?name={name}")
        decisions = await self._request("GET", f"/portfolio/decision-log?name={name}")

        result = {
            "portfolio": portfolio,
            "exposures": exposures,
            "risk": risk,
            "decision_queue": queue,
            "decision_log": decisions,
        }
        if scenario:
            result["scenario"] = await self._request(
                "POST",
                "/portfolio/scenario",
                json={"name": name, "scenario": scenario},
            )
        return result
