"""Orchestrator API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from stratos_orchestrator.api.deps import (
    get_langchain_agent_runtime,
    get_orchestrate_use_case,
    get_stream_orchestrate_use_case,
    get_v4_graph_runtime,
    get_v5_graph_runtime,
    get_v2_orchestrate_use_case,
    get_v2_stream_orchestrate_use_case,
)
from stratos_orchestrator.application import LangChainAgentRuntime, OrchestrateUseCase, V2OrchestrateUseCase, V2StreamOrchestrateUseCase, V4GraphRuntime
from stratos_orchestrator.application.v5 import V5Mode
from stratos_orchestrator.application.v5_runtime import V5GraphRuntime
from stratos_orchestrator.application.v5.contracts import ApprovalDecision
from stratos_orchestrator.application.stream_orchestrate import StreamOrchestrateUseCase
from stratos_orchestrator.application.v4_graph import V4InputItem


router = APIRouter(tags=["Agent"])


class OrchestrateRequest(BaseModel):
    query: str
    thread_id: str | None = None
    user_id: str | None = None


class OrchestrateResponse(BaseModel):
    status: str = "completed"
    thread_id: str | None = None
    run_id: str | None = None
    approval_requests: list[dict] = []
    intent: str = "research"
    role: str = "pm"
    decision: str = ""
    summary: str = ""
    recommendation: str
    key_findings: list[str] = []
    historical_context: list[str] = []
    portfolio_impact: list[str] = []
    recommended_actions: list[str] = []
    watch_items: list[str] = []
    data_quality: list[str] = []
    evidence_blocks: list[dict] = []
    specialist_views: list[dict] = []
    confidence_score: float
    confidence_calibration: str
    risk_band: str
    worst_case: str
    scenarios: list[dict]
    decision_packet: dict | None = None
    analyst_signals: list[dict] = []
    risk_verdict: dict | None = None
    freshness_summary: dict | None = None
    provider_health: dict | None = None
    replay_summary: dict | None = None
    degrade_reason: str | None = None
    trace: dict | None = None  # Optional execution trace


class OrchestrateV4Request(BaseModel):
    query: str | None = None
    thread_id: str | None = None
    user_id: str | None = None
    workspace_id: str = "default"
    role_lens: str | None = None
    response_mode_hint: str | None = None
    approval_response: dict | bool | str | None = None
    inputs: list[V4InputItem] = Field(default_factory=list)


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_agent(
    request: OrchestrateRequest,
    use_case: Annotated[OrchestrateUseCase, Depends(get_orchestrate_use_case)],
) -> OrchestrateResponse:
    """Execute the AI agent to answer a strategic query."""
    
    memo = await use_case.execute(request.query)
    
    return OrchestrateResponse(
        intent=memo.intent,
        role=memo.role,
        decision=memo.decision,
        summary=memo.summary,
        recommendation=memo.recommendation,
        key_findings=memo.key_findings,
        historical_context=memo.historical_context,
        portfolio_impact=memo.portfolio_impact,
        recommended_actions=memo.recommended_actions,
        watch_items=memo.watch_items,
        data_quality=memo.data_quality,
        evidence_blocks=memo.evidence_blocks,
        confidence_score=memo.confidence_band.score,
        confidence_calibration=memo.confidence_band.calibration,
        risk_band=memo.risk_band,
        worst_case=memo.worst_case,
        scenarios=memo.scenario_tree,
    )


@router.post("/orchestrate/stream")
async def orchestrate_agent_stream(
    request: OrchestrateRequest,
    use_case: Annotated[StreamOrchestrateUseCase, Depends(get_stream_orchestrate_use_case)],
) -> StreamingResponse:
    """Execute the AI agent and stream progress via SSE."""
    
    return StreamingResponse(
        use_case.execute(request.query),
        media_type="text/event-stream",
    )


@router.post("/orchestrate/v2", response_model=OrchestrateResponse)
async def orchestrate_agent_v2(
    request: OrchestrateRequest,
    use_case: Annotated[V2OrchestrateUseCase, Depends(get_v2_orchestrate_use_case)],
) -> OrchestrateResponse:
    memo = await use_case.execute(request.query)
    return OrchestrateResponse(
        intent=memo.intent,
        role=memo.role,
        decision=memo.decision,
        summary=memo.summary,
        recommendation=memo.recommendation,
        key_findings=memo.key_findings,
        historical_context=memo.historical_context,
        portfolio_impact=memo.portfolio_impact,
        recommended_actions=memo.recommended_actions,
        watch_items=memo.watch_items,
        data_quality=memo.data_quality,
        evidence_blocks=memo.evidence_blocks,
        confidence_score=memo.confidence_band.score,
        confidence_calibration=memo.confidence_band.calibration,
        risk_band=memo.risk_band,
        worst_case=memo.worst_case,
        scenarios=memo.scenario_tree,
    )


@router.post("/orchestrate/v2/stream")
async def orchestrate_agent_stream_v2(
    request: OrchestrateRequest,
    use_case: Annotated[V2StreamOrchestrateUseCase, Depends(get_v2_stream_orchestrate_use_case)],
) -> StreamingResponse:
    return StreamingResponse(
        use_case.execute(request.query),
        media_type="text/event-stream",
    )


@router.post("/orchestrate/v3", response_model=OrchestrateResponse)
async def orchestrate_agent_v3(
    request: OrchestrateRequest,
    runtime: Annotated[LangChainAgentRuntime, Depends(get_langchain_agent_runtime)],
) -> OrchestrateResponse:
    thread_id = request.thread_id or f"thread:{abs(hash(request.query))}"
    user_id = request.user_id or "anonymous"
    memo = await runtime.execute(request.query, thread_id=thread_id, user_id=user_id)
    return OrchestrateResponse(
        intent=memo.intent,
        role=memo.role,
        decision=memo.decision,
        summary=memo.summary,
        recommendation=memo.recommendation,
        key_findings=memo.key_findings,
        historical_context=memo.historical_context,
        portfolio_impact=memo.portfolio_impact,
        recommended_actions=memo.recommended_actions,
        watch_items=memo.watch_items,
        data_quality=memo.data_quality,
        evidence_blocks=memo.evidence_blocks,
        confidence_score=memo.confidence_band.score,
        confidence_calibration=memo.confidence_band.calibration,
        risk_band=memo.risk_band,
        worst_case=memo.worst_case,
        scenarios=memo.scenario_tree,
    )


@router.post("/orchestrate/v3/stream")
async def orchestrate_agent_stream_v3(
    request: OrchestrateRequest,
    runtime: Annotated[LangChainAgentRuntime, Depends(get_langchain_agent_runtime)],
) -> StreamingResponse:
    thread_id = request.thread_id or f"thread:{abs(hash(request.query))}"
    user_id = request.user_id or "anonymous"
    return StreamingResponse(
        runtime.stream(request.query, thread_id=thread_id, user_id=user_id),
        media_type="text/event-stream",
    )


def _response_from_memo(memo, trace: dict | None = None) -> OrchestrateResponse:
    thread_refs = (trace or {}).get("thread_refs", {})
    return OrchestrateResponse(
        status=(trace or {}).get("status", "completed"),
        thread_id=thread_refs.get("thread_id"),
        run_id=thread_refs.get("run_id"),
        approval_requests=(trace or {}).get("approval_requests", []),
        intent=memo.intent,
        role=memo.role,
        decision=memo.decision,
        summary=memo.summary,
        recommendation=memo.recommendation,
        key_findings=memo.key_findings,
        historical_context=memo.historical_context,
        portfolio_impact=memo.portfolio_impact,
        recommended_actions=memo.recommended_actions,
        watch_items=memo.watch_items,
        data_quality=memo.data_quality,
        evidence_blocks=memo.evidence_blocks,
        specialist_views=memo.specialist_views,
        confidence_score=memo.confidence_band.score,
        confidence_calibration=memo.confidence_band.calibration,
        risk_band=memo.risk_band,
        worst_case=memo.worst_case,
        scenarios=memo.scenario_tree,
        decision_packet=memo.decision_packet,
        analyst_signals=memo.analyst_signals,
        risk_verdict=memo.risk_verdict,
        freshness_summary=memo.freshness_summary,
        provider_health=getattr(memo, "provider_health", None),
        replay_summary=getattr(memo, "replay_summary", None),
        degrade_reason=(trace or {}).get("degrade_reason"),
        trace=trace,
    )


def _thread_id(value: str | None) -> str:
    return value or f"thread:{uuid4()}"


def _v4_inputs_from_request(request: OrchestrateV4Request) -> list[V4InputItem]:
    if request.inputs:
        return request.inputs
    return [V4InputItem(type="text", content=request.query or "")]


@router.post("/orchestrate/v4", response_model=OrchestrateResponse)
async def orchestrate_agent_v4(
    request: OrchestrateV4Request,
    runtime: Annotated[V4GraphRuntime, Depends(get_v4_graph_runtime)],
) -> OrchestrateResponse:
    inputs = _v4_inputs_from_request(request)
    thread_id = _thread_id(request.thread_id)
    user_id = request.user_id or "anonymous"
    memo, trace = await runtime.execute(
        inputs=inputs,
        thread_id=thread_id,
        user_id=user_id,
        workspace_id=request.workspace_id,
        role_lens=request.role_lens,
        response_mode_hint=request.response_mode_hint,
        approval_response=request.approval_response,
    )
    return _response_from_memo(memo, trace)


@router.post("/orchestrate/v4/stream")
async def orchestrate_agent_stream_v4(
    request: OrchestrateV4Request,
    runtime: Annotated[V4GraphRuntime, Depends(get_v4_graph_runtime)],
) -> StreamingResponse:
    inputs = _v4_inputs_from_request(request)
    thread_id = _thread_id(request.thread_id)
    user_id = request.user_id or "anonymous"
    return StreamingResponse(
        runtime.stream(
            inputs=inputs,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=request.workspace_id,
            role_lens=request.role_lens,
            response_mode_hint=request.response_mode_hint,
            approval_response=request.approval_response,
        ),
        media_type="text/event-stream",
    )


# ---------------------------------------------------------------------------
# V5 Routes
# ---------------------------------------------------------------------------


class OrchestrateV5Request(BaseModel):
    """Request model for V5 orchestration."""
    query: str | None = None
    thread_id: str | None = None
    user_id: str | None = None
    workspace_id: str = "default"
    mode: str | None = None
    approval_response: dict | bool | str | None = None


class ResumeV5Request(BaseModel):
    """Request model for V5 resume."""
    thread_id: str
    approval_id: str
    approved: bool
    note: str | None = None


def _parse_mode(mode_str: str | None) -> V5Mode | None:
    """Parse mode string to V5Mode enum."""
    if not mode_str:
        return None
    try:
        return V5Mode(mode_str)
    except ValueError:
        return None


def _parse_approval_response(response: dict | bool | str | None) -> ApprovalDecision | None:
    """Parse approval response from various formats."""
    if not response:
        return None
    
    if isinstance(response, dict):
        try:
            return ApprovalDecision(**response)
        except Exception:
            return ApprovalDecision(
                approval_id=response.get("approval_id", ""),
                approved=response.get("approved", False),
                note=response.get("note"),
            )
    elif isinstance(response, bool):
        return ApprovalDecision(approval_id="", approved=response)
    return None


@router.post("/orchestrate/v5", response_model=OrchestrateResponse)
async def orchestrate_v5(
    request: OrchestrateV5Request,
    runtime: Annotated[V5GraphRuntime, Depends(get_v5_graph_runtime)],
) -> OrchestrateResponse:
    """Execute V5 graph synchronously."""
    thread_id = _thread_id(request.thread_id)
    user_id = request.user_id or "anonymous"
    mode = _parse_mode(request.mode)
    approval_response = _parse_approval_response(request.approval_response)
    
    try:
        packet, trace = await runtime.execute(
            query=request.query or "",
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=request.workspace_id,
            mode=mode,
            approval_response=approval_response,
        )
        
        return OrchestrateResponse(
            status="completed",
            thread_id=thread_id,
            run_id=trace.get("run_id"),
            approval_requests=trace.get("approval_requests", []),
            intent="research",
            role="pm",
            decision=packet.action,
            summary=packet.thesis,
            recommendation=packet.thesis,
            key_findings=[],
            historical_context=[],
            portfolio_impact=[],
            recommended_actions=[packet.action] if packet.action else [],
            watch_items=[],
            data_quality=[],
            evidence_blocks=[],
            specialist_views=trace.get("specialist_signals", []),
            confidence_score=packet.confidence,
            confidence_calibration="high" if packet.confidence > 0.7 else "medium",
            risk_band="low" if packet.action in ["buy", "sell"] else "medium",
            worst_case=packet.thesis[:100] if packet.thesis else "",
            scenarios=[],
            decision_packet=packet.model_dump(),
            trace=trace,
        )
    except TimeoutError as e:
        return OrchestrateResponse(
            status="timeout",
            thread_id=thread_id,
            recommendation=str(e),
            confidence_score=0.0,
            confidence_calibration="unknown",
            risk_band="unknown",
            worst_case=str(e),
            scenarios=[],
        )


@router.post("/orchestrate/v5/stream")
async def orchestrate_v5_stream(
    request: OrchestrateV5Request,
    runtime: Annotated[V5GraphRuntime, Depends(get_v5_graph_runtime)],
) -> StreamingResponse:
    """Execute V5 graph with SSE streaming."""
    thread_id = _thread_id(request.thread_id)
    user_id = request.user_id or "anonymous"
    mode = _parse_mode(request.mode)
    approval_response = _parse_approval_response(request.approval_response)
    
    return StreamingResponse(
        runtime.stream(
            query=request.query or "",
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=request.workspace_id,
            mode=mode,
            approval_response=approval_response,
        ),
        media_type="text/event-stream",
    )


@router.post("/orchestrate/v5/resume")
async def resume_v5(
    request: ResumeV5Request,
    runtime: Annotated[V5GraphRuntime, Depends(get_v5_graph_runtime)],
) -> OrchestrateResponse:
    """Resume V5 graph from an approval decision."""
    approval_response = ApprovalDecision(
        approval_id=request.approval_id,
        approved=request.approved,
        note=request.note,
    )
    
    try:
        packet, trace = await runtime.resume(
            thread_id=request.thread_id,
            approval_response=approval_response,
        )
        
        return OrchestrateResponse(
            status="completed",
            thread_id=request.thread_id,
            run_id=trace.get("run_id"),
            approval_requests=trace.get("approval_requests", []),
            intent="research",
            role="pm",
            decision=packet.action,
            summary=packet.thesis,
            recommendation=packet.thesis,
            key_findings=[],
            historical_context=[],
            portfolio_impact=[],
            recommended_actions=[packet.action] if packet.action else [],
            watch_items=[],
            data_quality=[],
            evidence_blocks=[],
            specialist_views=trace.get("specialist_signals", []),
            confidence_score=packet.confidence,
            confidence_calibration="high" if packet.confidence > 0.7 else "medium",
            risk_band="low" if packet.action in ["buy", "sell"] else "medium",
            worst_case=packet.thesis[:100] if packet.thesis else "",
            scenarios=[],
            decision_packet=packet.model_dump(),
            trace=trace,
        )
    except TimeoutError as e:
        return OrchestrateResponse(
            status="timeout",
            thread_id=request.thread_id,
            recommendation=str(e),
            confidence_score=0.0,
            confidence_calibration="unknown",
            risk_band="unknown",
            worst_case=str(e),
            scenarios=[],
        )


@router.get("/orchestrate/v5/thread/{thread_id}")
async def get_v5_thread(
    thread_id: str,
    runtime: Annotated[V5GraphRuntime, Depends(get_v5_graph_runtime)],
) -> dict:
    """Get V5 thread state for reconnection/hydration."""
    state = await runtime.get_thread_state(thread_id)
    
    if state is None:
        return {"error": "Thread not found", "thread_id": thread_id}
    
    return state
