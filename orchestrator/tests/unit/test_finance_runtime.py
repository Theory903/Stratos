from __future__ import annotations

import pytest

from stratos_orchestrator.adapters.tools.registry import ToolRegistry
from stratos_orchestrator.application.finance.feedback import FinanceFeedbackMemory
from stratos_orchestrator.application.finance.resolver import InstrumentResolver
from stratos_orchestrator.application.finance.supervisor import FinanceSupervisorPlan
from stratos_orchestrator.application.finance_council import FinanceCouncilRuntime
from stratos_orchestrator.domain.entities import AnalystSignal, DecisionPacket, RiskVerdict


class FakeTool:
    def __init__(self, name: str, result: dict) -> None:
        self._name = name
        self._result = result
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._name

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, arguments: dict) -> dict:
        self.calls.append(arguments)
        return self._result


class RaisingTool(FakeTool):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(name, {})
        self._message = message

    async def execute(self, arguments: dict) -> dict:
        self.calls.append(arguments)
        raise RuntimeError(self._message)


def test_instrument_resolver_handles_india_indices_crypto_and_fx() -> None:
    resolver = InstrumentResolver()

    assert resolver.resolve("Should I add risk in Bank Nifty this week?") == "INDEX:BANKNIFTY"
    assert resolver.resolve("How does BTC look now?") == "X:BTCUSD"
    assert resolver.resolve("What is the INR vs USD setup today?") == "FX:INRUSD"
    assert resolver.resolve("Check NSE_EQ|INE009A01021 momentum") == "NSE_EQ|INE009A01021"


@pytest.mark.asyncio
async def test_finance_council_runtime_uses_extracted_modules_and_stable_payload() -> None:
    registry = ToolRegistry()
    market_tool = FakeTool(
        "market_analyze",
        {
            "ticker": "AAPL",
            "bars": [
                {"timestamp": "2026-03-17T09:15:00+00:00", "close": "180.0"},
                {"timestamp": "2026-03-16T09:15:00+00:00", "close": "175.0"},
                {"timestamp": "2026-03-15T09:15:00+00:00", "close": "170.0"},
            ],
        },
    )
    company_tool = FakeTool(
        "company_analyze",
        {
            "profile": {
                "earnings_quality": 0.8,
                "free_cash_flow_stability": 0.75,
                "moat_score": 0.7,
                "fraud_score": 0.1,
                "leverage_ratio": 0.2,
            }
        },
    )
    news_tool = FakeTool(
        "company_news_analyze",
        {
            "items": [
                {"event_id": "news-1", "headline": "Apple demand holds", "summary": "Channel checks stabilized.", "sentiment": 0.4}
            ]
        },
    )
    social_tool = FakeTool(
        "social_analyze",
        {
            "items": [
                {"event_id": "social-1", "headline": "Crowd tone improving", "sentiment": 0.3}
            ]
        },
    )
    portfolio_tool = FakeTool(
        "portfolio_analyze",
        {
            "risk": {
                "estimated_daily_volatility": 0.02,
                "value_at_risk_95": 0.03,
                "concentration_risk": 0.1,
                "risk_flags": [],
                "regime": {"regime_label": "risk_on"},
            }
        },
    )
    policy_tool = FakeTool(
        "policy_events_analyze",
        {"items": [{"event_id": "policy-1", "headline": "RBI steady", "summary": "No surprise.", "sentiment": 0.0}]},
    )
    order_book_tool = FakeTool(
        "order_book_analyze",
        {"snapshot": {"instrument": "AAPL", "top_bid_price": 179.9, "top_ask_price": 180.1}},
    )
    provider_health_tool = FakeTool(
        "provider_health_analyze",
        {
            "overall_status": "healthy",
            "providers": [
                {"provider": "upstox", "status": "healthy"},
                {"provider": "coinapi", "status": "healthy"},
            ],
        },
    )
    replay_tool = FakeTool(
        "replay_decision_analyze",
        {
            "requested_as_of": "2026-03-16T09:15:00+00:00",
            "replayed_decision": "BUY",
            "historical_move": 0.06,
            "decision_packet": {"confidence": 0.74, "kill_switch_reasons": []},
            "risk_verdict": {"allowed": True, "kill_switch_reasons": []},
            "freshness_summary": {"notes": ["Replay used historical bars."]},
        },
    )

    for tool in (
        market_tool,
        company_tool,
        news_tool,
        social_tool,
        portfolio_tool,
        policy_tool,
        order_book_tool,
        provider_health_tool,
        replay_tool,
    ):
        registry.register(tool)

    runtime = FinanceCouncilRuntime(registry)
    memo, trace = await runtime.execute(query="Should I add AAPL risk now?", role_lens="pm", workspace_id="workspace-1")

    assert memo.decision_packet is not None
    assert memo.risk_verdict is not None
    assert memo.freshness_summary is not None
    assert memo.provider_health is not None
    assert memo.replay_summary is not None
    assert len(memo.analyst_signals) >= 5
    assert any(signal["analyst"] == "QuantAnalyst" for signal in memo.analyst_signals)
    assert trace["mode"] == "finance_council"
    assert trace["answer_mode"] == "decision_with_limits"
    assert trace["supervisor_plan"] is not None
    assert "QuantAnalyst" in trace["supervisor_plan"]["active_analysts"]
    assert company_tool.calls
    assert policy_tool.calls
    assert order_book_tool.calls
    assert provider_health_tool.calls == [{}]
    assert replay_tool.calls


