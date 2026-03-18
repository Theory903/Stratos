from __future__ import annotations

from fastapi.testclient import TestClient

from stratos_orchestrator.api.app import create_app
from stratos_orchestrator.api.deps import (
    get_langchain_agent_runtime,
    get_v2_orchestrate_use_case,
    get_v4_graph_runtime,
)
from stratos_orchestrator.domain.entities import ConfidenceBand, StrategicMemo


def _memo(*, role: str = "general", intent: str = "research", decision: str = "Ready.") -> StrategicMemo:
    return StrategicMemo(
        query="test query",
        plan_summary="stub plan",
        tasks=[],
        confidence_band=ConfidenceBand.from_score(0.72),
        risk_policy_status="PASS",
        recommendation="stub recommendation",
        worst_case="stub worst case",
        risk_band="Low",
        intent=intent,
        role=role,
        decision=decision,
        summary="stub summary",
        key_findings=["finding"],
        recommended_actions=["action"],
        evidence_blocks=[{"title": "Stub", "detail": "Stub detail"}],
    )


class StubV2UseCase:
    async def execute(self, query: str) -> StrategicMemo:
        return _memo(role="pm", intent="portfolio", decision="V2 ready.")


class StubV3Runtime:
    async def execute(self, query: str, *, thread_id: str, user_id: str) -> StrategicMemo:
        return _memo(role="general", intent="research", decision="V3 ready.")


class StubV4Runtime:
    async def execute(
        self,
        *,
        inputs,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str | None = None,
        response_mode_hint: str | None = None,
        approval_response=None,
    ):
        memo = _memo(role=role_lens or "general", intent="research", decision="V4 ready.")
        trace = {
            "status": "completed",
            "thread_refs": {
                "thread_id": thread_id,
                "run_id": "run:test",
            },
            "answer_mode": "grounded_direct",
            "path": "langchain_v3_delegate",
            "delegate_runtime": "langchain_v3",
        }
        return memo, trace


def test_orchestrate_v2_v3_v4_routes_return_stable_envelopes() -> None:
    app = create_app()
    app.dependency_overrides[get_v2_orchestrate_use_case] = lambda: StubV2UseCase()
    app.dependency_overrides[get_langchain_agent_runtime] = lambda: StubV3Runtime()
    app.dependency_overrides[get_v4_graph_runtime] = lambda: StubV4Runtime()
    client = TestClient(app)

    v2_response = client.post("/orchestrate/v2", json={"query": "portfolio test"})
    assert v2_response.status_code == 200
    assert v2_response.json()["decision"] == "V2 ready."
    assert v2_response.json()["intent"] == "portfolio"

    v3_response = client.post("/orchestrate/v3", json={"query": "general test"})
    assert v3_response.status_code == 200
    assert v3_response.json()["decision"] == "V3 ready."
    assert v3_response.json()["role"] == "general"

    v4_response = client.post(
        "/orchestrate/v4",
        json={"query": "adaptive test", "role_lens": "general", "workspace_id": "workspace-test"},
    )
    assert v4_response.status_code == 200
    assert v4_response.json()["decision"] == "V4 ready."
    assert v4_response.json()["trace"]["delegate_runtime"] == "langchain_v3"
