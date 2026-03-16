"""Historical comparison tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class HistoryTool(HttpTool):
    @property
    def name(self) -> str:
        return "history_analyze"

    @property
    def description(self) -> str:
        return (
            "Fetch internal historical analogs, compare metrics, and anomalies for portfolio and "
            "research decisions."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type such as market, company, country, or market_regime.",
                },
                "entity_id": {
                    "type": "string",
                    "description": "Entity identifier such as AAPL, IND, X:BTCUSD, or global.",
                },
                "metric": {
                    "type": "string",
                    "description": "Metric to compare or detect anomalies on.",
                },
            },
            "required": ["entity_type", "entity_id"],
        }

    async def execute(self, arguments: dict) -> dict:
        entity_type = arguments["entity_type"]
        entity_id = arguments["entity_id"]
        metric = arguments.get("metric") or {
            "market": "close",
            "company": "fraud_score",
            "country": "currency_volatility",
            "world_state": "inflation",
        }.get(entity_type, "close")

        if entity_type == "market_regime":
            return await self._request("GET", "/history/similar-regimes")

        compare = await self._request(
            "GET",
            f"/compare/metric?entity_type={entity_type}&entity_id={entity_id}&metric={metric}",
        )
        anomaly = await self._request(
            "GET",
            f"/anomalies/{entity_id}?entity_type={entity_type}&metric={metric}",
        )
        return {
            "compare": compare,
            "anomaly": anomaly,
        }
