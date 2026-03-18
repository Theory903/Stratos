"""Adaptive finance supervisor for analyst selection and routing."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from stratos_orchestrator.config import Settings


ANALYST_NAMES = [
    "MarketAnalyst",
    "QuantAnalyst",
    "FundamentalsAnalyst",
    "NewsAnalyst",
    "SocialAnalyst",
    "MacroPolicyAnalyst",
]


class FinanceSupervisorPlan(BaseModel):
    active_analysts: list[Literal["MarketAnalyst", "QuantAnalyst", "FundamentalsAnalyst", "NewsAnalyst", "SocialAnalyst", "MacroPolicyAnalyst"]] = Field(default_factory=list)
    reasoning_mode: Literal["fast", "balanced", "deep"] = "balanced"
    risk_posture: Literal["aggressive", "normal", "defensive"] = "normal"
    requires_debate: bool = True
    rationale: str = ""


class FinanceSupervisor:
    """Model-routed finance supervisor with deterministic fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._model: BaseChatModel | None = None

    async def decide(
        self,
        *,
        query: str,
        instrument: str,
        context: dict[str, Any],
        feedback_summary: dict[str, Any] | None = None,
    ) -> FinanceSupervisorPlan:
        if self._settings is None:
            return self._fallback_plan(instrument=instrument, context=context)
        try:
            model = self._model or self._build_model()
            self._model = model
            planner = model.with_structured_output(FinanceSupervisorPlan)
            context_summary = self._context_summary(instrument=instrument, context=context, feedback_summary=feedback_summary)
            result = await planner.ainvoke(
                [
                    (
                        "system",
                        "You are the STRATOS finance supervisor. Choose which analysts should run for this request. "
                        "Only choose from: MarketAnalyst, QuantAnalyst, FundamentalsAnalyst, NewsAnalyst, SocialAnalyst, MacroPolicyAnalyst. "
                        "Use QuantAnalyst when market bars or order-book data are available. "
                        "Skip FundamentalsAnalyst for crypto, FX, and pure indices. "
                        "Use deep mode only when the request needs multiple conflicting views. "
                        "Set defensive posture when replay or risk data shows recent vetoes, risk_off, or weak freshness. "
                        "Prefer the smallest set that still captures edge."
                    ),
                    (
                        "human",
                        f"Query: {query}\nInstrument: {instrument}\nContext summary: {context_summary}",
                    ),
                ]
            )
            if isinstance(result, FinanceSupervisorPlan):
                return self._normalize_plan(result, instrument=instrument, context=context)
            if hasattr(result, "model_dump"):
                return self._normalize_plan(FinanceSupervisorPlan.model_validate(result.model_dump()), instrument=instrument, context=context)
            return self._normalize_plan(FinanceSupervisorPlan.model_validate(result), instrument=instrument, context=context)
        except Exception:
            return self._fallback_plan(instrument=instrument, context=context)

    def _build_model(self) -> BaseChatModel:
        assert self._settings is not None
        provider = self._settings.llm_provider
        explicit_model = self._settings.langchain_agent_model
        if provider == "ollama":
            return ChatOllama(
                model=explicit_model or self._settings.ollama_model,
                base_url=self._settings.ollama_base_url,
                temperature=0.1,
            )
        if provider == "groq":
            return ChatOpenAI(
                model=explicit_model or self._settings.groq_model,
                api_key=self._settings.groq_api_key,
                base_url=self._settings.groq_api_base,
                temperature=0.1,
                max_tokens=self._settings.langchain_agent_max_tokens,
            )
        return ChatOpenAI(
            model=explicit_model or self._settings.openai_model,
            api_key=self._settings.openai_api_key,
            temperature=0.1,
            max_tokens=self._settings.langchain_agent_max_tokens,
        )

    def _fallback_plan(self, *, instrument: str, context: dict[str, Any]) -> FinanceSupervisorPlan:
        analysts = ["MarketAnalyst", "NewsAnalyst", "MacroPolicyAnalyst"]
        if self._has_market_features(context):
            analysts.insert(1, "QuantAnalyst")
        if context.get("social"):
            analysts.append("SocialAnalyst")
        if not instrument.startswith(("X:", "FX:", "INDEX:")):
            analysts.insert(2 if "QuantAnalyst" in analysts else 1, "FundamentalsAnalyst")
        posture = "defensive" if self._is_defensive_context(context) else "normal"
        mode = "deep" if len(analysts) >= 5 else "balanced"
        return FinanceSupervisorPlan(
            active_analysts=analysts,
            reasoning_mode=mode,
            risk_posture=posture,
            requires_debate=True,
            rationale="Fallback supervisor used available market, event, and risk signals.",
        )

    def _normalize_plan(self, plan: FinanceSupervisorPlan, *, instrument: str, context: dict[str, Any]) -> FinanceSupervisorPlan:
        allowed = []
        for analyst in plan.active_analysts:
            if analyst not in ANALYST_NAMES:
                continue
            if analyst == "FundamentalsAnalyst" and instrument.startswith(("X:", "FX:", "INDEX:")):
                continue
            if analyst == "QuantAnalyst" and not self._has_market_features(context):
                continue
            if analyst not in allowed:
                allowed.append(analyst)
        if "MarketAnalyst" not in allowed:
            allowed.insert(0, "MarketAnalyst")
        if not instrument.startswith(("X:", "FX:", "INDEX:")) and "FundamentalsAnalyst" not in allowed:
            allowed.append("FundamentalsAnalyst")
        if self._has_market_features(context) and "QuantAnalyst" not in allowed:
            allowed.append("QuantAnalyst")
        if not context.get("social") and "SocialAnalyst" in allowed:
            allowed.remove("SocialAnalyst")
        if not context.get("news") and "NewsAnalyst" not in allowed:
            allowed.append("NewsAnalyst")
        if "MacroPolicyAnalyst" not in allowed:
            allowed.append("MacroPolicyAnalyst")
        return FinanceSupervisorPlan(
            active_analysts=allowed,
            reasoning_mode=plan.reasoning_mode,
            risk_posture="defensive" if self._is_defensive_context(context) else plan.risk_posture,
            requires_debate=plan.requires_debate,
            rationale=plan.rationale or "Supervisor selected analysts from available market and context signals.",
        )

    @staticmethod
    def _has_market_features(context: dict[str, Any]) -> bool:
        market = context.get("market")
        if isinstance(market, dict) and market.get("bars"):
            return True
        if isinstance(market, list) and market:
            return True
        return context.get("order_book") is not None

    @staticmethod
    def _is_defensive_context(context: dict[str, Any]) -> bool:
        risk = context.get("portfolio_risk") if isinstance(context.get("portfolio_risk"), dict) else {}
        regime = str((risk.get("regime") or {}).get("regime_label", "")).lower()
        replay = context.get("replay_summary") if isinstance(context.get("replay_summary"), dict) else {}
        freshness = context.get("freshness_summary") if isinstance(context.get("freshness_summary"), dict) else {}
        return "risk_off" in regime or replay.get("outcome_label") == "vetoed" or not freshness.get("market_ready", True)

    @staticmethod
    def _context_summary(*, instrument: str, context: dict[str, Any], feedback_summary: dict[str, Any] | None) -> str:
        news_count = len(context.get("news", []))
        social_count = len(context.get("social", []))
        policy_count = len(context.get("policy", []))
        market_payload = context.get("market") or {}
        if isinstance(market_payload, dict):
            bar_count = len(market_payload.get("bars", []))
        elif isinstance(market_payload, list):
            bar_count = len(market_payload)
        else:
            bar_count = 0
        order_book_ready = context.get("order_book") is not None
        replay = context.get("replay_summary") if isinstance(context.get("replay_summary"), dict) else {}
        feedback_line = ""
        if feedback_summary:
            feedback_line = (
                f", prior runs={feedback_summary.get('observations', 0)}, "
                f"avg_realized_move={feedback_summary.get('avg_realized_move', 0.0):.4f}, "
                f"veto_rate={feedback_summary.get('veto_rate', 0.0):.2f}"
            )
        return (
            f"bars={bar_count}, order_book_ready={order_book_ready}, news_count={news_count}, "
            f"social_count={social_count}, policy_count={policy_count}, "
            f"replay_outcome={replay.get('outcome_label')}, instrument={instrument}{feedback_line}"
        )
