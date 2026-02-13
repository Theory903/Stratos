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
class StrategicMemo:
    """Structured output from the agent."""
    query: str
    recommendation: str
    confidence: ConfidenceBand
    scenario_tree: list[dict]
    worst_case: str
    risk_band: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
