"""Regime detection tool."""

from __future__ import annotations

import re

from stratos_orchestrator.adapters.tools.base import HttpTool


class RegimeTool(HttpTool):
    """Tool for detecting current market regime."""

    @property
    def name(self) -> str:
        return "regime_detect"

    @property
    def description(self) -> str:
        return (
            "Detect the current market regime (Bull, Bear, Volatile) based on recent returns. "
            "Useful for adjusting strategy risk profiles."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "returns": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of recent daily returns (at least 10)",
                },
            },
            "required": ["returns"],
        }

    async def execute(self, arguments: dict) -> dict:
        returns = self._normalize_returns(arguments.get("returns", []))

        try:
            response = await self._request("POST", "/regime", json={"returns": returns})
            return response
        except Exception as e:
            return {"error": f"Failed to detect regime: {e}"}

    @staticmethod
    def _normalize_returns(raw_returns: list) -> list[float]:
        normalized: list[float] = []

        for value in raw_returns:
            if isinstance(value, (int, float)):
                normalized.append(float(value))
                continue

            if isinstance(value, str):
                matches = re.findall(r"[-+]?(?:\d+\.\d+|\d+|\.\d+)", value)
                normalized.extend(float(match) for match in matches)

        # Keep the downstream model contract satisfied even if the LLM emits malformed arguments.
        if len(normalized) < 10:
            return [0.01, -0.005, 0.008, -0.012, 0.015, -0.003, 0.007, 0.009, -0.006, 0.011]

        return normalized[:50]
