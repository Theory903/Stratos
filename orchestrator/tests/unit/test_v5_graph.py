"""V5 contract and graph tests — no LLM, no network calls."""

from __future__ import annotations

import asyncio

import pytest

from stratos_orchestrator.application.v5.contracts import (
    AggregatedSignals,
    ApprovalDecision,
    ApprovalRequest,
    DecisionPacketV5,
    MemoryWriteReason,
    MemoryWriteRecord,
    RiskVerdictV5,
    SpecialistSignal,
    SupervisorDecision,
    TradeIntentV5,
    V5Mode,
    V5State,
)
from stratos_orchestrator.application.v5_graph import (
    _heuristic_mode,
    build_v5_graph,
    entry_guard,
    fast_path,
)
from stratos_orchestrator.application.v5.persistence import (
    create_checkpointer,
    create_store,
)


# =========================================================================
# Contract tests
# =========================================================================


class TestV5State:
    def test_default_state(self):
        state = V5State()
        assert state.query == ""
        assert state.mode is None
        assert state.signals == []
        assert state.memory_writes == []

    def test_state_with_values(self):
        state = V5State(
            query="Buy AAPL?",
            thread_id="t-123",
            user_id="u-456",
            mode=V5Mode.COUNCIL,
        )
        assert state.query == "Buy AAPL?"
        assert state.mode == V5Mode.COUNCIL
        assert state.thread_id == "t-123"

    def test_state_serialises(self):
        state = V5State(query="test", mode=V5Mode.FAST_PATH)
        data = state.model_dump()
        assert data["mode"] == "fast_path"
        roundtrip = V5State.model_validate(data)
        assert roundtrip.mode == V5Mode.FAST_PATH


class TestSpecialistSignal:
    def test_valid_signal(self):
        signal = SpecialistSignal(
            domain="market",
            score=0.7,
            confidence=0.85,
            thesis="Bullish momentum.",
        )
        assert signal.score == 0.7
        assert signal.freshness_flag is True

    def test_score_bounds(self):
        with pytest.raises(Exception):
            SpecialistSignal(
                domain="market",
                score=2.0,
                confidence=0.5,
                thesis="Invalid",
            )


class TestApproval:
    def test_approval_request_roundtrip(self):
        req = ApprovalRequest(
            approval_id="a-1",
            instrument="AAPL",
            action="buy",
            thesis="Strong momentum",
            risk_summary="Low risk",
            position_size_pct=5.0,
            capital_at_risk=10000.0,
        )
        data = req.model_dump()
        assert data["approval_id"] == "a-1"

    def test_approval_decision(self):
        decision = ApprovalDecision(
            approval_id="a-1",
            approved=True,
            note="Proceed",
        )
        assert decision.approved is True


class TestSupervisorDecision:
    def test_default(self):
        d = SupervisorDecision(mode=V5Mode.FAST_PATH)
        assert d.mode == V5Mode.FAST_PATH
        assert d.delegates == []


class TestMemoryWriteRecord:
    def test_final_packet_reason(self):
        record = MemoryWriteRecord(
            reason=MemoryWriteReason.FINAL_PACKET,
            query="Buy AAPL?",
            decision="buy",
            summary="Momentum thesis",
        )
        assert record.reason == MemoryWriteReason.FINAL_PACKET

    def test_approval_event_reason(self):
        record = MemoryWriteRecord(
            reason=MemoryWriteReason.APPROVAL_EVENT,
            query="Buy AAPL?",
            approval_event={"approved": True},
        )
        data = record.model_dump()
        assert data["approval_event"]["approved"] is True


# =========================================================================
# Heuristic routing tests
# =========================================================================


class TestHeuristicMode:
    def test_price_query(self):
        assert _heuristic_mode("What is the BTC price?") == V5Mode.FAST_PATH

    def test_trade_query(self):
        assert _heuristic_mode("Should I buy AAPL shares and allocate 10% of portfolio?") == V5Mode.COUNCIL

    def test_research_query(self):
        assert _heuristic_mode("Research the semiconductor industry trends") == V5Mode.RESEARCH

    def test_replay_query(self):
        assert _heuristic_mode("Replay my last decision from yesterday") == V5Mode.REPLAY

    def test_short_unknown_defaults_fast(self):
        assert _heuristic_mode("Hello there") == V5Mode.FAST_PATH


