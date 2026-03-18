"""Portfolio allocation tool backed by real market history."""

from __future__ import annotations

import math
from statistics import mean
from typing import Any
from urllib.parse import quote

try:
    import stratos_engines
except ImportError:  # pragma: no cover
    stratos_engines = None

from stratos_orchestrator.adapters.tools.base import HttpTool


class PortfolioTool(HttpTool):
    """Optimize a portfolio allocation using real market data from Data Fabric."""

    @property
    def name(self) -> str:
        return "portfolio_allocate"

    @property
    def description(self) -> str:
        return (
            "Optimize a portfolio allocation using real market history, "
            "transaction-cost penalties, and liquidity-aware caps."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of asset tickers or instrument identifiers.",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["mean_variance", "risk_parity", "equal_weight"],
                    "default": "mean_variance",
                },
                "current_weights": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Existing portfolio weights for turnover-aware sizing.",
                },
                "transaction_cost_bps": {
                    "type": "number",
                    "description": "Fixed transaction cost in basis points.",
                    "default": 10.0,
                },
                "liquidity_limits": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Max allocation per asset based on liquidity constraints.",
                },
                "lookback": {
                    "type": "integer",
                    "description": "Number of market bars to load for allocation inputs.",
                    "default": 90,
                },
            },
            "required": ["tickers"],
        }

    async def execute(self, arguments: dict) -> dict:
        tickers = [str(ticker).upper() for ticker in arguments["tickers"]]
        strategy = str(arguments.get("strategy", "mean_variance"))
        current_weights = arguments.get("current_weights")
        liquidity_limits = arguments.get("liquidity_limits")
        lookback = max(30, min(int(arguments.get("lookback", 90)), 365))
        transaction_cost_bps = float(arguments.get("transaction_cost_bps", 10.0) or 0.0)
        transaction_cost_rate = transaction_cost_bps / 10000.0

        market_data = await self._load_market_histories(tickers, lookback=lookback)
        if "error" in market_data:
            return market_data

        expected_returns, covariance, diagnostics = self._build_model_inputs(market_data["histories"])
        if expected_returns is None or covariance is None:
            return {
                "status": "unavailable",
                "error": "Insufficient real market history to compute portfolio inputs.",
                "required_minimum_bars": 20,
                "coverage": diagnostics,
            }

        caps = liquidity_limits or self._derive_liquidity_caps(market_data["histories"])
        weights = self._allocate(
            expected_returns=expected_returns,
            covariance=covariance,
            strategy=strategy,
            current_weights=current_weights,
            transaction_cost_rate=transaction_cost_rate,
            liquidity_limits=caps,
        )

        allocation = {ticker: round(weight, 6) for ticker, weight in zip(tickers, weights)}
        return {
            "status": "success",
            "strategy": strategy,
            "allocation": allocation,
            "transaction_cost_rate": transaction_cost_rate,
            "liquidity_limits": [round(limit, 6) for limit in caps],
            "expected_returns": [round(value, 6) for value in expected_returns],
            "volatility": [round(math.sqrt(max(covariance[index][index], 0.0)), 6) for index in range(len(tickers))],
            "data_coverage": diagnostics,
            "solver": "rust_engine" if stratos_engines is not None else "python_fallback",
        }

    async def _load_market_histories(self, tickers: list[str], *, lookback: int) -> dict[str, Any]:
        histories: list[list[dict[str, Any]]] = []
        diagnostics: list[dict[str, Any]] = []

        for ticker in tickers:
            payload = await self._request("GET", f"/market/{quote(ticker, safe='')}?limit={lookback}")
            if not isinstance(payload, list):
                return {"status": "unavailable", "error": f"Market history for {ticker} was not returned as a list."}
            bars = sorted(
                [item for item in payload if isinstance(item, dict) and item.get("close") is not None],
                key=lambda item: str(item.get("timestamp", "")),
            )
            histories.append(bars)
            diagnostics.append({"ticker": ticker, "bar_count": len(bars)})
        return {"histories": histories, "diagnostics": diagnostics}

    def _build_model_inputs(self, histories: list[list[dict[str, Any]]]) -> tuple[list[float] | None, list[list[float]] | None, list[dict[str, Any]]]:
        diagnostics: list[dict[str, Any]] = []
        returns_series: list[list[float]] = []
        annualization = 252.0

        for bars in histories:
            closes = [self._to_float(item.get("close")) for item in bars if self._to_float(item.get("close")) > 0]
            if len(closes) < 20:
                diagnostics.append({"bar_count": len(closes), "status": "insufficient"})
                return None, None, diagnostics
            returns = [
                (current - previous) / previous
                for previous, current in zip(closes[:-1], closes[1:])
                if previous > 0
            ]
            if len(returns) < 19:
                diagnostics.append({"bar_count": len(closes), "status": "insufficient"})
                return None, None, diagnostics
            returns_series.append(returns)
            diagnostics.append({"bar_count": len(closes), "status": "ready"})

        window = min(len(series) for series in returns_series)
        if window < 19:
            return None, None, diagnostics

        aligned = [series[-window:] for series in returns_series]
        expected_returns = [mean(series) * annualization for series in aligned]
        covariance = [
            [
                self._covariance(aligned[row], aligned[column]) * annualization
                for column in range(len(aligned))
            ]
            for row in range(len(aligned))
        ]
        return expected_returns, covariance, diagnostics

    def _derive_liquidity_caps(self, histories: list[list[dict[str, Any]]]) -> list[float]:
        caps: list[float] = []
        dollar_volumes: list[float] = []
        for bars in histories:
            observed = [
                self._to_float(item.get("close")) * self._to_float(item.get("volume"))
                for item in bars[-20:]
                if self._to_float(item.get("close")) > 0 and self._to_float(item.get("volume")) > 0
            ]
            dollar_volumes.append(mean(observed) if observed else 0.0)
        max_volume = max(dollar_volumes, default=0.0)
        for value in dollar_volumes:
            if max_volume <= 0:
                caps.append(1.0)
                continue
            relative = max(0.15, min(1.0, value / max_volume))
            caps.append(relative)
        return caps

    def _allocate(
        self,
        *,
        expected_returns: list[float],
        covariance: list[list[float]],
        strategy: str,
        current_weights: list[float] | None,
        transaction_cost_rate: float,
        liquidity_limits: list[float] | None,
    ) -> list[float]:
        if stratos_engines is not None:
            try:
                return list(
                    stratos_engines.allocate_portfolio(
                        expected_returns=expected_returns,
                        covariance=covariance,
                        strategy=strategy,
                        min_weight=0.0,
                        max_weight=1.0,
                        current_weights=current_weights,
                        transaction_cost=transaction_cost_rate,
                        slippage_coeff=0.001,
                        slippage_exponent=1.5,
                        cost_regime_multiplier=1.0,
                        liquidity_limit=liquidity_limits,
                    )
                )
            except Exception:
                pass

        if strategy == "equal_weight":
            weights = [1.0 / len(expected_returns)] * len(expected_returns)
        elif strategy == "risk_parity":
            inverse_vol = [1.0 / max(math.sqrt(max(covariance[index][index], 0.0)), 1e-6) for index in range(len(expected_returns))]
            weights = self._normalize(inverse_vol)
        else:
            scores = [
                max(expected_returns[index], 0.0) / max(covariance[index][index], 1e-6)
                for index in range(len(expected_returns))
            ]
            if sum(scores) <= 0:
                scores = [1.0 / max(math.sqrt(max(covariance[index][index], 0.0)), 1e-6) for index in range(len(expected_returns))]
            weights = self._normalize(scores)

        if liquidity_limits and len(liquidity_limits) == len(weights):
            weights = self._apply_caps(weights, liquidity_limits)

        if current_weights and len(current_weights) == len(weights):
            shrink = min(0.35, max(0.05, transaction_cost_rate * 40))
            weights = self._normalize(
                [
                    ((1.0 - shrink) * target) + (shrink * max(float(current), 0.0))
                    for target, current in zip(weights, current_weights)
                ]
            )
            if liquidity_limits and len(liquidity_limits) == len(weights):
                weights = self._apply_caps(weights, liquidity_limits)

        return [round(weight, 10) for weight in weights]

    @staticmethod
    def _apply_caps(weights: list[float], caps: list[float]) -> list[float]:
        capped = [min(max(weight, 0.0), max(cap, 0.01)) for weight, cap in zip(weights, caps)]
        return PortfolioTool._normalize(capped)

    @staticmethod
    def _normalize(values: list[float]) -> list[float]:
        total = sum(max(value, 0.0) for value in values)
        if total <= 0:
            return [1.0 / len(values)] * len(values)
        return [max(value, 0.0) / total for value in values]

    @staticmethod
    def _covariance(left: list[float], right: list[float]) -> float:
        if len(left) != len(right) or len(left) < 2:
            return 0.0
        left_mean = mean(left)
        right_mean = mean(right)
        return sum((l - left_mean) * (r - right_mean) for l, r in zip(left, right)) / (len(left) - 1)

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
