"""Replay-backed finance feedback memory."""

from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

from stratos_orchestrator.application.finance.supervisor import FinanceSupervisorPlan
from stratos_orchestrator.application.persistence import SqliteStore
from stratos_orchestrator.domain.entities import AnalystSignal, DecisionPacket, RiskVerdict


class FinanceFeedbackMemory:
    """Persist finance decisions and summarize recent outcomes."""

    def __init__(self, path: str | Path) -> None:
        self._store = SqliteStore(path)

    def record(
        self,
        *,
        workspace_id: str,
        instrument: str,
        query: str,
        packet: DecisionPacket,
        risk_verdict: RiskVerdict,
        replay_summary: dict[str, Any] | None,
        analyst_signals: list[AnalystSignal],
        supervisor_plan: FinanceSupervisorPlan,
    ) -> None:
        key = f"{int(time.time() * 1_000_000)}:{instrument}"
        self._store.put(
            ("finance-feedback", workspace_id, instrument),
            key,
            {
                "query": query,
                "packet": asdict(packet),
                "risk_verdict": asdict(risk_verdict),
                "replay_summary": replay_summary or {},
                "analyst_signals": [asdict(signal) for signal in analyst_signals],
                "supervisor_plan": supervisor_plan.model_dump(),
            },
        )

    def summary(self, *, workspace_id: str, instrument: str, limit: int = 12) -> dict[str, Any]:
        items = self._store.search(("finance-feedback", workspace_id, instrument), limit=limit)
        records = [item.value for item in items if isinstance(item.value, dict)]
        if not records:
            return {"observations": 0, "avg_realized_move": 0.0, "veto_rate": 0.0}
        realized_moves = [
            float(record.get("replay_summary", {}).get("realized_move", 0.0) or 0.0)
            for record in records
            if isinstance(record.get("replay_summary", {}), dict)
        ]
        vetoes = 0
        for record in records:
            packet = record.get("packet", {})
            if isinstance(packet, dict) and packet.get("action") == "NO_TRADE":
                vetoes += 1
        last_packet = records[0].get("packet", {}) if isinstance(records[0].get("packet", {}), dict) else {}
        return {
            "observations": len(records),
            "avg_realized_move": mean(realized_moves) if realized_moves else 0.0,
            "veto_rate": vetoes / max(len(records), 1),
            "last_action": last_packet.get("action"),
            "last_confidence": last_packet.get("confidence"),
        }
