"""Typed finance council runtime for STRATOS finance workflows."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from stratos_orchestrator.adapters.tools.registry import ToolRegistry
from stratos_orchestrator.application.finance import (
    DecisionPackager,
    FinanceFeedbackMemory,
    FinanceContextLoader,
    FinanceSupervisor,
    FreshnessGate,
    FundamentalsAnalyst,
    InstrumentResolver,
    MacroPolicyAnalyst,
    MarketAnalyst,
    NewsAnalyst,
    QuantAnalyst,
    ResearchManager,
    RiskManager,
    SocialAnalyst,
    Trader,
    BearResearcher,
    BullResearcher,
)
from stratos_orchestrator.config import Settings
from stratos_orchestrator.domain.entities import StrategicMemo


class FinanceCouncilRuntime:
    """Adaptive finance council that consumes typed finance data."""

    def __init__(self, tools: ToolRegistry, settings: Settings | None = None) -> None:
        self._settings = settings
        self._context_loader = FinanceContextLoader(tools)
        self._resolver = InstrumentResolver()
        self._supervisor = FinanceSupervisor(settings=settings)
        self._freshness_gate = FreshnessGate()
        self._market_analyst = MarketAnalyst()
        self._quant_analyst = QuantAnalyst()
        self._fundamentals_analyst = FundamentalsAnalyst()
        self._news_analyst = NewsAnalyst()
        self._social_analyst = SocialAnalyst()
        self._macro_policy_analyst = MacroPolicyAnalyst()
        self._bull_researcher = BullResearcher()
        self._bear_researcher = BearResearcher()
        self._research_manager = ResearchManager()
        self._trader = Trader()
        self._risk_manager = RiskManager()
        self._packager = DecisionPackager()
        self._feedback = self._build_feedback_memory(settings)

    async def execute(self, *, query: str, role_lens: str, workspace_id: str) -> tuple[StrategicMemo, dict[str, Any]]:
        bundle = await self._run(query=query, role_lens=role_lens, workspace_id=workspace_id)
        memo = self._packager.memo(
            query=query,
            role_lens=role_lens,
            analyst_signals=bundle["analyst_signals"],
            packet=bundle["packet"],
            risk_verdict=bundle["risk_verdict"],
            freshness_summary=bundle["freshness_summary"],
            provider_health=bundle["provider_health"],
            replay_summary=bundle["replay_summary"],
            evidence_blocks=bundle["evidence_blocks"],
            debate_summary=bundle["debate"].synthesis,
        )
        trace = self._packager.trace(
            workspace_id=workspace_id,
            instrument=bundle["instrument"],
            packet=bundle["packet"],
            risk_verdict=bundle["risk_verdict"],
            supervisor_plan=bundle["supervisor_plan"],
            feedback_summary=bundle["feedback_summary"],
            degrade_reason=bundle["degrade_reason"],
        )
        return memo, trace

    async def stream(self, *, query: str, role_lens: str, workspace_id: str):
        yield ("status", "Resolving finance instrument...")
        instrument = self._resolver.resolve(query)
        yield ("context", {"role_lens": role_lens, "intent": "portfolio", "workspace_id": workspace_id, "instrument": instrument})
        yield ("status", "Loading finance decision context...")
        bundle = await self._run(query=query, role_lens=role_lens, workspace_id=workspace_id, instrument=instrument)
        yield (
            "finance_council",
            {
                "instrument": bundle["instrument"],
                "analyst_signals": [asdict(signal) for signal in bundle["analyst_signals"]],
                "freshness_summary": bundle["freshness_summary"],
                "provider_health": bundle["provider_health"],
                "replay_summary": bundle["replay_summary"],
                "supervisor_plan": bundle["supervisor_plan"],
                "feedback_summary": bundle["feedback_summary"],
            },
        )
        memo = self._packager.memo(
            query=query,
            role_lens=role_lens,
            analyst_signals=bundle["analyst_signals"],
            packet=bundle["packet"],
            risk_verdict=bundle["risk_verdict"],
            freshness_summary=bundle["freshness_summary"],
            provider_health=bundle["provider_health"],
            replay_summary=bundle["replay_summary"],
            evidence_blocks=bundle["evidence_blocks"],
            debate_summary=bundle["debate"].synthesis,
        )
        yield (
            "final_output",
            {
                "decision": memo.decision,
                "summary": memo.summary,
                "recommendation": memo.recommendation,
                "confidence_score": memo.confidence_band.score,
                "confidence_calibration": memo.confidence_band.calibration,
                "risk_band": memo.risk_band,
                "worst_case": memo.worst_case,
                "intent": memo.intent,
                "role": memo.role,
                "key_findings": memo.key_findings,
                "portfolio_impact": memo.portfolio_impact,
                "recommended_actions": memo.recommended_actions,
                "watch_items": memo.watch_items,
                "data_quality": memo.data_quality,
                "evidence_blocks": memo.evidence_blocks,
                "decision_packet": memo.decision_packet,
                "analyst_signals": memo.analyst_signals,
                "risk_verdict": memo.risk_verdict,
                "freshness_summary": memo.freshness_summary,
                "provider_health": memo.provider_health,
                "replay_summary": memo.replay_summary,
                "degrade_reason": bundle["degrade_reason"],
            },
        )

    async def _run(self, *, query: str, role_lens: str, workspace_id: str, instrument: str | None = None) -> dict[str, Any]:
        resolved_instrument = instrument or self._resolver.resolve(query)
        context = await self._context_loader.load(resolved_instrument)
        freshness_summary = self._freshness_gate.summarize(context)
        context["freshness_summary"] = freshness_summary
        feedback_summary = self._feedback.summary(workspace_id=workspace_id, instrument=resolved_instrument) if self._feedback is not None else {}
        supervisor_plan = await self._supervisor.decide(
            query=query,
            instrument=resolved_instrument,
            context=context,
            feedback_summary=feedback_summary,
        )
        analyst_signals = self._analyst_signals(resolved_instrument, context, supervisor_plan.active_analysts)
        bull_case = self._bull_researcher.summarize(analyst_signals)
        bear_case = self._bear_researcher.summarize(analyst_signals)
        debate = self._research_manager.synthesize(analyst_signals, bull_case=bull_case, bear_case=bear_case)
        trade_intent = self._trader.plan(resolved_instrument, analyst_signals, debate)
        risk_verdict = self._risk_manager.review(resolved_instrument, context, trade_intent, freshness_summary)
        packet = self._packager.packet(trade_intent, risk_verdict)
        evidence_blocks = self._packager.evidence_blocks(context, analyst_signals)
        if self._feedback is not None:
            self._feedback.record(
                workspace_id=workspace_id,
                instrument=resolved_instrument,
                query=query,
                packet=packet,
                risk_verdict=risk_verdict,
                replay_summary=context.get("replay_summary"),
                analyst_signals=analyst_signals,
                supervisor_plan=supervisor_plan,
            )
        degrade_reason = (
            risk_verdict.kill_switch_reasons[0]
            if risk_verdict.kill_switch_reasons
            else context.get("replay_summary", {}).get("veto_reason")
        )
        return {
            "instrument": resolved_instrument,
            "context": context,
            "freshness_summary": freshness_summary,
            "provider_health": context.get("provider_health"),
            "replay_summary": context.get("replay_summary"),
            "analyst_signals": analyst_signals,
            "debate": debate,
            "trade_intent": trade_intent,
            "risk_verdict": risk_verdict,
            "packet": packet,
            "evidence_blocks": evidence_blocks,
            "degrade_reason": degrade_reason,
            "role_lens": role_lens,
            "supervisor_plan": supervisor_plan.model_dump(),
            "feedback_summary": feedback_summary,
        }

    def _analyst_signals(self, instrument: str, context: dict[str, Any], active_analysts: list[str]):
        available = {
            "MarketAnalyst": self._market_analyst,
            "QuantAnalyst": self._quant_analyst,
            "FundamentalsAnalyst": self._fundamentals_analyst,
            "NewsAnalyst": self._news_analyst,
            "SocialAnalyst": self._social_analyst,
            "MacroPolicyAnalyst": self._macro_policy_analyst,
        }
        return [
            available[name].analyze(instrument, context)
            for name in active_analysts
            if name in available
        ]

    @staticmethod
    def _build_feedback_memory(settings: Settings | None) -> FinanceFeedbackMemory | None:
        if settings is None:
            return None
        path = Path(settings.runtime_state_dir) / "finance_feedback.sqlite3"
        return FinanceFeedbackMemory(path)
