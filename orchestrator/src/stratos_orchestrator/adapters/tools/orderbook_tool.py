"""Order book and market microstructure tool."""

from __future__ import annotations

from stratos_orchestrator.adapters.tools.base import HttpTool


class OrderBookTool(HttpTool):
    @property
    def name(self) -> str:
        return "order_book_analyze"

    @property
    def description(self) -> str:
        return "Read the latest order book snapshot for a tradable instrument."

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "instrument": {
                    "type": "string",
                    "description": "Instrument identifier such as X:BTCUSD or NSE_EQ|INE009A01021.",
                }
            },
            "required": ["instrument"],
        }

    async def execute(self, arguments: dict) -> dict:
        instrument = arguments["instrument"]
        snapshot = await self._request("GET", f"/orderbook/{instrument}")
        return {"instrument": instrument, "snapshot": snapshot}
