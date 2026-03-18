"""V5 runtime contracts — state, signals, and structured output schemas.

All models here are Pydantic-based so they work directly with
``model.with_structured_output(Schema)`` and serialise cleanly into
LangGraph checkpoints.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class V5Mode(StrEnum):
    """Routing modes the supervisor can select."""

    FAST_PATH = "fast_path"
    COUNCIL = "council"
    RESEARCH = "research"
    REPLAY = "replay"
    CLARIFICATION = "clarification"


class MemoryWriteReason(StrEnum):
    """Why the memory writer is creating a durable record."""

    FINAL_PACKET = "final_packet"
    USER_PREFERENCE = "user_preference"
    APPROVAL_EVENT = "approval_event"
    REPLAY_LESSON = "replay_lesson"


# ---------------------------------------------------------------------------
# Specialist signals
# ---------------------------------------------------------------------------


class SpecialistSignal(BaseModel):
    """Structured output from a single specialist node."""

    domain: str = Field(description="Specialist domain: market | news | social | macro | portfolio")
    score: float = Field(ge=-1.0, le=1.0, description="Directional score, -1 bearish to +1 bullish")
    confidence: float = Field(ge=0.0, le=1.0, description="How confident the specialist is")
    thesis: str = Field(description="One-paragraph thesis grounding the score")
    evidence_ids: list[str] = Field(default_factory=list, description="IDs of evidence items used")
    freshness_flag: bool = Field(default=True, description="Whether underlying data is fresh enough")


class AggregatedSignals(BaseModel):
    """Merged view of all specialist signals."""

    signals: list[SpecialistSignal] = Field(default_factory=list)
    consensus_direction: str = Field(default="neutral", description="bull | bear | neutral | mixed")
    consensus_score: float = Field(default=0.0, description="Weighted average score")
    consensus_confidence: float = Field(default=0.0, description="Harmonic mean of confidences")
    conflict_note: str = Field(default="", description="Where specialists disagree")


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


class ResearchBrief(BaseModel):
    """Synthesis of bull/bear research with evidence."""

    bull_thesis: str = ""
    bear_thesis: str = ""
    synthesis: str = ""
    verdict: str = "hold"
    confidence: float = 0.5
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HITL approval
# ---------------------------------------------------------------------------


class ApprovalRequest(BaseModel):
    """Payload surfaced to the user when the graph pauses at approval_gate."""

    approval_id: str
    instrument: str = ""
    action: str = ""
    thesis: str = ""
    risk_summary: str = ""
    position_size_pct: float = 0.0
    capital_at_risk: float = 0.0


class ApprovalDecision(BaseModel):
    """Structured resume payload for the approval gate.

    The frontend sends this back via ``POST /orchestrate/v5/resume``.
    """

    approval_id: str
    approved: bool
    note: str | None = None


# ---------------------------------------------------------------------------
# Risk / Trade
# ---------------------------------------------------------------------------


class TradeIntentV5(BaseModel):
    """Structured output from the trader agent."""

    instrument: str = ""
    action: str = ""
    score: float = 0.0
    confidence: float = 0.0
    thesis: str = ""
    entry_zone: str = ""
    stop_loss: str = ""
    take_profit: str = ""
    max_holding_period: str = ""


class RiskVerdictV5(BaseModel):
    """Structured output from the deterministic risk engine."""

    allowed: bool = False
    regime: str = "normal"
    value_at_risk_95: float = 0.0
    concentration_risk: float = 0.0
    position_size_pct: float = 0.0
    capital_at_risk: float = 0.0
    kill_switch_reasons: list[str] = Field(default_factory=list)
    rationale: str = ""


class DecisionPacketV5(BaseModel):
    """Final packaged output that lands in the frontend and memory."""

    instrument: str = ""
    action: str = ""
    confidence: float = 0.0
    score: float = 0.0
    thesis: str = ""
    entry_zone: str = ""
    stop_loss: str = ""
    take_profit: str = ""
    max_holding_period: str = ""
    position_size_pct: float = 0.0
    capital_at_risk: float = 0.0
    kill_switch_reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Supervisor classification
# ---------------------------------------------------------------------------


class SupervisorDecision(BaseModel):
    """Structured output from the supervisor node."""

    mode: V5Mode = Field(description="Which pipeline path to route to")
    rationale: str = Field(default="", description="One-line reasoning for the routing choice")
    delegates: list[str] = Field(
        default_factory=list,
        description="Specialist domains to activate (council mode only)",
    )


# ---------------------------------------------------------------------------
# Evidence & freshness
# ---------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    """A single piece of grounded evidence."""

    id: str
    source: str = ""
    content: str = ""
    timestamp: str = ""
    reliability: float = 1.0


class FreshnessSummary(BaseModel):
    """Staleness check across all data feeds."""

    all_fresh: bool = True
    stale_feeds: list[str] = Field(default_factory=list)
    oldest_timestamp: str = ""


class ProviderHealth(BaseModel):
    """Health status of upstream data providers."""

    healthy: bool = True
    degraded_providers: list[str] = Field(default_factory=list)
    outage_providers: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Memory write policy
# ---------------------------------------------------------------------------


class MemoryWriteRecord(BaseModel):
    """What gets persisted to long-term memory."""

    reason: MemoryWriteReason
    query: str = ""
    decision: str = ""
    summary: str = ""
    user_preference: str | None = None
    approval_event: dict[str, Any] | None = None
    replay_lesson: str | None = None


# ---------------------------------------------------------------------------
# Graph state (TypedDict for LangGraph)
# ---------------------------------------------------------------------------


class V5State(BaseModel):
    """Full state flowing through the V5 graph.

    Uses Pydantic so it works with LangGraph's ``StateGraph`` and serialises
    cleanly into checkpoints.  The ``messages`` field uses the
    ``add_messages`` reducer so LangGraph appends rather than overwrites.
    """

    # --- identity / threading ---
    query: str = ""
    thread_id: str = ""
    user_id: str = "anonymous"
    workspace_id: str = "default"

    # --- routing ---
    mode: V5Mode | None = None
    current_stage: str = ""

    # --- specialist council ---
    signals: list[dict[str, Any]] = Field(default_factory=list)
    aggregated_signals: dict[str, Any] | None = None

    # --- research ---
    research: dict[str, Any] | None = None

    # --- risk / trade ---
    trade_intent: dict[str, Any] | None = None
    risk_verdict: dict[str, Any] | None = None

    # --- HITL ---
    approval_request: dict[str, Any] | None = None
    approval_decision: dict[str, Any] | None = None
    interrupt_payload: dict[str, Any] | None = None

    # --- output ---
    final_packet: dict[str, Any] | None = None

    # --- evidence / health ---
    evidence_items: list[dict[str, Any]] = Field(default_factory=list)
    freshness_summary: dict[str, Any] | None = None
    provider_health: dict[str, Any] | None = None

    # --- memory ---
    memory_context: str = ""
    memory_reads: list[dict[str, Any]] = Field(default_factory=list)
    memory_writes: list[dict[str, Any]] = Field(default_factory=list)

    # --- degradation ---
    degrade_reason: str = ""

    # --- messages (append-only via add_messages reducer) ---
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
