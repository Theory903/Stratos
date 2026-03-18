"""Typed finance analyst roles."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from stratos_orchestrator.domain.entities import AnalystSignal


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _event_signal(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    sentiments: list[float] = []
    for item in items[:5]:
        sentiments.append(_safe_float(item.get("sentiment", 0.0)))
    average = mean(sentiments) if sentiments else 0.0
    return max(-1.0, min(1.0, average))


class MarketAnalyst:
    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        market_payload = context.get("market") or {}
        if isinstance(market_payload, list):
            bars = market_payload
        else:
            bars = market_payload.get("bars") or market_payload.get("market") or []
        closes = [_safe_float(item.get("close")) for item in bars[:20] if isinstance(item, dict)]
        closes = [value for value in closes if value > 0]
        momentum = 0.0
        vol = 0.0
        if len(closes) >= 2:
            momentum = (closes[0] - closes[-1]) / closes[-1]
            returns = [(current - previous) / previous for previous, current in zip(reversed(closes[:-1]), reversed(closes[1:])) if previous > 0]
            vol = pstdev(returns) if len(returns) >= 2 else 0.01
        score = max(-1.0, min(1.0, momentum * 6))
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        thesis = f"MarketAnalyst sees {direction} momentum with {momentum * 100:.2f}% window move and {vol * 100:.2f}% realized volatility."
        return AnalystSignal(
            analyst="MarketAnalyst",
            instrument=instrument,
            signal_score=score,
            confidence=0.65 if closes else 0.2,
            direction=direction,
            thesis=thesis,
            evidence_ids=[f"market:{instrument}"],
            citations=[thesis],
            freshness_ok=bool(closes),
        )


class FundamentalsAnalyst:
    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        if instrument.startswith(("X:", "FX:", "INDEX:")):
            return AnalystSignal(
                analyst="FundamentalsAnalyst",
                instrument=instrument,
                signal_score=0.0,
                confidence=0.35,
                direction="neutral",
                thesis="FundamentalsAnalyst defers because issuer fundamentals are not applicable for this instrument.",
                evidence_ids=[],
                citations=[],
                freshness_ok=True,
            )

        company = context.get("company") or {}
        profile = company.get("profile") or {}
        quality = mean(
            [
                _safe_float(profile.get("earnings_quality")),
                _safe_float(profile.get("free_cash_flow_stability")),
                _safe_float(profile.get("moat_score")),
            ]
        )
        fraud = _safe_float(profile.get("fraud_score"))
        leverage = _safe_float(profile.get("leverage_ratio"))
        raw = (quality - leverage - fraud) * 1.5
        direction = "bullish" if raw > 0.1 else "bearish" if raw < -0.1 else "neutral"
        thesis = f"FundamentalsAnalyst scores quality at {quality:.2f}, leverage at {leverage:.2f}, fraud risk at {fraud:.2f}."
        return AnalystSignal(
            analyst="FundamentalsAnalyst",
            instrument=instrument,
            signal_score=max(-1.0, min(1.0, raw)),
            confidence=0.6 if profile else 0.2,
            direction=direction,
            thesis=thesis,
            evidence_ids=[f"company:{instrument}"] if profile else [],
            citations=[thesis] if profile else [],
            freshness_ok=bool(profile),
        )


class NewsAnalyst:
    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        items = context.get("news", [])
        score = _event_signal(items)
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        headline = items[0]["headline"] if items and "headline" in items[0] else items[0].get("title") if items else "No news items"
        thesis = f"NewsAnalyst sees {direction} catalyst pressure. Lead item: {headline}."
        return AnalystSignal(
            analyst="NewsAnalyst",
            instrument=instrument,
            signal_score=score,
            confidence=0.62 if items else 0.2,
            direction=direction,
            thesis=thesis,
            evidence_ids=[str(item.get("event_id", f"news:{index}")) for index, item in enumerate(items[:3])],
            citations=[item.get("headline") or item.get("title", "") for item in items[:3]],
            freshness_ok=bool(items),
        )


class SocialAnalyst:
    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        items = context.get("social", [])
        score = _event_signal(items)
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        thesis = f"SocialAnalyst sees {direction} crowd tone across {len(items)} normalized posts."
        return AnalystSignal(
            analyst="SocialAnalyst",
            instrument=instrument,
            signal_score=score,
            confidence=0.55 if items else 0.2,
            direction=direction,
            thesis=thesis,
            evidence_ids=[str(item.get("event_id", f"social:{index}")) for index, item in enumerate(items[:3])],
            citations=[item.get("headline", "") for item in items[:3]],
            freshness_ok=bool(items),
        )


class MacroPolicyAnalyst:
    def analyze(self, instrument: str, context: dict[str, Any]) -> AnalystSignal:
        policy = context.get("policy", [])
        risk = context.get("portfolio_risk") if isinstance(context.get("portfolio_risk"), dict) else {}
        regime = str((risk.get("regime") or {}).get("regime_label", "unknown")).lower()
        policy_penalty = -0.1 if policy else 0.0
        regime_penalty = -0.2 if "risk_off" in regime else 0.0
        score = policy_penalty + regime_penalty
        direction = "bullish" if score > 0.1 else "bearish" if score < -0.1 else "neutral"
        thesis = f"MacroPolicyAnalyst sees {direction} overlay with regime {regime or 'unknown'} and {len(policy)} policy items."
        return AnalystSignal(
            analyst="MacroPolicyAnalyst",
            instrument=instrument,
            signal_score=score,
            confidence=0.58 if policy or risk else 0.3,
            direction=direction,
            thesis=thesis,
            evidence_ids=[str(item.get("event_id", f"policy:{index}")) for index, item in enumerate(policy[:3])],
            citations=[item.get("headline") or item.get("title", "") for item in policy[:3]],
            freshness_ok=bool(policy or risk),
        )
