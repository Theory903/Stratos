"""Finance memo and packet packaging."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from stratos_orchestrator.domain.entities import AnalystSignal, ConfidenceBand, DecisionPacket, RiskVerdict, StrategicMemo, TradeIntent


class DecisionPackager:
    def packet(self, trade_intent: TradeIntent, risk_verdict: RiskVerdict) -> DecisionPacket:
        action = trade_intent.action if risk_verdict.allowed else "NO_TRADE"
        return DecisionPacket(
            instrument=trade_intent.instrument,
            action=action,
            confidence=trade_intent.confidence if risk_verdict.allowed else min(trade_intent.confidence, 0.35),
            score=trade_intent.score,
            thesis=trade_intent.thesis if risk_verdict.allowed else risk_verdict.rationale,
            entry_zone=trade_intent.entry_zone,
            stop_loss=trade_intent.stop_loss,
            take_profit=trade_intent.take_profit,
            max_holding_period=trade_intent.max_holding_period,
            position_size_pct=risk_verdict.position_size_pct,
            capital_at_risk=risk_verdict.capital_at_risk,
            kill_switch_reasons=risk_verdict.kill_switch_reasons,
        )

    def memo(
        self,
        *,
        query: str,
        role_lens: str,
        analyst_signals: list[AnalystSignal],
        packet: DecisionPacket,
        risk_verdict: RiskVerdict,
        freshness_summary: dict[str, Any],
        provider_health: dict[str, Any] | None,
        replay_summary: dict[str, Any] | None,
        evidence_blocks: list[dict[str, str]],
        debate_summary: str,
    ) -> StrategicMemo:
        return StrategicMemo(
            query=query,
            plan_summary="Finance council executed typed market, news, social, macro, and risk passes.",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(packet.confidence),
            risk_policy_status="PASS" if risk_verdict.allowed else "FAIL",
            recommendation=packet.thesis,
            worst_case=self.worst_case(risk_verdict),
            risk_band="Low" if risk_verdict.allowed and not risk_verdict.kill_switch_reasons else "High",
            intent="portfolio",
            role=role_lens,
            decision=f"{packet.action} {packet.instrument}",
            summary=debate_summary,
            key_findings=[signal.thesis for signal in analyst_signals[:4]],
            portfolio_impact=[
                f"Position size {packet.position_size_pct * 100:.2f}%",
                f"Capital at risk {packet.capital_at_risk * 100:.2f}%",
            ],
            recommended_actions=self.recommended_actions(packet, risk_verdict),
            watch_items=freshness_summary.get("watch_items", []),
            data_quality=freshness_summary.get("notes", []),
            evidence_blocks=evidence_blocks,
            specialist_views=[
                {
                    "specialist": signal.analyst,
                    "title": signal.analyst,
                    "summary": signal.thesis,
                    "verdict": signal.direction,
                    "claims": signal.citations,
                    "concerns": [] if signal.freshness_ok else ["Freshness degraded"],
                }
                for signal in analyst_signals
            ],
            decision_packet=asdict(packet),
            analyst_signals=[asdict(signal) for signal in analyst_signals],
            risk_verdict=asdict(risk_verdict),
            freshness_summary=freshness_summary,
            provider_health=provider_health,
            replay_summary=replay_summary,
        )

    def trace(
        self,
        *,
        workspace_id: str,
        instrument: str,
        packet: DecisionPacket,
        risk_verdict: RiskVerdict,
        supervisor_plan: dict[str, Any] | None = None,
        feedback_summary: dict[str, Any] | None = None,
        degrade_reason: str | None = None,
    ) -> dict[str, Any]:
        return {
            "mode": "finance_council",
            "status": "completed",
            "answer_mode": "decision_with_limits",
            "workspace_id": workspace_id,
            "instrument": instrument,
            "packet": asdict(packet),
            "risk_verdict": asdict(risk_verdict),
            "supervisor_plan": supervisor_plan,
            "feedback_summary": feedback_summary,
            "degrade_reason": degrade_reason,
        }

    @staticmethod
    def evidence_blocks(context: dict[str, Any], analyst_signals: list[AnalystSignal]) -> list[dict[str, str]]:
        evidence: list[dict[str, str]] = []
        for signal in analyst_signals[:4]:
            evidence.append({"title": signal.analyst, "detail": signal.thesis})
        if context.get("news"):
            first = context["news"][0]
            evidence.append({"title": first.get("headline") or first.get("title", "News item"), "detail": first.get("summary", "")})
        return evidence[:6]

    @staticmethod
    def recommended_actions(packet: DecisionPacket, risk_verdict: RiskVerdict) -> list[str]:
        if not risk_verdict.allowed:
            return ["Do not open risk until the hard-gate failures clear.", *risk_verdict.kill_switch_reasons]
        return [
            f"Size {packet.position_size_pct * 100:.2f}% of capital.",
            f"Use stop {packet.stop_loss}.",
            f"Review thesis expiry at {packet.max_holding_period}.",
        ]

    @staticmethod
    def worst_case(risk_verdict: RiskVerdict) -> str:
        if risk_verdict.kill_switch_reasons:
            return "; ".join(risk_verdict.kill_switch_reasons[:2])
        return "Momentum reverses and portfolio risk budget is consumed before the thesis validates."
