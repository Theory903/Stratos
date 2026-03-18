"""Finance scoring profiles and conflict-aware score aggregation."""

from __future__ import annotations

from dataclasses import dataclass

from stratos_orchestrator.domain.entities import AnalystSignal


@dataclass(frozen=True, slots=True)
class ScoringProfile:
    name: str
    weights: dict[str, float]
    action_threshold: float
    conviction_threshold: float
    conflict_penalty_scale: float


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    profile_name: str
    raw_score: float
    final_score: float
    conflict_penalty: float
    action_threshold: float
    conviction_threshold: float
    disagreement_ratio: float


_PROFILES: dict[str, ScoringProfile] = {
    "india_equity_swing": ScoringProfile(
        name="india_equity_swing",
        weights={
            "MarketAnalyst": 0.25,
            "QuantAnalyst": 0.10,
            "FundamentalsAnalyst": 0.25,
            "NewsAnalyst": 0.20,
            "SocialAnalyst": 0.10,
            "MacroPolicyAnalyst": 0.10,
        },
        action_threshold=0.12,
        conviction_threshold=0.08,
        conflict_penalty_scale=0.20,
    ),
    "equity_swing": ScoringProfile(
        name="equity_swing",
        weights={
            "MarketAnalyst": 0.25,
            "QuantAnalyst": 0.10,
            "FundamentalsAnalyst": 0.25,
            "NewsAnalyst": 0.20,
            "SocialAnalyst": 0.10,
            "MacroPolicyAnalyst": 0.10,
        },
        action_threshold=0.12,
        conviction_threshold=0.08,
        conflict_penalty_scale=0.18,
    ),
    "crypto_swing": ScoringProfile(
        name="crypto_swing",
        weights={
            "MarketAnalyst": 0.30,
            "QuantAnalyst": 0.25,
            "FundamentalsAnalyst": 0.0,
            "NewsAnalyst": 0.20,
            "SocialAnalyst": 0.15,
            "MacroPolicyAnalyst": 0.10,
        },
        action_threshold=0.12,
        conviction_threshold=0.08,
        conflict_penalty_scale=0.22,
    ),
}


class FinanceScorer:
    """Aggregate analyst signals into a conflict-aware final score."""

    def score(self, instrument: str, analyst_signals: list[AnalystSignal]) -> ScoreSummary:
        profile = self.profile_for_instrument(instrument)
        raw_score = sum(signal.signal_score * profile.weights.get(signal.analyst, 0.0) for signal in analyst_signals)
        disagreement_ratio = self._disagreement_ratio(analyst_signals)
        conflict_penalty = disagreement_ratio * profile.conflict_penalty_scale
        final_score = self._apply_conflict_penalty(raw_score, conflict_penalty)
        return ScoreSummary(
            profile_name=profile.name,
            raw_score=raw_score,
            final_score=final_score,
            conflict_penalty=conflict_penalty,
            action_threshold=profile.action_threshold,
            conviction_threshold=profile.conviction_threshold,
            disagreement_ratio=disagreement_ratio,
        )

    @staticmethod
    def profile_for_instrument(instrument: str) -> ScoringProfile:
        if instrument.startswith("X:"):
            return _PROFILES["crypto_swing"]
        if instrument.startswith(("NSE", "BSE", "INDEX:NIFTY", "INDEX:BANKNIFTY", "INDEX:SENSEX", "INDEX:INDIAVIX")):
            return _PROFILES["india_equity_swing"]
        return _PROFILES["equity_swing"]

    @staticmethod
    def _disagreement_ratio(analyst_signals: list[AnalystSignal]) -> float:
        bullish = sum(signal.confidence for signal in analyst_signals if signal.signal_score > 0.05)
        bearish = sum(signal.confidence for signal in analyst_signals if signal.signal_score < -0.05)
        total = bullish + bearish
        if total <= 0:
            return 0.0
        return min(bullish, bearish) / total

    @staticmethod
    def _apply_conflict_penalty(raw_score: float, penalty: float) -> float:
        if raw_score > 0:
            return max(0.0, raw_score - penalty)
        if raw_score < 0:
            return min(0.0, raw_score + penalty)
        return 0.0
