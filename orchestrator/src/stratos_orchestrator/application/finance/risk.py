"""Risk-profile and risk-manager modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stratos_orchestrator.domain.entities import RiskVerdict, TradeIntent


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass(frozen=True, slots=True)
class RiskProfileAssessment:
    name: str
    max_position_size_pct: float
    risk_budget_pct: float
    regime_multiplier: float = 1.0


class AggressiveRiskProfile:
    def assess(self) -> RiskProfileAssessment:
        return RiskProfileAssessment(name="AggressiveRisk", max_position_size_pct=0.05, risk_budget_pct=0.02, regime_multiplier=1.0)


class NeutralRiskProfile:
    def assess(self) -> RiskProfileAssessment:
        return RiskProfileAssessment(name="NeutralRisk", max_position_size_pct=0.03, risk_budget_pct=0.015, regime_multiplier=0.8)


class ConservativeRiskProfile:
    def assess(self) -> RiskProfileAssessment:
        return RiskProfileAssessment(name="ConservativeRisk", max_position_size_pct=0.02, risk_budget_pct=0.01, regime_multiplier=0.5)


class RiskManager:
    def __init__(self) -> None:
        self._aggressive = AggressiveRiskProfile()
        self._neutral = NeutralRiskProfile()
        self._conservative = ConservativeRiskProfile()

    def review(
        self,
        instrument: str,
        context: dict[str, Any],
        trade_intent: TradeIntent,
        freshness_summary: dict[str, Any],
    ) -> RiskVerdict:
        risk = context.get("portfolio_risk") if isinstance(context.get("portfolio_risk"), dict) else {}
        portfolio = context.get("portfolio") if isinstance(context.get("portfolio"), dict) else {}
        exposures = context.get("portfolio_exposures") if isinstance(context.get("portfolio_exposures"), dict) else {}
        vol = _safe_float(risk.get("estimated_daily_volatility"))
        var_95 = _safe_float(risk.get("value_at_risk_95"))
        concentration = _safe_float(risk.get("concentration_risk"))
        constraints = portfolio.get("constraints", {}) if isinstance(portfolio, dict) else {}
        max_single_name_weight = _safe_float(constraints.get("max_single_name_weight")) or 0.35
        max_crypto_weight = _safe_float(constraints.get("max_crypto_weight")) or 0.35
        max_drawdown_allowed = _safe_float(constraints.get("max_drawdown_allowed")) or 0.20
        current_drawdown = _safe_float(risk.get("current_drawdown"))
        regime_label = str((risk.get("regime") or {}).get("regime_label", "unknown")).lower() if isinstance(risk, dict) else "unknown"
        kill_switch_reasons: list[str] = []
        if not freshness_summary.get("market_ready"):
            kill_switch_reasons.append("Primary market feed missing.")
        risk_flags = risk.get("risk_flags", []) if isinstance(risk, dict) else []
        if any(isinstance(flag, str) and "concentrated" in flag.lower() for flag in risk_flags):
            kill_switch_reasons.append("Portfolio concentration already elevated.")
        if context.get("order_book") is None and instrument.startswith("X:"):
            kill_switch_reasons.append("Crypto order book feed missing.")
        if trade_intent.action == "HOLD":
            kill_switch_reasons.append("Council stayed neutral; edge did not clear the action threshold.")
        if abs(trade_intent.score) < 0.08:
            kill_switch_reasons.append("Council score below conviction threshold.")
        if current_drawdown > max_drawdown_allowed:
            kill_switch_reasons.append(
                f"Portfolio drawdown {current_drawdown:.2%} exceeds allowed limit of {max_drawdown_allowed:.2%}."
            )

        top_positions = exposures.get("top_positions", []) if isinstance(exposures, dict) else []
        matching_position = next(
            (position for position in top_positions if str(position.get("ticker", "")).upper() == instrument.upper()),
            None,
        )
        if matching_position and _safe_float(matching_position.get("weight")) >= max_single_name_weight:
            kill_switch_reasons.append(
                f"{instrument} already sits at {_safe_float(matching_position.get('weight')):.2%}, above the single-name limit of {max_single_name_weight:.2%}."
            )

        asset_class_exposure = exposures.get("asset_class_exposure", {}) if isinstance(exposures, dict) else {}
        current_crypto_weight = _safe_float(asset_class_exposure.get("crypto"))
        if instrument.startswith("X:") and current_crypto_weight >= max_crypto_weight:
            kill_switch_reasons.append(
                f"Crypto exposure is already {current_crypto_weight:.2%}, above the portfolio cap of {max_crypto_weight:.2%}."
            )

        profile = self._profile_for_regime(regime_label).assess()
        position_size_pct = min(
            profile.max_position_size_pct * profile.regime_multiplier,
            max(0.0, (profile.risk_budget_pct * profile.regime_multiplier) / max(vol, 0.01)),
        )

        if instrument.startswith("X:") and current_crypto_weight > 0:
            remaining_crypto_capacity = max(0.0, max_crypto_weight - current_crypto_weight)
            position_size_pct = min(position_size_pct, remaining_crypto_capacity)
        if kill_switch_reasons:
            position_size_pct = 0.0
        capital_at_risk = position_size_pct * profile.risk_budget_pct
        allowed = not kill_switch_reasons and trade_intent.action != "HOLD"
        rationale = (
            f"RiskManager approved trade sizing under {profile.name} for regime {regime_label}."
            if allowed
            else "RiskManager vetoed due to hard-gate violations."
        )
        return RiskVerdict(
            allowed=allowed,
            regime=str((risk.get("regime") or {}).get("regime_label", "unknown")) if isinstance(risk, dict) else "unknown",
            value_at_risk_95=var_95,
            concentration_risk=concentration,
            position_size_pct=position_size_pct,
            capital_at_risk=capital_at_risk,
            kill_switch_reasons=kill_switch_reasons,
            rationale=rationale,
        )

    def _profile_for_regime(self, regime_label: str):
        normalized = regime_label.lower()
        if normalized in {"risk_on", "bull", "normal"}:
            return self._aggressive
        if normalized in {"risk_off", "crisis", "stressed"}:
            return self._conservative
        return self._neutral