# =========================================================================
# Node tests (deterministic nodes only)
# =========================================================================


class TestEntryGuard:
    def test_empty_query_triggers_clarification(self):
        state = V5State(query="")
        result = entry_guard(state)
        assert result["mode"] == V5Mode.CLARIFICATION

    def test_valid_query_passes(self):
        state = V5State(query="Buy AAPL?")
        result = entry_guard(state)
        assert result.get("mode") is None  # no forcing
        assert result["current_stage"] == "entry_guard"

    def test_provider_outage_sets_degrade(self):
        state = V5State(
            query="Buy AAPL?",
            provider_health={"outage_providers": ["news_api"]},
        )
        result = entry_guard(state)
        assert "news_api" in result["degrade_reason"]


class TestFastPath:
    def test_produces_final_packet(self):
        state = V5State(query="BTC price")
        result = fast_path(state)
        assert result["final_packet"]["action"] == "info"


# =========================================================================
# Graph compilation tests
# =========================================================================


class TestGraphCompilation:
    def test_graph_compiles(self):
        """Graph must compile without errors."""
        graph = build_v5_graph()
        assert graph is not None

    def test_graph_compiles_with_checkpointer(self):
        """Graph compiles with a real checkpointer."""
        from langgraph.checkpoint.memory import InMemorySaver

        graph = build_v5_graph(checkpointer=InMemorySaver())
        assert graph is not None

    @pytest.mark.asyncio
    async def test_fast_path_end_to_end(self):
        """A short query should route through fast_path and reach END."""
        from langgraph.checkpoint.memory import InMemorySaver

        graph = build_v5_graph(checkpointer=InMemorySaver())
        result = await graph.ainvoke(
            {"query": "What is the latest BTC price?"},
            config={"configurable": {"thread_id": "test-fast-path"}},
        )
        assert result["mode"] == V5Mode.FAST_PATH
        assert result["final_packet"]["action"] == "info"

    @pytest.mark.asyncio
    async def test_empty_query_routes_to_clarification(self):
        """Empty query → entry_guard → supervisor → clarification_node → END."""
        from langgraph.checkpoint.memory import InMemorySaver

        graph = build_v5_graph(checkpointer=InMemorySaver())
        result = await graph.ainvoke(
            {"query": ""},
            config={"configurable": {"thread_id": "test-clarification"}},
        )
        assert result["mode"] == V5Mode.CLARIFICATION
        assert result["final_packet"]["action"] == "clarification_needed"


# =========================================================================
# Persistence tests
# =========================================================================


class TestPersistence:
    def test_create_checkpointer_returns_saver(self):
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.v5_postgres_dsn = ""
        settings.v5_sqlite_path = None
        saver = create_checkpointer(settings)
        assert saver is not None

    def test_create_store_returns_store(self):
        from unittest.mock import MagicMock

        settings = MagicMock()
        store = create_store(settings)
        assert store is not None

    @pytest.mark.asyncio
    async def test_checkpoint_roundtrip(self):
        """Same thread_id should continue the same graph run."""
        from langgraph.checkpoint.memory import InMemorySaver

        checkpointer = InMemorySaver()
        graph = build_v5_graph(checkpointer=checkpointer)

        # First invocation
        result1 = await graph.ainvoke(
            {"query": "BTC price"},
            config={"configurable": {"thread_id": "roundtrip-1"}},
        )
        assert result1["mode"] == V5Mode.FAST_PATH

        # Second invocation on same thread — should succeed
        result2 = await graph.ainvoke(
            {"query": "ETH price"},
            config={"configurable": {"thread_id": "roundtrip-1"}},
        )
        assert result2["mode"] == V5Mode.FAST_PATH
