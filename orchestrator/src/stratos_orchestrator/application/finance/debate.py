"""Bull/bear research and synthesis roles."""

from __future__ import annotations

from stratos_orchestrator.domain.entities import AnalystSignal, DebateMemo


class BullResearcher:
    def summarize(self, analyst_signals: list[AnalystSignal]) -> str:
        bullish = [signal for signal in analyst_signals if signal.signal_score > 0]
        return "; ".join(signal.thesis for signal in bullish[:2]) or "BullResearcher found no durable upside case."


class BearResearcher:
    def summarize(self, analyst_signals: list[AnalystSignal]) -> str:
        bearish = [signal for signal in analyst_signals if signal.signal_score < 0]
        return "; ".join(signal.thesis for signal in bearish[:2]) or "BearResearcher found no dominant downside case."


class ResearchManager:
    def synthesize(self, analyst_signals: list[AnalystSignal], *, bull_case: str, bear_case: str) -> DebateMemo:
        net = sum(signal.signal_score * signal.confidence for signal in analyst_signals)
        verdict = "buy_bias" if net > 0.15 else "sell_bias" if net < -0.15 else "hold_bias"
        synthesis = f"ResearchManager netted the council at {net:.2f} with verdict {verdict}."
        confidence = min(0.9, max(0.25, abs(net)))
        return DebateMemo(
            bull_case=bull_case,
            bear_case=bear_case,
            synthesis=synthesis,
            verdict=verdict,
            confidence=confidence,
        )
