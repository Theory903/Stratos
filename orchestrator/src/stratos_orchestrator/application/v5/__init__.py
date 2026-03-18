"""V5 runtime package — LangGraph-native orchestration layer.

Public API:
    build_v5_graph()      — compile the V5 state graph
    V5State               — full state flowing through the graph
    V5Mode                — routing modes
    DecisionPacketV5      — final output contract
    ApprovalRequest       — HITL approval payload
    ApprovalDecision      — HITL resume payload
    create_checkpointer() — persistence factory
    create_store()        — store factory
    build_model()         — multi-provider model factory

Tool sets (lazy-loaded to avoid hard dependency on registry at import time):
    build_council_tools() — domain-scoped specialist tools
    build_fast_path_tools() — lookup-only tools
    build_replay_tools()  — history tools
    build_research_tools() — broad investigation tools
"""

from stratos_orchestrator.application.v5_graph import build_v5_graph

from stratos_orchestrator.application.v5.contracts import (
    AggregatedSignals,
    ApprovalDecision,
    ApprovalRequest,
    DecisionPacketV5,
    MemoryWriteReason,
    MemoryWriteRecord,
    ResearchBrief,
    RiskVerdictV5,
    SpecialistSignal,
    SupervisorDecision,
    TradeIntentV5,
    V5Mode,
    V5State,
)
from stratos_orchestrator.application.v5.persistence import (
    create_checkpointer,
    create_store,
)
from stratos_orchestrator.application.v5.builders import (
    build_model,
    build_middleware,
    build_structured_output,
)


def __getattr__(name: str):
    """Lazy-load tool_sets to avoid hard dependency on registry at import."""
    _tool_set_names = {
        "build_council_tools",
        "build_fast_path_tools",
        "build_replay_tools",
        "build_research_tools",
    }
    if name in _tool_set_names:
        from stratos_orchestrator.application.v5 import tool_sets

        return getattr(tool_sets, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Graph builder
    "build_v5_graph",
    # Contracts
    "V5State",
    "V5Mode",
    "SpecialistSignal",
    "AggregatedSignals",
    "ResearchBrief",
    "ApprovalRequest",
    "ApprovalDecision",
    "TradeIntentV5",
    "RiskVerdictV5",
    "DecisionPacketV5",
    "SupervisorDecision",
    "MemoryWriteReason",
    "MemoryWriteRecord",
    # Persistence
    "create_checkpointer",
    "create_store",
    # Builders
    "build_model",
    "build_middleware",
    "build_structured_output",
    # Tool Sets (lazy)
    "build_council_tools",
    "build_fast_path_tools",
    "build_replay_tools",
    "build_research_tools",
]