@pytest.mark.asyncio
async def test_finance_council_runtime_degrades_when_optional_sources_fail() -> None:
    registry = ToolRegistry()
    registry.register(
        FakeTool(
            "market_analyze",
            {
                "ticker": "AAPL",
                "bars": [
                    {"timestamp": "2026-03-17T09:15:00+00:00", "close": "180.0"},
                    {"timestamp": "2026-03-16T09:15:00+00:00", "close": "175.0"},
                ],
            },
        )
    )
    registry.register(
        FakeTool(
            "portfolio_analyze",
            {
                "risk": {
                    "estimated_daily_volatility": 0.02,
                    "value_at_risk_95": 0.03,
                    "concentration_risk": 0.1,
                    "risk_flags": [],
                    "regime": {"regime_label": "risk_on"},
                }
            },
        )
    )
    registry.register(RaisingTool("social_analyze", "404 from data fabric"))
    registry.register(RaisingTool("company_news_analyze", "404 from data fabric"))
    registry.register(RaisingTool("order_book_analyze", "404 from data fabric"))

    runtime = FinanceCouncilRuntime(registry)
    memo, trace = await runtime.execute(query="Should I add AAPL risk now?", role_lens="pm", workspace_id="workspace-1")

    assert memo.freshness_summary is not None
    assert memo.freshness_summary["market_ready"] is True
    assert memo.freshness_summary["news_count"] == 0
    assert memo.freshness_summary["social_count"] == 0
    assert trace["mode"] == "finance_council"


def test_finance_feedback_memory_summarizes_recent_outcomes(tmp_path) -> None:
    memory = FinanceFeedbackMemory(tmp_path / "finance-feedback.sqlite3")

    signal = AnalystSignal(
        analyst="QuantAnalyst",
        instrument="AAPL",
        signal_score=0.3,
        confidence=0.7,
        direction="bullish",
        thesis="quant bullish",
    )
    packet = DecisionPacket(
        instrument="AAPL",
        action="BUY",
        confidence=0.7,
        score=0.22,
        thesis="buy thesis",
        entry_zone="entry",
        stop_loss="stop",
        take_profit="target",
        max_holding_period="10d",
        position_size_pct=0.02,
        capital_at_risk=0.0004,
    )
    verdict = RiskVerdict(
        allowed=True,
        regime="risk_on",
        value_at_risk_95=0.03,
        concentration_risk=0.12,
        position_size_pct=0.02,
        capital_at_risk=0.0004,
    )

    memory.record(
        workspace_id="workspace-1",
        instrument="AAPL",
        query="Should I buy AAPL?",
        packet=packet,
        risk_verdict=verdict,
        replay_summary={"realized_move": 0.04, "outcome_label": "accepted"},
        analyst_signals=[signal],
        supervisor_plan=FinanceSupervisorPlan(active_analysts=["QuantAnalyst"]),
    )
    memory.record(
        workspace_id="workspace-1",
        instrument="AAPL",
        query="Should I buy AAPL again?",
        packet=DecisionPacket(
            instrument="AAPL",
            action="NO_TRADE",
            confidence=0.3,
            score=0.02,
            thesis="no trade",
            entry_zone="n/a",
            stop_loss="n/a",
            take_profit="n/a",
            max_holding_period="10d",
            position_size_pct=0.0,
            capital_at_risk=0.0,
            kill_switch_reasons=["neutral"],
        ),
        risk_verdict=RiskVerdict(
            allowed=False,
            regime="risk_off",
            value_at_risk_95=0.03,
            concentration_risk=0.12,
            position_size_pct=0.0,
            capital_at_risk=0.0,
            kill_switch_reasons=["neutral"],
        ),
        replay_summary={"realized_move": -0.01, "outcome_label": "vetoed"},
        analyst_signals=[signal],
        supervisor_plan=FinanceSupervisorPlan(active_analysts=["QuantAnalyst"]),
    )

    summary = memory.summary(workspace_id="workspace-1", instrument="AAPL")

    assert summary["observations"] == 2
    assert summary["veto_rate"] == 0.5
    assert summary["last_action"] in {"BUY", "NO_TRADE"}
