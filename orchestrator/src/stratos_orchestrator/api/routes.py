"""Orchestrator API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from stratos_orchestrator.api.deps import (
    get_langchain_agent_runtime,
    get_orchestrate_use_case,
    get_stream_orchestrate_use_case,
    get_v2_orchestrate_use_case,
    get_v2_stream_orchestrate_use_case,
)
from stratos_orchestrator.application import LangChainAgentRuntime, OrchestrateUseCase, V2OrchestrateUseCase, V2StreamOrchestrateUseCase
from stratos_orchestrator.application.stream_orchestrate import StreamOrchestrateUseCase


router = APIRouter(tags=["Agent"])


class OrchestrateRequest(BaseModel):
    query: str
    thread_id: str | None = None
    user_id: str | None = None


class OrchestrateResponse(BaseModel):
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
    confidence_score: float
    confidence_calibration: str
    risk_band: str
    worst_case: str
    scenarios: list[dict]
    trace: dict | None = None  # Optional execution trace


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
