"""Tax analysis tool backed by real portfolio and market data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from stratos_orchestrator.adapters.tools.base import HttpTool


class TaxTool(HttpTool):
    """Analyze tax posture from the live portfolio snapshot."""

    @property
    def name(self) -> str:
        return "tax_optimize"

    @property
    def description(self) -> str:
        return (
            "Analyze tax implications from live portfolio positions using current market prices "
            "and holding-period information when available."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "portfolio_name": {
                    "type": "string",
                    "default": "primary",
                },
                "capital_gains_rate": {
                    "type": "number",
                    "default": 0.15,
                },
                "short_term_rate": {
                    "type": "number",
                    "default": 0.30,
                },
                "harvest_threshold_pct": {
                    "type": "number",
                    "default": -0.08,
                },
            },
        }

    async def execute(self, arguments: dict) -> dict:
        portfolio_name = str(arguments.get("portfolio_name", "primary"))
        capital_gains_rate = float(arguments.get("capital_gains_rate", 0.15) or 0.15)
        short_term_rate = float(arguments.get("short_term_rate", 0.30) or 0.30)
        harvest_threshold_pct = float(arguments.get("harvest_threshold_pct", -0.08) or -0.08)

        portfolio = await self._request("GET", f"/portfolio?name={quote(portfolio_name, safe='')}")
        if not isinstance(portfolio, dict):
            return {"status": "unavailable", "error": "Portfolio snapshot was not available."}

        positions = portfolio.get("positions", [])
        if not isinstance(positions, list) or not positions:
            return {"status": "unavailable", "error": f"Portfolio '{portfolio_name}' has no positions."}

        analyses: list[dict[str, Any]] = []
        total_market_value = 0.0
        total_unrealized_gain = 0.0
        estimated_tax_drag = 0.0

        for position in positions:
            if not isinstance(position, dict):
                continue
            ticker = str(position.get("ticker", "")).upper()
            quantity = self._to_float(position.get("quantity"))
            average_cost = self._to_float(position.get("average_cost"))
            if not ticker or quantity <= 0:
                continue
            market_payload = await self._request("GET", f"/market/{quote(ticker, safe='')}?limit=2")
            bars = market_payload if isinstance(market_payload, list) else []
            if not bars:
                continue
            last_price = self._to_float(bars[-1].get("close") if bars else 0.0)
            market_value = quantity * last_price
            cost_basis = quantity * average_cost
            unrealized_gain = market_value - cost_basis
            gain_pct = 0.0 if cost_basis <= 0 else unrealized_gain / cost_basis
            holding_term = self._holding_term(position)
            tax_rate = capital_gains_rate if holding_term == "long_term" else short_term_rate
            taxable_gain = max(unrealized_gain, 0.0)
            estimated_drag = taxable_gain * tax_rate

            total_market_value += market_value
            total_unrealized_gain += unrealized_gain
            estimated_tax_drag += estimated_drag
            analyses.append(
                {
                    "ticker": ticker,
                    "quantity": quantity,
                    "market_value": round(market_value, 2),
                    "cost_basis": round(cost_basis, 2),
                    "unrealized_gain": round(unrealized_gain, 2),
                    "gain_pct": round(gain_pct, 6),
                    "holding_term": holding_term,
                    "estimated_tax_drag": round(estimated_drag, 2),
                    "harvest_candidate": gain_pct <= harvest_threshold_pct,
                }
            )

        if not analyses:
            return {"status": "unavailable", "error": "Tax analysis could not price any live positions."}

        harvest_candidates = [item["ticker"] for item in analyses if item["harvest_candidate"]]
        long_term_positions = [item["ticker"] for item in analyses if item["holding_term"] == "long_term"]
        recommendation = self._recommendation(
            harvest_candidates=harvest_candidates,
            long_term_positions=long_term_positions,
            total_unrealized_gain=total_unrealized_gain,
        )
        return {
            "status": "success",
            "portfolio_name": portfolio_name,
            "total_market_value": round(total_market_value, 2),
            "total_unrealized_gain": round(total_unrealized_gain, 2),
            "estimated_tax_drag": round(estimated_tax_drag, 2),
            "harvest_candidates": harvest_candidates,
            "long_term_positions": long_term_positions,
            "recommendation": recommendation,
            "positions": analyses,
        }

    @staticmethod
    def _holding_term(position: dict[str, Any]) -> str:
        raw_date = (
            position.get("acquired_at")
            or position.get("purchase_date")
            or position.get("entered_at")
            or position.get("trade_date")
        )
        if not raw_date:
            return "unknown"
        try:
            acquired = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        except ValueError:
            return "unknown"
        if acquired.tzinfo is None:
            acquired = acquired.replace(tzinfo=UTC)
        return "long_term" if (datetime.now(UTC) - acquired).days >= 365 else "short_term"

    @staticmethod
    def _recommendation(*, harvest_candidates: list[str], long_term_positions: list[str], total_unrealized_gain: float) -> str:
        if harvest_candidates:
            return f"Review tax-loss harvesting candidates: {', '.join(harvest_candidates[:5])}."
        if long_term_positions and total_unrealized_gain > 0:
            return "Prefer trimming long-term gains before short-term gains where liquidity allows."
        if total_unrealized_gain <= 0:
            return "Current unrealized P&L does not imply immediate capital-gains pressure."
        return "Holding-period metadata is incomplete; do not automate tax decisions without lot-level data."

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
