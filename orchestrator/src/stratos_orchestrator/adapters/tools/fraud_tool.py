"""Fraud detection tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class FraudTool(HttpTool):
    """Tool for detecting potential financial fraud."""

    @property
    def name(self) -> str:
        return "fraud_scan"

    @property
    def description(self) -> str:
        return (
            "Scan financial data for anomalies and potential fraud. "
            "Returns a list of detected anomalies with scores."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "Matrix of financial data points to scan",
                },
            },
            "required": ["data"],
        }

    async def execute(self, arguments: dict) -> dict:
        data = arguments["data"]

        try:
            response = await self._request("POST", "/anomalies", json={"data": data})
            return response
        except Exception as e:
            return {"error": f"Failed to scan for fraud: {e}"}
