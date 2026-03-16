"""Orchestrator domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime


class TaskStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class AgentTask:
    """A single task the agent must execute."""
    tool_name: str
    arguments: dict
    status: TaskStatus = TaskStatus.PENDING
    result: dict | None = None
    error: str | None = None


@dataclass(slots=True)
class ExecutionPlan:
    """Ordered list of tasks to execute."""
    query: str
    tasks: list[AgentTask] = field(default_factory=list)
    reasoning: str = ""


@dataclass(frozen=True, slots=True)
class ConfidenceBand:
    """Calibrated confidence band."""
    score: float
    calibration: str  # high, medium, low

    @classmethod
    def from_score(cls, score: float) -> ConfidenceBand:
        cal = "high" if score >= 0.8 else "medium" if score >= 0.5 else "low"
        return cls(score=score, calibration=cal)


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """Institutional risk constraints with Dynamic De-Risking (Subsystem G)."""
    max_allocation: float = 0.35
    max_leverage: float = 1.2
    max_drawdown_allowed: float = 0.20
    
    # Multi-dimensional constraints
    max_sector_concentration: float = 0.50  # No sector > 50%
    max_net_exposure: float = 1.0           # Net exposure limit
    
    # Crisis Certification triggers
    vix_crisis_threshold: float = 30.0    # Spike triggers ADR
    corr_spike_threshold: float = 0.8    # High asset correlation triggers ADR
    
    # De-risking multipliers
    crisis_mult: float = 0.5             # Cut limits by 50% in crisis
    stressed_mult: float = 0.8           # Cut limits by 20% in stress
    
    liquidity_guard_active: bool = True


@dataclass(frozen=True, slots=True)
class StrategicMemo:
    """Structured output from the agent with Governance status (Subsystem F/G)."""
    query: str
    plan_summary: str
    tasks: list[AgentTask]
    confidence_band: ConfidenceBand
    risk_policy_status: str              # PASS/FAIL/ADR_ACTIVE
    recommendation: str
    worst_case: str
    risk_band: str                       # e.g., "VaR 99%: 4.2%"
    policy_violations: list[str] = field(default_factory=list)
    system_regime: str = "normal"        # normal, stressed, crisis
    regime_stability: float = 1.0        # 0.0 - 1.0
    scenario_tree: list[dict] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)
