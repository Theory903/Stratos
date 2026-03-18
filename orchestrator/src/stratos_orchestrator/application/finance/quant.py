"""Quant signal generation from real market bars and order-book context."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from stratos_orchestrator.domain.entities import AnalystSignal


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class QuantAnalyst:
    """Feature-driven market microstructure and trend analyst."""

    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        bars = self._bars(context)
        closes = [_safe_float(item.get("close")) for item in bars if isinstance(item, dict)]
        closes = [value for value in closes if value > 0]
        if len(closes) < 4:
            return AnalystSignal(
                analyst="QuantAnalyst",
                instrument=instrument,
                signal_score=0.0,
                confidence=0.2,
                direction="neutral",
                thesis="QuantAnalyst lacks enough market bars to build a stable feature set.",
                evidence_ids=[],
                citations=[],
                freshness_ok=False,
            )

        latest = closes[0]
        momentum_3 = self._pct_change(latest, closes[min(3, len(closes) - 1)])
        momentum_10 = self._pct_change(latest, closes[min(10, len(closes) - 1)])
        returns = [self._pct_change(current, previous) for current, previous in zip(closes[:-1], closes[1:]) if previous > 0]
        realized_vol = pstdev(returns) if len(returns) >= 2 else 0.0
        trend_ratio = latest / max(mean(closes[: min(len(closes), 10)]), 1e-9) - 1.0
        order_book_signal = self._order_book_signal(context.get("order_book"))

        raw_score = (momentum_3 * 0.30) + (momentum_10 * 0.30) + (trend_ratio * 0.20) + (order_book_signal * 0.20)
        vol_penalty = min(0.25, realized_vol * 2.5)
        score = max(-1.0, min(1.0, (raw_score * 6.0) - vol_penalty))
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        thesis = (
            f"QuantAnalyst reads {direction} structure with 3-bar momentum {momentum_3 * 100:.2f}%, "
            f"10-bar momentum {momentum_10 * 100:.2f}%, realized vol {realized_vol * 100:.2f}%, "
            f"and order-book imbalance {order_book_signal:.2f}."
        )
        confidence = min(0.82, 0.45 + (min(len(closes), 20) / 40.0))
        if context.get("order_book") is not None:
            confidence += 0.08

        return AnalystSignal(
            analyst="QuantAnalyst",
            instrument=instrument,
            signal_score=score,
            confidence=min(confidence, 0.9),
            direction=direction,
            thesis=thesis,
            evidence_ids=[f"quant:{instrument}", f"market:{instrument}"],
            citations=[thesis],
            freshness_ok=True,
        )

    @staticmethod
    def _bars(context: dict[str, Any]) -> list[dict[str, Any]]:
        market_payload = context.get("market") or {}
        if isinstance(market_payload, list):
            return [item for item in market_payload if isinstance(item, dict)]
        if isinstance(market_payload, dict):
            payload = market_payload.get("bars") or market_payload.get("market") or []
            return [item for item in payload if isinstance(item, dict)]
        return []

    @staticmethod
    def _pct_change(current: float, previous: float) -> float:
        if previous <= 0:
            return 0.0
        return (current - previous) / previous

    @staticmethod
    def _order_book_signal(order_book: Any) -> float:
        if not isinstance(order_book, dict):
            return 0.0
        bid_price = _safe_float(order_book.get("top_bid_price"))
        ask_price = _safe_float(order_book.get("top_ask_price"))
        bid_size = _safe_float(order_book.get("top_bid_size") or order_book.get("bid_size"))
        ask_size = _safe_float(order_book.get("top_ask_size") or order_book.get("ask_size"))
        if bid_size > 0 and ask_size > 0:
            return max(-1.0, min(1.0, (bid_size - ask_size) / (bid_size + ask_size)))
        if bid_price > 0 and ask_price > 0:
            spread_mid = (bid_price + ask_price) / 2.0
            if spread_mid <= 0:
                return 0.0
            spread = (ask_price - bid_price) / spread_mid
            return max(-0.5, min(0.5, -spread * 10.0))
        return 0.0
