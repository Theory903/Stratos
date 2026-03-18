"""Trade intent generation."""

from __future__ import annotations

from statistics import mean

from stratos_orchestrator.application.finance.scoring import FinanceScorer
from stratos_orchestrator.domain.entities import AnalystSignal, DebateMemo, TradeIntent


class Trader:
    def __init__(self, scorer: FinanceScorer | None = None) -> None:
        self._scorer = scorer or FinanceScorer()

    def plan(self, instrument: str, analyst_signals: list[AnalystSignal], debate: DebateMemo) -> TradeIntent:
        score_summary = self._scorer.score(instrument, analyst_signals)
        action = (
            "BUY"
            if score_summary.final_score >= score_summary.action_threshold
            else "SELL"
            if score_summary.final_score <= -score_summary.action_threshold
            else "HOLD"
        )
        entry_zone = "scale in on 0.5-1.0 ATR pullbacks" if action == "BUY" else "sell strength into failed rebounds" if action == "SELL" else "wait for clearer break"
        stop_loss = "2.0 ATR below entry" if action == "BUY" else "2.0 ATR above entry" if action == "SELL" else "n/a"
        take_profit = "3.0 ATR target with trailing stop" if action != "HOLD" else "n/a"
        max_holding_period = "7d" if instrument.startswith("X:") else "10d"
        return TradeIntent(
            instrument=instrument,
            action=action,
            score=score_summary.final_score,
            confidence=max(0.2, min(0.92, mean(signal.confidence for signal in analyst_signals))),
            thesis=debate.synthesis,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            take_profit=take_profit,
            max_holding_period=max_holding_period,
        )
