"""STRATOS v4 LangGraph runtime with strict state and bounded execution."""

from __future__ import annotations

import asyncio
import json
import re
import time
from dataclasses import replace
from functools import lru_cache
from typing import Any
from uuid import uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.types import Command, interrupt
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import Literal, TypedDict
from urllib.parse import urlparse

from stratos_orchestrator.adapters.tools.registry import ToolRegistry
from stratos_orchestrator.application.finance_council import FinanceCouncilRuntime
from stratos_orchestrator.application.persistence import SqliteCheckpointSaver, SqliteRunCoordinator, SqliteStore
from stratos_orchestrator.application.langchain_v3 import LangChainAgentRuntime, _classify_intent, _classify_role
from stratos_orchestrator.config import Settings
from stratos_orchestrator.domain.entities import AgentTask, ConfidenceBand, StrategicMemo, TaskStatus


AUTHORITY_SCORES = {"A0": 1.0, "A1": 0.92, "A2": 0.74, "A3": 0.45, "A4": 0.22}
DIRECT_MODES = {"exact_direct", "grounded_direct"}
HEAVY_RESPONSE_MODES = {"memo", "presentation"}


class V4InputItem(BaseModel):
    type: Literal["text", "image", "pdf", "spreadsheet", "file_ref"] = "text"
    content: str | None = None
    name: str | None = None
    uri: str | None = None


class ThreadRefs(BaseModel):
    assistant_id: str
    thread_id: str
    run_id: str
    workspace_id: str
    user_id: str


class EvidenceItem(BaseModel):
    evidence_id: str
    title: str
    detail: str
    source_type: str
    authority_grade: Literal["A0", "A1", "A2", "A3", "A4"]
    source_url: str | None = None
    domain: str | None = None
    freshness_ok: bool = True
    supporting_claim_ids: list[str] = Field(default_factory=list)


class ToolBudgetState(BaseModel):
    max_tool_budget: int = 6
    tools_used: int = 0
    max_external_calls: int = 1
    external_calls_used: int = 0
    max_retrieval_rounds: int = 1
    retrieval_rounds_used: int = 0
    max_specialist_count: int = 1
    specialists_used: int = 0
    max_token_budget: int = 1200


class ConfidenceLedger(BaseModel):
    routing_confidence: float = 0.0
    freshness_confidence: float = 0.0
    retrieval_confidence: float = 0.0
    grounding_confidence: float = 0.0
    conflict_confidence: float = 0.0
    answer_confidence: float = 0.0


class RetrievalPlan(BaseModel):
    mode: Literal["none", "web_search", "evidence"]
    query: str
    corpus: str | None = None
    top_k: int = 0
    citation_required: bool = False
    max_rounds: int = 0
    diversity_target: int = 1


class RetrievalJudgeResult(BaseModel):
    passed: bool
    relevance: float
    authority: float
    freshness: float
    source_diversity: float
    grounding_sufficiency: float
    reason: str


class ConflictMarker(BaseModel):
    severity: Literal["low", "medium", "high"]
    detail: str


class ClaimRecord(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: Literal["fact", "inference", "recommendation", "warning"]
    required_support_level: Literal["direct", "supported", "strong"]
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    support_strength: float = 0.0
    authority_grade: Literal["A0", "A1", "A2", "A3", "A4"] = "A4"
    freshness_ok: bool = False
    audit_status: Literal["accepted", "softened", "rejected"] = "rejected"


class RenderContract(BaseModel):
    answer_mode: Literal[
        "exact_direct",
        "grounded_direct",
        "decision_with_limits",
        "research_with_citations",
        "memo",
        "presentation",
        "insufficient_evidence",
    ] = "grounded_direct"
    detail_level: Literal["short", "standard", "deep"] = "standard"
    citation_mode: Literal["none", "inline", "evidence_block"] = "none"
    structure_mode: Literal["freeform", "semi_structured", "fully_structured"] = "freeform"


class TerminationRecord(BaseModel):
    stop: bool = False
    reason: str = ""
    path: str = ""


class ExecutionPolicy(BaseModel):
    success_condition: str
    early_stop_condition: str
    degrade_condition: str
    max_specialist_count: int
    max_external_calls: int
    max_retrieval_rounds: int
    allowed_tools: list[str]
    confidence_target: float
    planned_specialists: list[str]


class ApprovalRequest(BaseModel):
    approval_id: str
    reason: str
    required: bool = False


class ApprovalDecision(BaseModel):
    approval_id: str | None = None
    approved: bool
    notes: str | None = None


class SpecialistResult(BaseModel):
    specialist: str
    summary: str
    claims: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    verdict: str | None = None


class PackagedOutput(BaseModel):
    thread_refs: ThreadRefs
    decision: str
    summary: str
    recommendation: str
    answer_mode: str
    termination_reason: str
    degrade_reason: str | None = None
    evidence_blocks: list[dict[str, str]]
    specialist_views: list[dict[str, Any]] = Field(default_factory=list)
    trace: dict[str, Any]


class ResolvedEntities(BaseModel):
    company_ticker: str | None = None
    market_ticker: str | None = None
    country_codes: list[str] = Field(default_factory=list)
    event_scope: str | None = None
    confidence: float = 0.0


class V4State(TypedDict, total=False):
    input_envelope: dict[str, Any]
    facts_internal: dict[str, Any]
    facts_external: dict[str, Any]
    evidence_items: list[dict[str, Any]]
    freshness_map: dict[str, Any]
    retrieval_decisions: dict[str, Any]
    tool_budget: dict[str, Any]
    confidence_ledger: dict[str, float]
    conflict_markers: list[dict[str, Any]]
    approval_requests: list[dict[str, Any]]
    render_contract: dict[str, Any]
    claim_set: list[dict[str, Any]]
    claim_support_index: dict[str, list[str]]
    source_authority_map: dict[str, str]
    termination_record: dict[str, Any]
    degrade_reason: str | None
    thread_refs: dict[str, Any]
    execution_policy: dict[str, Any]
    specialist_outputs: dict[str, Any]
    output_package: dict[str, Any]


class V4GraphRuntime:
    """Strict LangGraph runtime for STRATOS v4."""

    def __init__(
        self,
        *,
        settings: Settings,
        tools: ToolRegistry,
        general_runtime: LangChainAgentRuntime | None = None,
    ) -> None:
        self._settings = settings
        self._tools = tools
        self._general_runtime = general_runtime
        self._finance_council = FinanceCouncilRuntime(tools, settings=settings)
        persistence_dir = settings.runtime_state_dir
        self._checkpointer = SqliteCheckpointSaver(persistence_dir / "langgraph_checkpoints.sqlite3")
        self._store = SqliteStore(persistence_dir / "langgraph_store.sqlite3")
        self._run_coordinator = SqliteRunCoordinator(persistence_dir / "runtime_control.sqlite3")
        self._graph = None
        self._specialist_graphs: dict[str, Any] = {}
        self._resolver_model: BaseChatModel | None = None

    async def execute(
        self,
        *,
        inputs: list[V4InputItem],
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str | None = None,
        response_mode_hint: str | None = None,
        approval_response: dict[str, Any] | bool | str | None = None,
    ) -> tuple[StrategicMemo, dict[str, Any]]:
        query = self._text_query(inputs)
        resolved_role = role_lens or _classify_role(query)
        delegate_to_general = self._should_delegate_to_general_runtime(query=query, role_lens=resolved_role)
        if delegate_to_general:
            return await self._execute_with_general_runtime(
                query=query,
                thread_id=thread_id,
                user_id=user_id,
                workspace_id=workspace_id,
                role_lens=resolved_role,
            )
        finance_role = (role_lens or "").lower() in {"pm", "cfa"} or (
            role_lens is None and resolved_role.lower() in {"pm", "cfa"} and not delegate_to_general
        )
        if finance_role:
            return await self._finance_council.execute(
                query=query,
                role_lens=resolved_role,
                workspace_id=workspace_id,
            )
        if approval_response is None:
            await self._reset_thread_state(thread_id)
        initial_state = self._build_initial_state(
            inputs=inputs,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            role_lens=role_lens,
            response_mode_hint=response_mode_hint,
        )
        refs = ThreadRefs.model_validate(initial_state["thread_refs"])
        final_status = "failed"
        await self._register_run(refs)
        try:
            graph = await self._ensure_graph()
            final_state = await asyncio.wait_for(
                graph.ainvoke(
                    self._graph_input(initial_state, approval_response),
                    config={"configurable": {"thread_id": thread_id}},
                ),
                timeout=45,
            )
            final_status = "interrupted" if "__interrupt__" in final_state else "completed"
        finally:
            await self._release_run(refs, status=final_status)

        if "__interrupt__" in final_state:
            return self._interrupted_result(initial_state, final_state["__interrupt__"])
        package = PackagedOutput.model_validate(final_state["output_package"])
        memo = self._memo_from_state(final_state, package)
        return memo, package.trace

    async def stream(
        self,
        *,
        inputs: list[V4InputItem],
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str | None = None,
        response_mode_hint: str | None = None,
        approval_response: dict[str, Any] | bool | str | None = None,
    ):
        query = self._text_query(inputs)
        resolved_role = role_lens or _classify_role(query)
        delegate_to_general = self._should_delegate_to_general_runtime(query=query, role_lens=resolved_role)
        if delegate_to_general:
            async for event_type, payload in self._stream_with_general_runtime(
                query=query,
                thread_id=thread_id,
                user_id=user_id,
                workspace_id=workspace_id,
                role_lens=resolved_role,
            ):
                yield self._event(event_type, payload)
            return
        finance_role = (role_lens or "").lower() in {"pm", "cfa"} or (
            role_lens is None and resolved_role.lower() in {"pm", "cfa"} and not delegate_to_general
        )
        if finance_role:
            async for event_type, payload in self._finance_council.stream(
                query=query,
                role_lens=resolved_role,
                workspace_id=workspace_id,
            ):
                yield self._event(event_type, payload)
            return
        if approval_response is None:
            await self._reset_thread_state(thread_id)
        initial_state = self._build_initial_state(
            inputs=inputs,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            role_lens=role_lens,
            response_mode_hint=response_mode_hint,
        )
        refs = ThreadRefs.model_validate(initial_state["thread_refs"])
        yield self._event("status", "Initializing STRATOS v4 graph runtime...")
        yield self._event(
            "context",
            {
                "thread_id": refs.thread_id,
                "run_id": refs.run_id,
                "workspace_id": refs.workspace_id,
                "intent": initial_state["input_envelope"]["intent"],
                "role_lens": initial_state["input_envelope"]["role_lens"],
                "response_mode_hint": initial_state["input_envelope"].get("response_mode_hint"),
            },
        )
        final_status = "failed"
        await self._register_run(refs)
        try:
            graph = await self._ensure_graph()
            final_state = None
            async for event in graph.astream_events(
                self._graph_input(initial_state, approval_response),
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
            ):
                emitted = self._stream_event_from_graph_event(event, refs)
                if emitted is not None:
                    yield emitted
                if event["event"] == "on_chain_stream" and event.get("name") == "LangGraph":
                    chunk = event["data"].get("chunk", {})
                    interrupts = list(chunk.get("__interrupt__", ()))
                    if interrupts:
                        yield self._event(
                            "approval_required",
                            {
                                "thread_id": refs.thread_id,
                                "run_id": refs.run_id,
                                "approval_requests": self._interrupt_payloads(interrupts),
                                "status": "interrupted",
                            },
                        )
                if event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                    final_state = event["data"]["output"]
            final_status = "interrupted" if final_state is not None and "__interrupt__" in final_state else "completed"
        finally:
            await self._release_run(refs, status=final_status)

        if final_state is None or "__interrupt__" in final_state:
            return
        package = PackagedOutput.model_validate(final_state["output_package"])
        memo = self._memo_from_state(final_state, package)
        yield self._event(
            "final_output",
            {
                "thread_id": refs.thread_id,
                "run_id": refs.run_id,
                "intent": final_state["input_envelope"]["intent"],
                "role": final_state["input_envelope"]["role_lens"],
                "decision": package.decision,
                "summary": package.summary,
                "recommendation": package.recommendation,
                "confidence_score": final_state["confidence_ledger"]["answer_confidence"],
                "confidence_calibration": ConfidenceBand.from_score(final_state["confidence_ledger"]["answer_confidence"]).calibration,
                "risk_band": "Low" if package.answer_mode in DIRECT_MODES else "Medium",
                "worst_case": final_state.get("degrade_reason") or "Evidence quality may limit the answer.",
                "evidence_blocks": package.evidence_blocks,
                "key_findings": memo.key_findings,
                "historical_context": memo.historical_context,
                "portfolio_impact": memo.portfolio_impact,
                "recommended_actions": memo.recommended_actions,
                "watch_items": memo.watch_items,
                "specialist_views": memo.specialist_views,
                "trace": package.trace,
                "data_quality": self._data_quality(final_state),
            },
        )

    async def _ensure_graph(self):
        if self._graph is not None:
            return self._graph
        workflow = StateGraph(V4State)
        for node_name, handler in (
            ("intake_router", self._intake_router),
            ("context_builder", self._context_builder),
            ("freshness_adjudicator", self._freshness_adjudicator),
            ("execution_planner", self._execution_planner),
            ("sufficiency_gate_1", self._sufficiency_gate_1),
            ("retrieval_gate", self._retrieval_gate),
            ("retrieval_planner", self._retrieval_planner),
            ("retriever", self._retriever),
            ("reranker", self._reranker),
            ("retrieval_judge", self._retrieval_judge),
            ("sufficiency_gate_2", self._sufficiency_gate_2),
            ("specialist_admission_gate", self._specialist_admission_gate),
            ("macro_subgraph", self._macro_subgraph),
            ("portfolio_subgraph", self._portfolio_subgraph),
            ("events_subgraph", self._events_subgraph),
            ("research_subgraph", self._research_subgraph),
            ("risk_subgraph", self._risk_subgraph),
            ("conflict_resolver", self._conflict_resolver),
            ("claim_auditor", self._claim_auditor),
            ("response_controller", self._response_controller),
            ("approval_gate", self._approval_gate),
            ("renderer", self._renderer),
            ("output_packager", self._output_packager),
        ):
            workflow.add_node(node_name, handler)

        workflow.add_edge(START, "intake_router")
        workflow.add_edge("intake_router", "context_builder")
        workflow.add_edge("context_builder", "freshness_adjudicator")
        workflow.add_edge("freshness_adjudicator", "execution_planner")
        workflow.add_edge("execution_planner", "sufficiency_gate_1")
        workflow.add_conditional_edges(
            "sufficiency_gate_1",
            self._after_sufficiency_gate_1,
            {"retrieval_gate": "retrieval_gate", "claim_auditor": "claim_auditor"},
        )
        workflow.add_conditional_edges(
            "retrieval_gate",
            self._after_retrieval_gate,
            {
                "claim_auditor": "claim_auditor",
                "retrieval_planner": "retrieval_planner",
                "specialist_admission_gate": "specialist_admission_gate",
            },
        )
        workflow.add_edge("retrieval_planner", "retriever")
        workflow.add_edge("retriever", "reranker")
        workflow.add_edge("reranker", "retrieval_judge")
        workflow.add_edge("retrieval_judge", "sufficiency_gate_2")
        workflow.add_conditional_edges(
            "sufficiency_gate_2",
            self._after_sufficiency_gate_2,
            {"claim_auditor": "claim_auditor", "specialist_admission_gate": "specialist_admission_gate"},
        )
        workflow.add_conditional_edges(
            "specialist_admission_gate",
            self._after_specialist_gate,
            {"claim_auditor": "claim_auditor", "macro_subgraph": "macro_subgraph"},
        )
        workflow.add_edge("macro_subgraph", "portfolio_subgraph")
        workflow.add_edge("portfolio_subgraph", "events_subgraph")
        workflow.add_edge("events_subgraph", "research_subgraph")
        workflow.add_edge("research_subgraph", "risk_subgraph")
        workflow.add_edge("risk_subgraph", "conflict_resolver")
        workflow.add_edge("conflict_resolver", "claim_auditor")
        workflow.add_edge("claim_auditor", "response_controller")
        workflow.add_edge("response_controller", "approval_gate")
        workflow.add_edge("approval_gate", "renderer")
        workflow.add_edge("renderer", "output_packager")
        workflow.add_edge("output_packager", END)

        self._graph = workflow.compile(checkpointer=self._checkpointer, store=self._store)
        return self._graph

    def _build_initial_state(
        self,
        *,
        inputs: list[V4InputItem],
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str | None,
        response_mode_hint: str | None,
    ) -> V4State:
        text_query = self._text_query(inputs)
        inferred_role = role_lens or _classify_role(text_query)
        refs = ThreadRefs(
            assistant_id="stratos-v4",
            thread_id=thread_id,
            run_id=f"run:{uuid4()}",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        return {
            "input_envelope": {
                "query": text_query,
                "inputs": [item.model_dump() for item in inputs],
                "intent": _classify_intent(text_query),
                "role_lens": inferred_role,
                "response_mode_hint": response_mode_hint,
                "ui_mode": "command",
                "portfolio_dependency": any(token in text_query.lower() for token in ("portfolio", "book", "exposure", "holding", "position", "rebalance")),
            },
            "facts_internal": {},
            "facts_external": {},
            "evidence_items": [],
            "freshness_map": {},
            "retrieval_decisions": {},
            "tool_budget": ToolBudgetState().model_dump(),
            "confidence_ledger": ConfidenceLedger(routing_confidence=0.82, answer_confidence=0.25).model_dump(),
            "conflict_markers": [],
            "approval_requests": [],
            "render_contract": RenderContract().model_dump(),
            "claim_set": [],
            "claim_support_index": {},
            "source_authority_map": {},
            "termination_record": TerminationRecord().model_dump(),
            "degrade_reason": None,
            "thread_refs": refs.model_dump(),
            "execution_policy": {},
            "specialist_outputs": {},
            "output_package": {},
        }

    @staticmethod
    def _graph_input(initial_state: V4State, approval_response: dict[str, Any] | bool | str | None) -> V4State | Command:
        if approval_response is None:
            return initial_state
        return Command(
            update={"thread_refs": initial_state["thread_refs"]},
            resume=approval_response,
        )

    def _interrupted_result(self, initial_state: V4State, interrupts: list[Any]) -> tuple[StrategicMemo, dict[str, Any]]:
        refs = ThreadRefs.model_validate(initial_state["thread_refs"])
        requests = self._interrupt_payloads(interrupts)
        memo = StrategicMemo(
            query=initial_state["input_envelope"]["query"],
            plan_summary="Execution paused pending explicit approval.",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(0.0),
            risk_policy_status="PENDING_APPROVAL",
            recommendation="Resume this thread with an approval decision to continue execution.",
            worst_case="No final output was produced because the graph is paused.",
            risk_band="approval_pending",
            intent=initial_state["input_envelope"]["intent"],
            role=initial_state["input_envelope"]["role_lens"],
            decision="Approval required before completion.",
            summary="The run paused at an approval gate and is waiting for a resume command.",
            data_quality=["Execution checkpoint persisted and waiting on human input."],
        )
        trace = {
            "status": "interrupted",
            "path": "approval_gate",
            "thread_refs": refs.model_dump(),
            "approval_requests": requests,
        }
        return memo, trace

    async def _execute_with_general_runtime(
        self,
        *,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str,
    ) -> tuple[StrategicMemo, dict[str, Any]]:
        if self._general_runtime is None:
            raise RuntimeError("General runtime is not configured.")
        memo = await self._general_runtime.execute(query, thread_id=thread_id, user_id=user_id)
        normalized_memo = replace(
            memo,
            intent=_classify_intent(query),
            role=role_lens or memo.role,
        )
        return normalized_memo, self._general_trace(
            memo=normalized_memo,
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            role_lens=role_lens,
        )

    async def _stream_with_general_runtime(
        self,
        *,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str,
    ):
        if self._general_runtime is None:
            raise RuntimeError("General runtime is not configured.")

        async for raw in self._general_runtime.stream(query, thread_id=thread_id, user_id=user_id):
            if not isinstance(raw, str) or not raw.startswith("event: "):
                continue
            lines = raw.strip().splitlines()
            if len(lines) < 2 or not lines[1].startswith("data: "):
                continue
            event_type = lines[0].removeprefix("event: ").strip()
            try:
                payload = json.loads(lines[1].removeprefix("data: ").strip())
            except json.JSONDecodeError:
                continue
            mapped = self._map_general_runtime_event(
                event_type=event_type,
                payload=payload,
                query=query,
                thread_id=thread_id,
                user_id=user_id,
                workspace_id=workspace_id,
                role_lens=role_lens,
            )
            if mapped is not None:
                yield mapped

    @staticmethod
    def _interrupt_payloads(interrupts: list[Any]) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for item in interrupts:
            value = getattr(item, "value", item)
            if isinstance(value, dict):
                payloads.append(value)
        return payloads

    def _should_delegate_to_general_runtime(self, *, query: str, role_lens: str | None) -> bool:
        if self._general_runtime is None:
            return False
        normalized_role = (role_lens or _classify_role(query)).lower()
        lowered = query.strip().lower()
        if normalized_role not in {"pm", "cfa"}:
            return True
        if self._is_conversational_query(query):
            return True
        if _classify_intent(query) == "docs":
            return True
        return any(token in lowered for token in ("langchain", "langgraph", "rag", "mcp", "tool calling"))

    def _general_trace(
        self,
        *,
        memo: StrategicMemo,
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str,
    ) -> dict[str, Any]:
        thread_refs = ThreadRefs(
            assistant_id="stratos-v4",
            thread_id=thread_id,
            run_id=f"run:{uuid4()}",
            workspace_id=workspace_id,
            user_id=user_id,
        )
        return {
            "status": "completed",
            "path": "langchain_v3_delegate",
            "answer_mode": "grounded_direct" if memo.risk_band == "Low" else "decision_with_limits",
            "degrade_reason": None,
            "conflicts": [],
            "claims": [],
            "retrieval": {"mode": "agentic_auto"},
            "specialists": {},
            "thread_refs": thread_refs.model_dump(),
            "delegate_runtime": "langchain_v3",
            "intent": _classify_intent(query),
            "role": role_lens,
        }

    def _map_general_runtime_event(
        self,
        *,
        event_type: str,
        payload: dict[str, Any],
        query: str,
        thread_id: str,
        user_id: str,
        workspace_id: str,
        role_lens: str,
    ) -> tuple[str, dict[str, Any]] | None:
        if event_type == "status":
            return "status", payload
        if event_type == "context":
            return (
                "context",
                {
                    "thread_id": thread_id,
                    "workspace_id": workspace_id,
                    "intent": payload.get("intent", _classify_intent(query)),
                    "role_lens": role_lens,
                    "response_mode_hint": "direct",
                    "engine": "langchain_v3",
                },
            )
        if event_type == "strategy":
            return (
                "strategy",
                {
                    **payload,
                    "engine": "langchain_v3",
                    "role_lens": role_lens,
                },
            )
        if event_type == "task_result":
            return "task_result", payload
        if event_type != "final_memo":
            return None
        memo = StrategicMemo(
            query=query,
            plan_summary="LangChain runtime delegated the response.",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(float(payload.get("confidence_score", 0.4))),
            risk_policy_status="PASS",
            recommendation=str(payload.get("recommendation", "")),
            worst_case=str(payload.get("worst_case", "")),
            risk_band=str(payload.get("risk_band", "Medium")),
            intent=str(payload.get("intent", _classify_intent(query))),
            role=role_lens or str(payload.get("role", _classify_role(query))),
            decision=str(payload.get("decision", "")),
            summary=str(payload.get("summary", "")),
            key_findings=list(payload.get("key_findings", [])),
            historical_context=list(payload.get("historical_context", [])),
            portfolio_impact=list(payload.get("portfolio_impact", [])),
            recommended_actions=list(payload.get("recommended_actions", [])),
            watch_items=list(payload.get("watch_items", [])),
            data_quality=list(payload.get("data_quality", [])),
            evidence_blocks=list(payload.get("evidence_blocks", [])),
            specialist_views=[],
            scenario_tree=list(payload.get("scenario_tree", [])),
        )
        trace = self._general_trace(
            memo=memo,
            query=query,
            thread_id=thread_id,
            user_id=user_id,
            workspace_id=workspace_id,
            role_lens=role_lens,
        )
        return (
            "final_output",
            {
                "thread_id": trace["thread_refs"]["thread_id"],
                "run_id": trace["thread_refs"]["run_id"],
                "intent": memo.intent,
                "role": memo.role,
                "decision": memo.decision,
                "summary": memo.summary,
                "recommendation": memo.recommendation,
                "confidence_score": memo.confidence_band.score,
                "confidence_calibration": memo.confidence_band.calibration,
                "risk_band": memo.risk_band,
                "worst_case": memo.worst_case,
                "evidence_blocks": memo.evidence_blocks,
                "key_findings": memo.key_findings,
                "historical_context": memo.historical_context,
                "portfolio_impact": memo.portfolio_impact,
                "recommended_actions": memo.recommended_actions,
                "watch_items": memo.watch_items,
                "specialist_views": memo.specialist_views,
                "trace": trace,
                "data_quality": memo.data_quality,
            },
        )

    async def _register_run(self, refs: ThreadRefs) -> None:
        self._run_coordinator.acquire_run(
            assistant_id=refs.assistant_id,
            thread_id=refs.thread_id,
            run_id=refs.run_id,
            workspace_id=refs.workspace_id,
            user_id=refs.user_id,
            max_runs_per_workspace=4,
            max_runs_per_thread=1,
        )

    async def _release_run(self, refs: ThreadRefs, *, status: str) -> None:
        self._run_coordinator.complete_run(
            thread_id=refs.thread_id,
            run_id=refs.run_id,
            status=status,
        )

    async def _reset_thread_state(self, thread_id: str) -> None:
        await self._checkpointer.adelete_thread(thread_id)

    async def _intake_router(self, state: V4State) -> dict[str, Any]:
        query = state["input_envelope"]["query"]
        lowered = query.lower()
        multimodal = [item["type"] for item in state["input_envelope"]["inputs"] if item["type"] != "text"]
        response_hint = state["input_envelope"].get("response_mode_hint")
        resolved = await self._resolve_query_entities(query)
        return {
            "input_envelope": {
                **state["input_envelope"],
                "multimodal_types": multimodal,
                "freshness_sensitive": any(token in lowered for token in ("latest", "today", "current", "breaking", "changed")),
                "complexity": "high" if len(query.split()) > 14 else "standard",
                "needs_clarification": self._needs_clarification(query),
                "response_mode_hint": response_hint,
                "resolved_entities": resolved.model_dump(),
                "portfolio_dependency": state["input_envelope"]["portfolio_dependency"],
            },
            "confidence_ledger": {
                **state["confidence_ledger"],
                "routing_confidence": max(0.6, resolved.confidence or (0.9 if not multimodal else 0.78)),
            },
        }

    async def _context_builder(self, state: V4State) -> dict[str, Any]:
        query = state["input_envelope"]["query"]
        facts_internal = dict(state["facts_internal"])
        source_authority = dict(state["source_authority_map"])
        tool_tasks: list[tuple[str, dict[str, Any], str]] = []
        lowered = query.lower()
        resolved = ResolvedEntities.model_validate(state["input_envelope"].get("resolved_entities", {}))
        macro_country_focus = bool(resolved.country_codes) or any(
            token in lowered for token in ("macro", "inflation", "rates", "oil", "liquidity", "world", "sovereign", "debt", "fiscal", "currency", "fx", "pressure")
        )
        company_focus = self._should_run_company_analysis(query=query, resolved=resolved)

        if state["input_envelope"]["portfolio_dependency"] and self._tools.has_tool("portfolio_analyze"):
            tool_tasks.append(("portfolio_analyze", {"name": "primary"}, "portfolio"))
        if macro_country_focus and self._tools.has_tool("macro_analyze_world"):
            tool_tasks.append(("macro_analyze_world", {}, "world_state"))
        primary_country = resolved.country_codes[0] if resolved.country_codes else None
        if resolved.country_codes and self._tools.has_tool("macro_analyze_country"):
            for country_code in list(dict.fromkeys(resolved.country_codes))[:2]:
                tool_tasks.append(("macro_analyze_country", {"country_code": country_code, "include_world_state": True}, f"country:{country_code}"))
        if resolved.market_ticker and self._tools.has_tool("market_analyze"):
            tool_tasks.append(("market_analyze", {"ticker": resolved.market_ticker, "limit": 5}, f"market:{resolved.market_ticker}"))
        if company_focus and resolved.company_ticker and not resolved.market_ticker and self._tools.has_tool("company_analyze"):
            tool_tasks.append(("company_analyze", {"ticker": resolved.company_ticker}, f"company:{resolved.company_ticker}"))
        if (
            company_focus
            and resolved.company_ticker
            and any(token in lowered for token in ("news", "headline", "latest", "current", "event", "watch"))
            and self._tools.has_tool("company_news_analyze")
        ):
            tool_tasks.append(("company_news_analyze", {"ticker": resolved.company_ticker}, f"company_news:{resolved.company_ticker}"))
        if any(token in lowered for token in ("event", "pulse", "news")) and self._tools.has_tool("events_analyze"):
            event_scope = self._infer_event_scope(
                query=query,
                market_ticker=resolved.market_ticker,
                company_ticker=resolved.company_ticker,
                country_code=primary_country,
                resolved_scope=resolved.event_scope,
            )
            tool_tasks.append(("events_analyze", {"scope": event_scope, "query": query[:120]}, f"events:{event_scope}"))
        if any(token in lowered for token in ("regime", "risk sentiment", "sentiment")) and self._tools.has_tool("regime_detect"):
            tool_tasks.append(("regime_detect", {}, "regime"))
        if any(token in lowered for token in ("history", "regime", "analog", "anomaly")) and self._tools.has_tool("history_analyze"):
            if "regime" in lowered:
                tool_tasks.append(("history_analyze", {"entity_type": "market_regime", "entity_id": "global"}, "history:regime"))
            elif company_focus and resolved.company_ticker:
                tool_tasks.append(("history_analyze", {"entity_type": "company", "entity_id": resolved.company_ticker, "metric": "fraud_score"}, f"history:{resolved.company_ticker}"))
        if any(token in lowered for token in ("fed", "fomc", "rbi", "policy", "central bank", "regulation")) and self._tools.has_tool("policy_events_analyze"):
            policy_scope = "india" if primary_country == "IND" else "us" if primary_country == "USA" else "global"
            tool_tasks.append(("policy_events_analyze", {"scope": policy_scope, "query": query[:120]}, f"policy:{policy_scope}"))

        tool_budget = ToolBudgetState.model_validate(state["tool_budget"])
        tasks: list[AgentTask] = []
        requested_dimensions = sum(
            1
            for condition in (
                state["input_envelope"]["portfolio_dependency"],
                any(token in lowered for token in ("macro", "inflation", "rates", "oil", "liquidity", "world")),
                bool(primary_country),
                bool(resolved.company_ticker or resolved.market_ticker),
                any(token in lowered for token in ("event", "pulse", "news")),
                any(token in lowered for token in ("fed", "fomc", "rbi", "policy", "central bank", "regulation")),
                any(token in lowered for token in ("regime", "risk sentiment", "sentiment", "history", "analog", "anomaly")),
            )
            if condition
        )
        tool_cap = min(
            tool_budget.max_tool_budget,
            6 if requested_dimensions >= 4 else 5 if state["input_envelope"].get("complexity") == "high" or requested_dimensions >= 3 else 3,
        )
        for tool_name, arguments, bucket in tool_tasks[: max(1, tool_cap)]:
            task = AgentTask(tool_name=tool_name, arguments=arguments, status=TaskStatus.EXECUTING)
            try:
                result = await self._execute_tool(tool_name, arguments, state=state, external=False)
                task.result = result
                task.status = TaskStatus.COMPLETED
                facts_internal[bucket] = result
                source_authority[bucket] = "A0"
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
            tasks.append(task)

        memories = self._store.search(("v4-memory", state["thread_refs"]["workspace_id"], state["thread_refs"]["user_id"]), limit=3)
        memory_lines = [str(item.value.get("summary", "")) for item in memories if item.value]
        if memory_lines:
            facts_internal["memory_context"] = memory_lines
            source_authority["memory_context"] = "A3"

        has_substantive_facts = self._has_substantive_internal_facts(facts_internal)

        return {
            "facts_internal": facts_internal,
            "source_authority_map": source_authority,
            "tool_budget": {
                **tool_budget.model_dump(),
                "tools_used": tool_budget.tools_used + len(tasks),
            },
            "confidence_ledger": {
                **state["confidence_ledger"],
                "grounding_confidence": 0.82 if has_substantive_facts else state["confidence_ledger"]["grounding_confidence"],
            },
        }

    async def _freshness_adjudicator(self, state: V4State) -> dict[str, Any]:
        freshness_sensitive = state["input_envelope"]["freshness_sensitive"]
        facts_internal = state["facts_internal"]
        freshness_map = {
            "internal_truth_ready": self._has_substantive_internal_facts(facts_internal),
            "freshness_debt": freshness_sensitive and "memory_context" not in facts_internal,
            "web_check_authorized": freshness_sensitive,
        }
        return {
            "freshness_map": freshness_map,
            "confidence_ledger": {
                **state["confidence_ledger"],
                "freshness_confidence": 0.88 if not freshness_map["freshness_debt"] else 0.46,
            },
        }

    async def _execution_planner(self, state: V4State) -> dict[str, Any]:
        intent = state["input_envelope"]["intent"]
        query = state["input_envelope"]["query"].lower()
        specialists: list[str] = []
        if any(token in query for token in ("macro", "oil", "inflation", "rates", "btc", "regime", "history", "analog")):
            specialists.append("macro")
        if state["input_envelope"]["portfolio_dependency"]:
            specialists.append("portfolio")
            specialists.append("risk")
        if any(token in query for token in ("event", "news", "pulse", "fed", "fomc", "rbi", "headline")):
            specialists.append("events")
        if any(token in query for token in ("compare", "filing", "policy", "research", "quality", "history", "watch", "news", "headline")):
            specialists.append("research")
        if state["input_envelope"].get("response_mode_hint") in {"memo", "presentation"}:
            specialists.append("presentation")

        allowed_tools = ["web_search", "webpage_read"]
        for name in (
            "portfolio_analyze",
            "company_analyze",
            "company_news_analyze",
            "market_analyze",
            "macro_analyze_world",
            "macro_analyze_country",
            "events_analyze",
            "history_analyze",
            "regime_detect",
            "policy_analyze",
            "policy_events_analyze",
        ):
            if self._tools.has_tool(name):
                allowed_tools.append(name)

        policy = ExecutionPolicy(
            success_condition="Provide the shortest grounded answer that satisfies the user intent.",
            early_stop_condition="Stop when structured internal facts or one retrieval round are sufficient.",
            degrade_condition="Downgrade when retrieval, grounding, or conflict confidence remains below threshold.",
            max_specialist_count=min(3, len(set(specialists)) or 1),
            max_external_calls=1 if state["freshness_map"]["web_check_authorized"] else 0,
            max_retrieval_rounds=1,
            allowed_tools=allowed_tools,
            confidence_target=0.72 if intent in {"portfolio", "scenario"} else 0.6,
            planned_specialists=list(dict.fromkeys(specialists)),
        )
        budget = ToolBudgetState.model_validate(state["tool_budget"])
        budget.max_specialist_count = policy.max_specialist_count
        budget.max_external_calls = policy.max_external_calls
        budget.max_retrieval_rounds = policy.max_retrieval_rounds
        return {"execution_policy": policy.model_dump(), "tool_budget": budget.model_dump()}

    async def _sufficiency_gate_1(self, state: V4State) -> dict[str, Any]:
        enough = (
            self._has_substantive_internal_facts(state["facts_internal"])
            and not state["freshness_map"]["web_check_authorized"]
            and not self._requires_deeper_analysis(state)
        )
        if enough:
            termination = TerminationRecord(stop=True, reason="Internal structured truth was sufficient before retrieval.", path="sufficiency_gate_1")
            return {"termination_record": termination.model_dump()}
        return {}

    async def _retrieval_gate(self, state: V4State) -> dict[str, Any]:
        query = state["input_envelope"]["query"].lower()
        mode = "none"
        if state["freshness_map"]["web_check_authorized"] or any(token in query for token in ("news", "headline", "fed", "fomc", "rbi")):
            mode = "web_search"
        if any(token in query for token in ("filing", "policy", "research", "compare", "transcript")):
            mode = "evidence"
        return {
            "retrieval_decisions": {
                **state["retrieval_decisions"],
                "mode": mode,
            }
        }

    async def _retrieval_planner(self, state: V4State) -> dict[str, Any]:
        mode = state["retrieval_decisions"]["mode"]
        query = state["input_envelope"]["query"]
        citation_required = mode == "evidence" or state["input_envelope"].get("response_mode_hint") in {"research", "memo", "presentation"}
        corpus = None
        if "filing" in query.lower():
            corpus = "company_filings"
        elif "policy" in query.lower():
            corpus = "policy_docs"
        elif "event" in query.lower() or "news" in query.lower():
            corpus = "macro_events"
        plan = RetrievalPlan(
            mode=mode,
            query=query,
            corpus=corpus,
            top_k=3 if mode != "none" else 0,
            citation_required=citation_required,
            max_rounds=1 if mode != "none" else 0,
            diversity_target=2 if mode == "evidence" else 1,
        )
        return {"retrieval_decisions": {**state["retrieval_decisions"], "plan": plan.model_dump()}}

    async def _retriever(self, state: V4State) -> dict[str, Any]:
        plan = RetrievalPlan.model_validate(state["retrieval_decisions"]["plan"])
        if plan.mode == "none":
            return {}

        budget = ToolBudgetState.model_validate(state["tool_budget"])
        evidence_items = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        facts_external = dict(state["facts_external"])
        if budget.external_calls_used >= budget.max_external_calls and plan.mode == "web_search":
            return {"degrade_reason": "External freshness budget was exhausted before retrieval."}

        if plan.mode == "web_search":
            result = await self._execute_tool("web_search", {"query": plan.query, "limit": plan.top_k}, state=state, external=True)
            facts_external["web_search"] = result
            for index, item in enumerate(result.get("results", []), start=1):
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"web:{index}",
                        title=item.get("title", "Web result"),
                        detail=item.get("url", ""),
                        source_type="web_search",
                        authority_grade=self._authority_for_url(item.get("url")),
                        source_url=item.get("url"),
                        domain=urlparse(item.get("url", "")).netloc or None,
                    )
                )
        elif plan.mode == "evidence":
            search_result = await self._execute_tool("web_search", {"query": plan.query, "limit": plan.top_k}, state=state, external=True)
            facts_external["evidence_search"] = search_result
            for index, item in enumerate(search_result.get("results", []), start=1):
                try:
                    page = await self._execute_tool("webpage_read", {"url": item["url"], "max_chars": 2400}, state=state, external=True)
                except Exception:
                    page = {"url": item.get("url"), "title": item.get("title"), "content": item.get("title", "")}
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"evidence:{index}",
                        title=page.get("title") or item.get("title", "Evidence"),
                        detail=str(page.get("content", ""))[:500],
                        source_type="retrieved_document",
                        authority_grade=self._authority_for_url(page.get("url") or item.get("url")),
                        source_url=page.get("url") or item.get("url"),
                        domain=urlparse(page.get("url") or item.get("url", "")).netloc or None,
                    )
                )

        budget.external_calls_used += 1
        budget.retrieval_rounds_used += 1
        source_authority = dict(state["source_authority_map"])
        for item in evidence_items:
            source_authority[item.evidence_id] = item.authority_grade
        return {
            "facts_external": facts_external,
            "evidence_items": [item.model_dump() for item in evidence_items],
            "source_authority_map": source_authority,
            "tool_budget": budget.model_dump(),
        }

    async def _reranker(self, state: V4State) -> dict[str, Any]:
        evidence_items = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        ranked = sorted(
            evidence_items,
            key=lambda item: (AUTHORITY_SCORES[item.authority_grade], item.freshness_ok, len(item.detail)),
            reverse=True,
        )
        return {"evidence_items": [item.model_dump() for item in ranked]}

    async def _retrieval_judge(self, state: V4State) -> dict[str, Any]:
        evidence_items = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        if not evidence_items:
            result = RetrievalJudgeResult(
                passed=False,
                relevance=0.0,
                authority=0.0,
                freshness=0.0,
                source_diversity=0.0,
                grounding_sufficiency=0.0,
                reason="No evidence items were retrieved.",
            )
        else:
            domains = {item.domain or item.source_url or item.evidence_id for item in evidence_items}
            authority = sum(AUTHORITY_SCORES[item.authority_grade] for item in evidence_items[:3]) / min(len(evidence_items), 3)
            relevance = 0.72 if any(self._query_term_match(state["input_envelope"]["query"], item.title + " " + item.detail) for item in evidence_items[:3]) else 0.42
            freshness = 0.85 if state["retrieval_decisions"]["mode"] == "web_search" else 0.62
            diversity = min(1.0, len(domains) / max(1, RetrievalPlan.model_validate(state["retrieval_decisions"]["plan"]).diversity_target))
            grounding = round((authority + relevance + freshness + diversity) / 4, 2)
            result = RetrievalJudgeResult(
                passed=grounding >= 0.56,
                relevance=relevance,
                authority=authority,
                freshness=freshness,
                source_diversity=diversity,
                grounding_sufficiency=grounding,
                reason="Retrieval passed quality thresholds." if grounding >= 0.56 else "Retrieval quality was too weak for escalation.",
            )
        return {
            "retrieval_decisions": {**state["retrieval_decisions"], "judge": result.model_dump()},
            "confidence_ledger": {
                **state["confidence_ledger"],
                "retrieval_confidence": result.relevance,
                "grounding_confidence": result.grounding_sufficiency,
            },
        }

    async def _sufficiency_gate_2(self, state: V4State) -> dict[str, Any]:
        judge = RetrievalJudgeResult.model_validate(state["retrieval_decisions"].get("judge", {"passed": True, "relevance": 0.0, "authority": 0.0, "freshness": 0.0, "source_diversity": 0.0, "grounding_sufficiency": 0.0, "reason": ""}))
        simple_web = state["retrieval_decisions"].get("mode") == "web_search" and len(state["input_envelope"]["query"].split()) <= 10
        if judge.passed and simple_web:
            termination = TerminationRecord(stop=True, reason="Web search produced sufficient grounding for a direct answer.", path="sufficiency_gate_2")
            return {"termination_record": termination.model_dump()}
        if not judge.passed and state["retrieval_decisions"].get("mode") != "none":
            return {"degrade_reason": judge.reason}
        return {}

    async def _specialist_admission_gate(self, state: V4State) -> dict[str, Any]:
        judge = state["retrieval_decisions"].get("judge")
        policy = ExecutionPolicy.model_validate(state["execution_policy"])
        allow = True
        if judge and not judge["passed"] and state["input_envelope"]["freshness_sensitive"]:
            allow = False
        if not policy.planned_specialists:
            allow = False
        if not allow:
            termination = TerminationRecord(stop=True, reason="Specialist fan-out was not justified by evidence quality or plan.", path="specialist_admission_gate")
            return {"termination_record": termination.model_dump()}
        return {}

    async def _macro_subgraph(self, state: V4State) -> dict[str, Any]:
        return await self._run_specialist("macro", state)

    async def _portfolio_subgraph(self, state: V4State) -> dict[str, Any]:
        return await self._run_specialist("portfolio", state)

    async def _events_subgraph(self, state: V4State) -> dict[str, Any]:
        return await self._run_specialist("events", state)

    async def _research_subgraph(self, state: V4State) -> dict[str, Any]:
        return await self._run_specialist("research", state)

    async def _risk_subgraph(self, state: V4State) -> dict[str, Any]:
        return await self._run_specialist("risk", state)

    async def _conflict_resolver(self, state: V4State) -> dict[str, Any]:
        conflicts = [ConflictMarker.model_validate(item) for item in state["conflict_markers"]]
        if state["freshness_map"].get("freshness_debt") and state["facts_external"]:
            conflicts.append(ConflictMarker(severity="medium", detail="External freshness checks were needed because internal freshness was uncertain."))
        if state["degrade_reason"]:
            conflicts.append(ConflictMarker(severity="high", detail=state["degrade_reason"]))
        confidence = 0.88 if not conflicts else 0.42 if any(item.severity == "high" for item in conflicts) else 0.64
        return {
            "conflict_markers": [item.model_dump() for item in conflicts],
            "confidence_ledger": {**state["confidence_ledger"], "conflict_confidence": confidence},
        }

    async def _claim_auditor(self, state: V4State) -> dict[str, Any]:
        evidence_items = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        claims: list[ClaimRecord] = []
        support_index: dict[str, list[str]] = {}
        facts_internal = state["facts_internal"]
        if facts_internal:
            claims.append(
                ClaimRecord(
                    claim_id="claim:internal",
                    claim_text="STRATOS internal state was used as the primary source of truth for this answer.",
                    claim_type="fact",
                    required_support_level="direct",
                    supporting_evidence_ids=[],
                    support_strength=1.0,
                    authority_grade="A0",
                    freshness_ok=not state["freshness_map"].get("freshness_debt", False),
                    audit_status="accepted",
                )
            )
            support_index["claim:internal"] = []
        if evidence_items:
            primary = evidence_items[0]
            status: Literal["accepted", "softened"] = "accepted" if AUTHORITY_SCORES[primary.authority_grade] >= 0.74 else "softened"
            claims.append(
                ClaimRecord(
                    claim_id="claim:evidence",
                    claim_text=f"External evidence was used to ground the answer using {len(evidence_items)} source(s).",
                    claim_type="inference",
                    required_support_level="supported",
                    supporting_evidence_ids=[item.evidence_id for item in evidence_items[:2]],
                    support_strength=min(1.0, len(evidence_items) / 2),
                    authority_grade=primary.authority_grade,
                    freshness_ok=all(item.freshness_ok for item in evidence_items[:2]),
                    audit_status=status,
                )
            )
            support_index["claim:evidence"] = [item.evidence_id for item in evidence_items[:2]]
        watch_items = self._build_watch_items(state)
        for index, item in enumerate(watch_items[:4], start=1):
            claims.append(
                ClaimRecord(
                    claim_id=f"claim:watch:{index}",
                    claim_text=item,
                    claim_type="inference",
                    required_support_level="supported",
                    supporting_evidence_ids=[],
                    support_strength=0.72,
                    authority_grade="A0",
                    freshness_ok=not state["freshness_map"].get("freshness_debt", False),
                    audit_status="accepted",
                )
            )
            support_index[f"claim:watch:{index}"] = []
        specialist_outputs = state.get("specialist_outputs", {})
        for specialist_name, specialist_output in specialist_outputs.items():
            for index, specialist_claim in enumerate(specialist_output.get("claims", [])[:2], start=1):
                claim_id = f"claim:{specialist_name}:{index}"
                claims.append(
                    ClaimRecord(
                        claim_id=claim_id,
                        claim_text=specialist_claim,
                        claim_type="inference",
                        required_support_level="supported",
                        supporting_evidence_ids=[],
                        support_strength=0.7,
                        authority_grade="A0",
                        freshness_ok=True,
                        audit_status="accepted",
                    )
                )
                support_index[claim_id] = []
        if state["degrade_reason"]:
            claims.append(
                ClaimRecord(
                    claim_id="claim:warning",
                    claim_text=state["degrade_reason"],
                    claim_type="warning",
                    required_support_level="direct",
                    supporting_evidence_ids=[],
                    support_strength=1.0,
                    authority_grade="A0",
                    freshness_ok=True,
                    audit_status="accepted",
                )
            )
            support_index["claim:warning"] = []
        return {
            "claim_set": [item.model_dump() for item in claims],
            "claim_support_index": support_index,
        }

    async def _response_controller(self, state: V4State) -> dict[str, Any]:
        hint = state["input_envelope"].get("response_mode_hint")
        confidence = ConfidenceLedger.model_validate(state["confidence_ledger"])
        claims = [ClaimRecord.model_validate(item) for item in state["claim_set"]]
        accepted_claims = [claim for claim in claims if claim.audit_status != "rejected"]
        effective_conflict_confidence = confidence.conflict_confidence or (0.78 if not state.get("conflict_markers") else 0.45)
        mode = "grounded_direct"
        if state["input_envelope"].get("needs_clarification") and not self._has_substantive_internal_facts(state["facts_internal"]):
            mode = "insufficient_evidence"
        elif state["degrade_reason"]:
            mode = "insufficient_evidence"
        elif hint in {"memo", "presentation"} and confidence.grounding_confidence >= 0.7 and effective_conflict_confidence >= 0.7:
            mode = hint
        elif state["input_envelope"]["portfolio_dependency"]:
            mode = "decision_with_limits" if confidence.grounding_confidence >= 0.45 else "insufficient_evidence"
        elif state["retrieval_decisions"].get("mode") == "evidence":
            mode = "research_with_citations" if confidence.grounding_confidence >= 0.56 else "decision_with_limits"
        if not accepted_claims:
            mode = "insufficient_evidence"
        contract = RenderContract(
            answer_mode=mode,
            detail_level="short" if mode in DIRECT_MODES else "standard",
            citation_mode="evidence_block" if mode in {"research_with_citations", "memo", "presentation"} else "none",
            structure_mode="semi_structured" if mode in {"decision_with_limits", "research_with_citations"} else "freeform",
        )
        return {
            "render_contract": contract.model_dump(),
            "confidence_ledger": {
                **state["confidence_ledger"],
                "conflict_confidence": effective_conflict_confidence,
                "answer_confidence": min(confidence.grounding_confidence or 0.3, effective_conflict_confidence) if mode != "insufficient_evidence" else 0.28,
            },
        }

    async def _approval_gate(self, state: V4State) -> dict[str, Any]:
        requests = [ApprovalRequest.model_validate(item) for item in state["approval_requests"]]
        if state["render_contract"]["answer_mode"] == "presentation":
            requests.append(
                ApprovalRequest(
                    approval_id=f"approval:{uuid4()}",
                    reason="Presentation export requires human approval before distribution.",
                    required=True,
                )
            )
        required_requests = [request for request in requests if request.required]
        if not required_requests:
            return {"approval_requests": [item.model_dump() for item in requests]}

        raw_decision = interrupt({"approval_requests": [item.model_dump() for item in required_requests]})
        if isinstance(raw_decision, bool):
            decision = ApprovalDecision(approved=raw_decision)
        elif isinstance(raw_decision, str):
            decision = ApprovalDecision(approved=raw_decision.lower() in {"approve", "approved", "yes", "true", "allow"}, notes=raw_decision)
        else:
            decision = ApprovalDecision.model_validate(raw_decision)
        approved_id = decision.approval_id or required_requests[0].approval_id
        resolved_requests = [
            item for item in requests if not (item.required and item.approval_id == approved_id)
        ]
        if not decision.approved:
            return {
                "approval_requests": [item.model_dump() for item in resolved_requests],
                "degrade_reason": "Human approval was denied for the requested export.",
                "termination_record": TerminationRecord(
                    stop=True,
                    reason="Human approval denied the requested export.",
                    path="approval_gate",
                ).model_dump(),
                "render_contract": RenderContract(
                    answer_mode="insufficient_evidence",
                    detail_level="short",
                    citation_mode="none",
                    structure_mode="freeform",
                ).model_dump(),
            }
        return {"approval_requests": [item.model_dump() for item in resolved_requests]}

    async def _renderer(self, state: V4State) -> dict[str, Any]:
        contract = RenderContract.model_validate(state["render_contract"])
        claims = [ClaimRecord.model_validate(item) for item in state["claim_set"] if item["audit_status"] != "rejected"]
        evidence_items = [EvidenceItem.model_validate(item) for item in state["evidence_items"]]
        conflict_markers = [ConflictMarker.model_validate(item) for item in state["conflict_markers"]]
        decision, summary, recommendation = self._render_output(contract, claims, evidence_items, conflict_markers, state)
        evidence_blocks = [
            {"title": item.title, "detail": item.detail[:280]}
            for item in evidence_items[:3]
        ]
        if not evidence_blocks and claims:
            evidence_blocks = [{"title": "Audited claims", "detail": claim.claim_text} for claim in claims[:2]]
        return {
            "output_package": {
                "decision": decision,
                "summary": summary,
                "recommendation": recommendation,
                "evidence_blocks": evidence_blocks,
            }
        }

    async def _output_packager(self, state: V4State) -> dict[str, Any]:
        output = dict(state["output_package"])
        package = PackagedOutput(
            thread_refs=ThreadRefs.model_validate(state["thread_refs"]),
            decision=output["decision"],
            summary=output["summary"],
            recommendation=output["recommendation"],
            answer_mode=state["render_contract"]["answer_mode"],
            termination_reason=state["termination_record"]["reason"] or "Graph completed all required steps.",
            degrade_reason=state.get("degrade_reason"),
            evidence_blocks=output["evidence_blocks"],
            specialist_views=self._specialist_views(state),
            trace={
                "path": state["termination_record"]["path"] or "output_packager",
                "answer_mode": state["render_contract"]["answer_mode"],
                "degrade_reason": state.get("degrade_reason"),
                "conflicts": state["conflict_markers"],
                "claims": state["claim_set"],
                "retrieval": state["retrieval_decisions"],
                "specialists": state["specialist_outputs"],
                "thread_refs": state["thread_refs"],
            },
        )
        self._store.put(
            ("v4-memory", package.thread_refs.workspace_id, package.thread_refs.user_id),
            f"{package.thread_refs.thread_id}:{int(time.time())}",
            {"summary": package.summary, "decision": package.decision},
        )
        return {"output_package": package.model_dump()}

    def _after_sufficiency_gate_1(self, state: V4State) -> str:
        return "claim_auditor" if state["termination_record"]["stop"] else "retrieval_gate"

    def _after_retrieval_gate(self, state: V4State) -> str:
        if state["retrieval_decisions"].get("mode") != "none":
            return "retrieval_planner"
        return "specialist_admission_gate" if self._needs_specialists(state) else "claim_auditor"

    def _after_sufficiency_gate_2(self, state: V4State) -> str:
        return "claim_auditor" if state["termination_record"]["stop"] else "specialist_admission_gate"

    def _after_specialist_gate(self, state: V4State) -> str:
        return "claim_auditor" if state["termination_record"]["stop"] else "macro_subgraph"

    async def _run_specialist(self, specialist: str, state: V4State) -> dict[str, Any]:
        policy = ExecutionPolicy.model_validate(state["execution_policy"])
        if specialist not in policy.planned_specialists:
            return {}
        if specialist not in self._specialist_graphs:
            self._specialist_graphs[specialist] = self._build_specialist_graph(specialist)
        result = await self._specialist_graphs[specialist].ainvoke(state)
        outputs = dict(state["specialist_outputs"])
        outputs[specialist] = result["specialist_output"]
        budget = ToolBudgetState.model_validate(state["tool_budget"])
        budget.specialists_used += 1
        return {
            "specialist_outputs": outputs,
            "tool_budget": budget.model_dump(),
        }

    def _build_specialist_graph(self, specialist: str):
        class SpecialistState(TypedDict, total=False):
            facts_internal: dict[str, Any]
            evidence_items: list[dict[str, Any]]
            degrade_reason: str | None
            specialist_output: dict[str, Any]

        async def run(_: SpecialistState, *, _specialist: str = specialist) -> dict[str, Any]:
            return {"specialist_output": self._specialist_result(_specialist, _)}

        graph = StateGraph(SpecialistState)
        graph.add_node("run", run)
        graph.add_edge(START, "run")
        graph.add_edge("run", END)
        return graph.compile()

    def _specialist_result(self, specialist: str, state: dict[str, Any]) -> dict[str, Any]:
        facts_internal = state.get("facts_internal", {})
        evidence_items = [EvidenceItem.model_validate(item) for item in state.get("evidence_items", [])]
        if specialist == "macro":
            regime = facts_internal.get("regime", {})
            history = facts_internal.get("history:regime", {})
            policy = next((value for key, value in facts_internal.items() if key.startswith("policy:")), {})
            world_state = self._extract_world_state(facts_internal)
            country_snapshots = self._extract_country_snapshots(facts_internal)
            regime_label = regime.get("regime") or regime.get("regime_label")
            analogs = history if isinstance(history, list) else history.get("regimes") or history.get("analogs") or []
            claims = [f"Current market regime reads {regime_label}."] if regime_label else []
            if world_state:
                macro_line = self._world_state_summary(world_state)
                if macro_line:
                    claims.append(macro_line)
            for country_code, snapshot in country_snapshots[:2]:
                sovereign_line = self._country_snapshot_summary(country_code, snapshot)
                if sovereign_line:
                    claims.append(sovereign_line)
            policy_items = policy.get("items", []) if isinstance(policy, dict) else []
            if policy_items:
                first_policy = policy_items[0] if isinstance(policy_items[0], dict) else {}
                policy_headline = first_policy.get("title") or first_policy.get("headline")
                if policy_headline:
                    claims.append(f"Policy watch: {policy_headline}")
            return SpecialistResult(
                specialist="macro",
                summary="Macro specialist reviewed sovereign balance-sheet pressure, world-state drag, and regime context.",
                claims=claims,
                concerns=[] if analogs or regime_label or world_state or country_snapshots else ["Regime history was limited."],
                verdict="Constructive" if regime_label in {"risk_on", "sideways"} else "Defensive" if regime_label else None,
            ).model_dump()
        if specialist == "portfolio":
            portfolio = facts_internal.get("portfolio", {})
            exposures = portfolio.get("exposures", {}) if isinstance(portfolio.get("exposures", {}), dict) else {}
            risk = portfolio.get("risk", {}) if isinstance(portfolio.get("risk", {}), dict) else {}
            top_positions = exposures.get("top_positions", [])
            aapl_position = next((item for item in top_positions if item.get("ticker") == "AAPL"), None)
            return SpecialistResult(
                specialist="portfolio",
                summary="Portfolio specialist reviewed holdings, concentration, and risk context.",
                claims=(
                    [f"AAPL is already {round(float(aapl_position.get('weight', 0)) * 100, 1)}% of portfolio market value."]
                    if aapl_position
                    else []
                ),
                concerns=(
                    [f"Concentration risk is elevated at {round(float(risk.get('concentration_risk', 0)) * 100, 1)}% in the top position."]
                    if float(risk.get("concentration_risk", 0)) >= 0.3
                    else []
                ),
                verdict="Keep sizing bounded" if float(risk.get("concentration_risk", 0)) >= 0.3 else "Room to add selectively",
            ).model_dump()
        if specialist == "events":
            event_bucket = next((value for key, value in facts_internal.items() if key.startswith("events:")), {})
            company_news = next((value for key, value in facts_internal.items() if key.startswith("company_news:")), {})
            pulse = event_bucket.get("pulse", {})
            clusters = event_bucket.get("clusters", []) if isinstance(event_bucket, dict) else []
            feed = event_bucket.get("feed", []) if isinstance(event_bucket, dict) else []
            company_items = company_news.get("items", []) if isinstance(company_news, dict) else []
            pulse_headline = ""
            if isinstance(pulse, dict):
                pulse_headline = pulse.get("headline") or next(iter(pulse.get("highlights", []) or []), "")
            if not pulse_headline and isinstance(feed, list) and feed:
                first_feed = feed[0] if isinstance(feed[0], dict) else {}
                pulse_headline = first_feed.get("headline") or first_feed.get("title") or ""
            claims = ([pulse_headline] if pulse_headline else []) + ([f"{len(clusters)} event cluster(s) are active in the selected scope."] if clusters else [])
            if company_items:
                first_company_item = company_items[0] if isinstance(company_items[0], dict) else {}
                company_headline = first_company_item.get("title") or first_company_item.get("headline")
                if company_headline:
                    claims.append(f"Company news: {company_headline}")
            return SpecialistResult(
                specialist="events",
                summary="Events specialist reviewed the internal event pulse and cluster set.",
                claims=claims,
                concerns=[] if pulse_headline or clusters or feed or company_items else ["No event pulse was available."],
                verdict="Watch event drift" if pulse_headline or clusters or feed else "No event pressure detected",
            ).model_dump()
        if specialist == "research":
            company = next((value for key, value in facts_internal.items() if key.startswith("company:")), {})
            company_news = next((value for key, value in facts_internal.items() if key.startswith("company_news:")), {})
            profile = company.get("profile", {})
            news_items = company_news.get("items", []) if isinstance(company_news, dict) else []
            company_label = profile.get("ticker") or profile.get("name") or "The company"
            claims: list[str] = []
            concerns: list[str] = []
            if profile:
                if float(profile.get("earnings_quality", 0)) < 0.75:
                    concerns.append(f"{company_label} earnings quality is only {profile.get('earnings_quality'):.2f}.")
                if float(profile.get("free_cash_flow_stability", 0)) < 0.6:
                    concerns.append(f"Free cash flow stability is soft at {profile.get('free_cash_flow_stability'):.2f}.")
                if float(profile.get("leverage_ratio", 0)) > 0.65:
                    concerns.append(f"Leverage ratio is elevated at {profile.get('leverage_ratio'):.2f}.")
                claims.append(f"{company_label} fraud score is {profile.get('fraud_score'):.2f} and moat score is {profile.get('moat_score'):.2f}.")
            if news_items:
                first_news = news_items[0] if isinstance(news_items[0], dict) else {}
                news_headline = first_news.get("title") or first_news.get("headline")
                if news_headline:
                    claims.append(f"Latest company news: {news_headline}.")
            return SpecialistResult(
                specialist="research",
                summary="Research specialist reviewed company quality and internal history context.",
                claims=claims,
                concerns=concerns or (["Research evidence remained thin."] if not profile and not evidence_items and not news_items else []),
                verdict="Quality needs confirmation" if concerns else "Quality is not the main blocker",
            ).model_dump()
        if specialist == "risk":
            concerns = []
            if state.get("degrade_reason"):
                concerns.append(state["degrade_reason"])
            return SpecialistResult(
                specialist="risk",
                summary="Risk specialist audited evidence quality, conflicts, and downgrade conditions.",
                claims=["Keep the sizing decision conditional on the weakest uncovered signal."],
                concerns=concerns,
                verdict="Gate new risk through the weakest signal first",
            ).model_dump()
        if specialist == "presentation":
            return SpecialistResult(
                specialist="presentation",
                summary="Presentation specialist prepared the audited state for export-safe rendering.",
                claims=[],
                concerns=[],
                verdict="Export-safe",
            ).model_dump()
        return SpecialistResult(specialist=specialist, summary="No specialist output.", claims=[], concerns=[]).model_dump()

    async def _execute_tool(self, tool_name: str, arguments: dict[str, Any], *, state: V4State, external: bool) -> dict[str, Any]:
        policy = ExecutionPolicy.model_validate(state["execution_policy"]) if state.get("execution_policy") else None
        if policy and tool_name not in policy.allowed_tools:
            raise RuntimeError(f"Tool '{tool_name}' is not allowed by the execution policy.")
        if external:
            if tool_name == "webpage_read" and state["retrieval_decisions"].get("mode") == "web_search":
                raise RuntimeError("Simple web freshness path may not escalate to webpage_read.")
        return await self._tools.execute(tool_name, arguments)

    def _render_output(
        self,
        contract: RenderContract,
        claims: list[ClaimRecord],
        evidence_items: list[EvidenceItem],
        conflict_markers: list[ConflictMarker],
        state: V4State,
    ) -> tuple[str, str, str]:
        watch_items = self._build_watch_items(state)
        if contract.answer_mode == "insufficient_evidence":
            if state["input_envelope"].get("needs_clarification"):
                decision = "Need one clear layer of context first."
                summary = "Ask with a portfolio, ticker, country, market, event, or scenario so STRATOS can ground the answer."
                recommendation = (
                    "Try: 'price of ethereum', 'what do sticky inflation and oil mean for my portfolio', "
                    "or 'what should I watch in AAPL before adding risk'."
                )
                return decision, summary, recommendation
            decision = "Do not over-interpret this result."
            summary = state.get("degrade_reason") or "The runtime could not build enough grounded evidence for a stronger answer."
            recommendation = "Use the currently available internal context as a directional signal only and retry once fresher or stronger evidence is available."
            return decision, summary, recommendation

        if contract.answer_mode in DIRECT_MODES:
            market_line = self._market_direct_summary(state)
            macro_frame = self._macro_country_frame(state)
            query = state["input_envelope"]["query"].lower()
            prefers_news = any(token in query for token in ("news", "headline", "fed", "fomc", "rbi", "policy"))
            if macro_frame is not None:
                return macro_frame
            if prefers_news and watch_items:
                prioritized_watch_items = [
                    item for item in watch_items
                    if any(marker in item.lower() for marker in ("headline", "policy watch", "event pulse"))
                ] or watch_items
                decision = "Use the freshest grounded internal view available."
                summary = prioritized_watch_items[0]
                recommendation = "; ".join(prioritized_watch_items[:2])
                if evidence_items:
                    recommendation += f" External check: {evidence_items[0].title}."
                return decision, summary, recommendation
            if market_line:
                decision = "Use the latest internal market snapshot."
                summary = market_line
                recommendation = market_line
                if evidence_items:
                    recommendation += f" Supporting external evidence: {evidence_items[0].title}."
                return decision, summary, recommendation
            if watch_items:
                decision = "Use the freshest grounded internal view available."
                summary = watch_items[0]
                recommendation = "; ".join(watch_items[:2])
                if evidence_items:
                    recommendation += f" External check: {evidence_items[0].title}."
                return decision, summary, recommendation
            decision = "Use the shortest grounded answer available."
            summary = claims[0].claim_text if claims else "Grounded state was available."
            recommendation = summary
            if evidence_items:
                recommendation += f" Primary external evidence: {evidence_items[0].title}."
            return decision, summary, recommendation

        if contract.answer_mode == "decision_with_limits":
            council_views = self._specialist_views(state)
            summary_parts = [view["summary"] for view in council_views[:2] if view.get("summary")]
            action_parts = [view["verdict"] for view in council_views[:2] if view.get("verdict")]
            decision = "Add risk only if the quality, pulse, and regime checks stay supportive."
            summary = (
                "; ".join(summary_parts + watch_items[:2])
                if summary_parts or watch_items
                else "Internal truth and any available supporting evidence were combined, but the answer remains scoped by current evidence quality."
            )
            recommendation = (
                "PM synthesis: "
                + "; ".join(action_parts + watch_items[:3])
                if action_parts or watch_items
                else "Focus on the immediate portfolio implication, keep the answer conditional where freshness or evidence is limited, and avoid overstating precision."
            )
            return decision, summary, recommendation

        if contract.answer_mode == "research_with_citations":
            decision = "Use an evidence-led research answer."
            summary = "The runtime gathered supporting documents and ranked them before synthesis."
            recommendation = "Anchor the answer in the cited evidence blocks, carry forward the specialist concerns, and treat unsupported extensions as out of scope."
            return decision, summary, recommendation

        decision = "Render the audited result for a structured audience."
        summary = "The answer met the stricter grounding requirements for a structured output mode."
        recommendation = "Use the audited claims and evidence blocks as the basis for the final structured narrative."
        if conflict_markers:
            recommendation += f" Outstanding conflicts: {conflict_markers[0].detail}"
        return decision, summary, recommendation

    def _memo_from_state(self, state: V4State, package: PackagedOutput) -> StrategicMemo:
        confidence = state["confidence_ledger"]["answer_confidence"]
        tasks = self._tasks_from_state(state)
        specialist_views = package.specialist_views
        is_simple_quote = self._is_simple_quote_query(state)
        key_findings = [] if is_simple_quote else self._collect_key_findings(state, specialist_views)
        historical_context = [] if is_simple_quote else self._collect_historical_context(state, specialist_views)
        portfolio_impact = [] if is_simple_quote else self._collect_portfolio_impact(state, specialist_views)
        recommended_actions = [package.recommendation] if is_simple_quote else self._collect_recommended_actions(package, specialist_views)
        watch_items = [] if is_simple_quote else self._build_watch_items(state)
        return StrategicMemo(
            query=state["input_envelope"]["query"],
            plan_summary=state["termination_record"]["reason"] or "STRATOS v4 completed the graph run.",
            tasks=tasks,
            confidence_band=ConfidenceBand.from_score(confidence),
            risk_policy_status="PASS" if package.answer_mode != "insufficient_evidence" else "FAILED",
            recommendation=package.recommendation,
            worst_case=state.get("degrade_reason") or "Grounding quality may limit the reliability of this answer.",
            risk_band="Low" if package.answer_mode in DIRECT_MODES else "Medium",
            system_regime="normal" if not state["degrade_reason"] else "degraded",
            regime_stability=max(0.1, confidence),
            scenario_tree=[],
            intent=state["input_envelope"]["intent"],
            role=state["input_envelope"]["role_lens"],
            decision=package.decision,
            summary=package.summary,
            key_findings=key_findings,
            historical_context=historical_context,
            portfolio_impact=portfolio_impact,
            recommended_actions=recommended_actions,
            watch_items=watch_items,
            data_quality=self._data_quality(state),
            evidence_blocks=package.evidence_blocks,
            specialist_views=specialist_views,
        )

    def _tasks_from_state(self, state: V4State) -> list[AgentTask]:
        tasks: list[AgentTask] = []
        for bucket, payload in state["facts_internal"].items():
            if bucket == "memory_context":
                continue
            tasks.append(AgentTask(tool_name=bucket, arguments={}, status=TaskStatus.COMPLETED, result={"content": str(payload)[:400]}))
        for payload in state["facts_external"].values():
            tasks.append(AgentTask(tool_name="external_retrieval", arguments={}, status=TaskStatus.COMPLETED, result={"content": str(payload)[:400]}))
        return tasks

    def _data_quality(self, state: V4State) -> list[str]:
        lines: list[str] = []
        if state["freshness_map"].get("freshness_debt"):
            lines.append("Internal freshness debt triggered external checks.")
        if state.get("degrade_reason"):
            lines.append(state["degrade_reason"])
        if not state["evidence_items"]:
            lines.append("No external evidence items were retained.")
        return lines

    def _requires_deeper_analysis(self, state: V4State) -> bool:
        query = state["input_envelope"]["query"].lower()
        intent = state["input_envelope"].get("intent")
        if state["input_envelope"].get("needs_clarification"):
            return False
        if self._is_simple_quote_query(state):
            return False
        if state["input_envelope"].get("complexity") == "high":
            return True
        if intent in {"research", "scenario"}:
            return True
        if any(token in query for token in ("watch", "before", "compare", "history", "pulse", "event", "quality")):
            return True
        return False

    def _is_simple_quote_query(self, state: V4State) -> bool:
        query = state["input_envelope"]["query"].lower().strip()
        if not query:
            return False
        quote_markers = ("price", "quote", "spot", "last price", "market price")
        deeper_markers = (
            "watch",
            "should",
            "why",
            "impact",
            "portfolio",
            "risk",
            "quality",
            "news",
            "headline",
            "pulse",
            "history",
            "regime",
            "fed",
            "fomc",
            "rbi",
            "policy",
            "compare",
            "before",
            "add risk",
        )
        has_quote_marker = any(marker in query for marker in quote_markers)
        if not has_quote_marker:
            return False
        return not any(marker in query for marker in deeper_markers)

    def _needs_specialists(self, state: V4State) -> bool:
        policy = state.get("execution_policy") or {}
        planned = policy.get("planned_specialists") or []
        return bool(planned) and self._requires_deeper_analysis(state)

    def _infer_event_scope(
        self,
        *,
        query: str,
        market_ticker: str | None,
        company_ticker: str | None,
        country_code: str | None,
        resolved_scope: str | None,
    ) -> str:
        lowered = query.lower()
        if resolved_scope:
            return resolved_scope
        if "btc" in lowered or market_ticker == "X:BTCUSD" or company_ticker == "BTC":
            return "btc"
        if country_code == "IND" or "india" in lowered:
            return "india"
        if country_code == "USA" or "us" in lowered:
            return "us"
        return "global"

    async def _resolve_query_entities(self, query: str) -> ResolvedEntities:
        if not query.strip():
            return ResolvedEntities(confidence=0.0)
        try:
            model = self._resolver_model or self._build_model()
            self._resolver_model = model
            structured = model.with_structured_output(ResolvedEntities)
            result = await structured.ainvoke(
                [
                    (
                        "system",
                        "Resolve financial entities from the user query. "
                        "Return market_ticker for tradable market instruments like BTC, ETH, FX pairs, commodities, and indices. "
                        "Return company_ticker for listed companies. "
                        "Return ISO-3 country_codes when countries are mentioned. "
                        "Use event_scope only when the query clearly targets btc, india, us, or global. "
                        "Prefer null over guessing. "
                        "Examples: 'price of bitcoin' -> market_ticker X:BTCUSD. "
                        "'price of ETH' -> market_ticker X:ETHUSD. "
                        "'price of inr over usd' -> market_ticker FX:INRUSD. "
                        "'price of APPL' likely refers to Apple -> company_ticker AAPL. "
                        "'How should I frame India sovereign risk versus US macro pressure this week?' -> country_codes ['IND','USA']."
                    ),
                    ("human", query),
                ]
            )
            if isinstance(result, ResolvedEntities):
                resolved = result
            elif hasattr(result, "model_dump"):
                resolved = ResolvedEntities.model_validate(result.model_dump())
            else:
                resolved = ResolvedEntities.model_validate(result)
            resolved = self._normalize_resolved_entities(query, resolved)
            if resolved.confidence <= 0:
                resolved.confidence = 0.7 if any((resolved.market_ticker, resolved.company_ticker, resolved.country_codes, resolved.event_scope)) else 0.4
            return resolved
        except Exception:
            return self._fallback_resolved_entities(query)

    def _build_model(self) -> BaseChatModel:
        provider = self._settings.llm_provider
        explicit_model = self._settings.langchain_agent_model
        if provider == "ollama":
            return ChatOllama(
                model=explicit_model or self._settings.ollama_model,
                base_url=self._settings.ollama_base_url,
                temperature=0.1,
            )
        if provider == "groq":
            return ChatOpenAI(
                model=explicit_model or self._settings.groq_model,
                api_key=self._settings.groq_api_key,
                base_url=self._settings.groq_api_base,
                temperature=0.1,
                max_tokens=self._settings.langchain_agent_max_tokens,
            )
        return ChatOpenAI(
            model=explicit_model or self._settings.openai_model,
            api_key=self._settings.openai_api_key,
            temperature=0.1,
            max_tokens=self._settings.langchain_agent_max_tokens,
        )

    def _build_watch_items(self, state: V4State) -> list[str]:
        items: list[str] = []
        facts_internal = state.get("facts_internal", {})
        world_state = self._extract_world_state(facts_internal)
        country_snapshots = self._extract_country_snapshots(facts_internal)

        macro_line = self._world_state_summary(world_state)
        if macro_line:
            items.append(macro_line)
        for country_code, snapshot in country_snapshots[:2]:
            sovereign_line = self._country_snapshot_summary(country_code, snapshot)
            if sovereign_line:
                items.append(sovereign_line)

        company = next((value for key, value in facts_internal.items() if key.startswith("company:")), {})
        profile = company.get("profile", {})
        if profile:
            company_label = profile.get("ticker") or profile.get("name") or "This company"
            earnings_quality = float(profile.get("earnings_quality", 0))
            if earnings_quality < 0.75:
                items.append(f"{company_label} earnings quality is only {earnings_quality:.2f}, so wait for cleaner quality confirmation.")
            fcf_stability = float(profile.get("free_cash_flow_stability", 0))
            if fcf_stability < 0.6:
                items.append(f"Free cash flow stability is soft at {fcf_stability:.2f}.")
            leverage_ratio = float(profile.get("leverage_ratio", 0))
            if leverage_ratio > 0.65:
                items.append(f"Leverage is elevated at {leverage_ratio:.2f}, which argues against adding size aggressively.")

        portfolio = facts_internal.get("portfolio", {})
        exposures = portfolio.get("exposures", {}) if isinstance(portfolio.get("exposures", {}), dict) else {}
        risk = portfolio.get("risk", {}) if isinstance(portfolio.get("risk", {}), dict) else {}
        top_positions = exposures.get("top_positions", [])
        aapl_position = next((item for item in top_positions if item.get("ticker") == "AAPL"), None)
        if aapl_position:
            items.append(f"AAPL already represents {float(aapl_position.get('weight', 0)) * 100:.1f}% of the portfolio.")
        concentration = float(risk.get("concentration_risk", 0))
        if concentration >= 0.3:
            items.append(f"Top-position concentration is high at {concentration * 100:.1f}%.")

        event_bucket = next((value for key, value in facts_internal.items() if key.startswith("events:")), {})
        pulse = event_bucket.get("pulse", {})
        if isinstance(pulse, dict):
            event_headline = pulse.get("headline") or next(iter(pulse.get("highlights", []) or []), None)
            if event_headline:
                items.append(f"Event pulse headline: {event_headline}")
        company_news = next((value for key, value in facts_internal.items() if key.startswith("company_news:")), {})
        company_news_items = company_news.get("items", []) if isinstance(company_news, dict) else []
        if company_news_items:
            first_company_news = company_news_items[0] if isinstance(company_news_items[0], dict) else {}
            company_headline = first_company_news.get("title") or first_company_news.get("headline")
            if company_headline:
                items.append(f"Latest company headline: {company_headline}")
        policy_bucket = next((value for key, value in facts_internal.items() if key.startswith("policy:")), {})
        policy_items = policy_bucket.get("items", []) if isinstance(policy_bucket, dict) else []
        if policy_items:
            first_policy = policy_items[0] if isinstance(policy_items[0], dict) else {}
            policy_headline = first_policy.get("title") or first_policy.get("headline")
            if policy_headline:
                items.append(f"Policy watch: {policy_headline}")

        regime = facts_internal.get("regime", {})
        regime_label = regime.get("regime") or regime.get("regime_label")
        if regime_label:
            items.append(f"Current regime reads {regime_label}.")

        history = facts_internal.get("history:regime", {})
        if isinstance(history, list) and history:
            items.append("Review the closest prior regime analogs before adding incremental beta.")
        elif isinstance(history, dict) and history:
            items.append("Regime history is available and should be checked against prior analogs.")

        return items

    def _specialist_views(self, state: V4State) -> list[dict[str, Any]]:
        outputs = state.get("specialist_outputs", {})
        ordering = ["macro", "portfolio", "events", "research", "risk", "presentation"]
        views: list[dict[str, Any]] = []
        for specialist in ordering:
            payload = outputs.get(specialist)
            if not payload:
                continue
            result = SpecialistResult.model_validate(payload)
            views.append(
                {
                    "specialist": result.specialist,
                    "title": readable_specialist_title(result.specialist),
                    "summary": result.summary,
                    "verdict": result.verdict,
                    "claims": result.claims[:2],
                    "concerns": result.concerns[:2],
                }
            )
        return views

    def _collect_key_findings(self, state: V4State, specialist_views: list[dict[str, Any]]) -> list[str]:
        findings: list[str] = []
        for view in specialist_views:
            findings.extend(view.get("claims", []))
            findings.extend(view.get("concerns", []))
        if not findings:
            findings = [claim["claim_text"] for claim in state["claim_set"] if claim["audit_status"] != "rejected"]
        return findings[:4]

    def _collect_historical_context(self, state: V4State, specialist_views: list[dict[str, Any]]) -> list[str]:
        items: list[str] = []
        history = state.get("facts_internal", {}).get("history:regime", {})
        if isinstance(history, dict):
            analogs = history.get("analogs") or history.get("regimes") or []
            if analogs:
                items.append(f"{len(analogs)} prior regime analog(s) are available for comparison.")
        elif isinstance(history, list) and history:
            items.append(f"{len(history)} prior regime analog(s) are available for comparison.")
        for view in specialist_views:
            if view["specialist"] == "macro":
                items.extend(view.get("claims", [])[:1])
        return items[:3]

    def _collect_portfolio_impact(self, state: V4State, specialist_views: list[dict[str, Any]]) -> list[str]:
        items: list[str] = []
        for view in specialist_views:
            if view["specialist"] == "portfolio":
                items.extend(view.get("claims", []))
                items.extend(view.get("concerns", []))
        if not items:
            watch_items = self._build_watch_items(state)
            items = [item for item in watch_items if "portfolio" in item.lower() or "concentration" in item.lower() or "top-position" in item.lower()]
        return items[:3]

    @staticmethod
    def _collect_recommended_actions(package: PackagedOutput, specialist_views: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        for view in specialist_views:
            verdict = view.get("verdict")
            if verdict:
                actions.append(f"{view['title']}: {verdict}")
        if package.recommendation not in actions:
            actions.append(package.recommendation)
        return actions[:4]

    def _market_direct_summary(self, state: V4State) -> str | None:
        market_bucket = next((value for key, value in state.get("facts_internal", {}).items() if key.startswith("market:")), None)
        if not isinstance(market_bucket, dict):
            company_bucket = next((value for key, value in state.get("facts_internal", {}).items() if key.startswith("company:")), None)
            if not isinstance(company_bucket, dict):
                return None
            recent_market_data = company_bucket.get("recent_market_data")
            if not isinstance(recent_market_data, list) or not recent_market_data:
                return None
            latest = recent_market_data[0]
            ticker = latest.get("ticker") or company_bucket.get("profile", {}).get("ticker") or "asset"
            close = latest.get("close")
            timestamp = latest.get("timestamp")
            if close is None:
                return None
            if timestamp:
                return f"{ticker} last closed at {close} as of {timestamp}."
            return f"{ticker} last closed at {close}."
        if market_bucket.get("pending"):
            ticker = market_bucket.get("ticker") or "asset"
            label = {
                "X:BTCUSD": "Bitcoin",
                "X:ETHUSD": "Ethereum",
                "X:XAUUSD": "Gold",
                "CMD:CRUDE": "Crude oil",
                "INDEX:NIFTY50": "NIFTY 50",
                "INDEX:SENSEX": "SENSEX",
                "INDEX:BANKNIFTY": "BANKNIFTY",
                "INDEX:INDIAVIX": "India VIX",
                "INDEX:DXY": "DXY",
                "MACRO:US10Y": "US 10Y",
                "FX:USDINR": "USD/INR",
                "FX:INRUSD": "INR/USD",
            }.get(ticker, ticker)
            retry_seconds = market_bucket.get("suggested_retry_seconds")
            if retry_seconds:
                return f"{label} snapshot is still building. Retry in about {retry_seconds} seconds."
            return f"{label} snapshot is still building."
        latest = market_bucket.get("latest")
        if not isinstance(latest, dict):
            return None
        ticker = market_bucket.get("ticker") or latest.get("ticker") or "asset"
        close = latest.get("close")
        timestamp = latest.get("timestamp")
        if close is None:
            return None
        label = {
            "X:BTCUSD": "Bitcoin",
            "X:ETHUSD": "Ethereum",
            "X:XAUUSD": "Gold",
            "CMD:CRUDE": "Crude oil",
            "INDEX:NIFTY50": "NIFTY 50",
            "INDEX:SENSEX": "SENSEX",
            "INDEX:BANKNIFTY": "BANKNIFTY",
            "INDEX:INDIAVIX": "India VIX",
            "INDEX:DXY": "DXY",
            "MACRO:US10Y": "US 10Y",
            "FX:USDINR": "USD/INR",
            "FX:INRUSD": "INR/USD",
        }.get(ticker, ticker)
        if timestamp:
            return f"{label} last closed at {close} as of {timestamp}."
        return f"{label} last closed at {close}."

    def _macro_country_frame(self, state: V4State) -> tuple[str, str, str] | None:
        if state["input_envelope"].get("intent") != "macro":
            return None

        country_snapshots = self._extract_country_snapshots(state.get("facts_internal", {}))
        if not country_snapshots:
            return None

        snapshot_map = {code: snapshot for code, snapshot in country_snapshots}
        india = snapshot_map.get("IND")
        us = snapshot_map.get("USA")

        if india and us:
            india_debt = india.get("debt_gdp")
            us_debt = us.get("debt_gdp")
            india_deficit = india.get("fiscal_deficit")
            us_deficit = us.get("fiscal_deficit")

            relative_balance_sheet = (
                india_debt is not None
                and us_debt is not None
                and india_deficit is not None
                and us_deficit is not None
                and float(india_debt) < float(us_debt)
                and float(india_deficit) <= float(us_deficit)
            )

            decision = "Frame India as the relative sovereign-balance-sheet story and the US as the main macro transmission channel."
            if relative_balance_sheet:
                summary = (
                    f"India screens cleaner than the US on sovereign debt and fiscal metrics "
                    f"({float(india_debt):.1f}% vs {float(us_debt):.1f}% debt-to-GDP; "
                    f"{float(india_deficit):.1f}% vs {float(us_deficit):.1f}% fiscal deficit), "
                    "so this week the bigger cross-asset pressure should be framed through US rates, dollar, and liquidity."
                )
            else:
                summary = (
                    "Frame the setup as a two-part risk: India sovereign resilience still matters locally, "
                    "but the dominant cross-asset pressure likely runs through US rates, dollar strength, and global liquidity."
                )
            recommendation = (
                "Lead with: India is not the immediate source of systemic stress, but it remains exposed to tighter global financial "
                "conditions if US macro pressure keeps yields and the dollar elevated. Watch India fiscal slippage and currency volatility, "
                "but anchor the weekly risk framing to the US macro impulse first."
            )
            return decision, summary, recommendation

        country_code, snapshot = country_snapshots[0]
        sovereign_line = self._country_snapshot_summary(country_code, snapshot)
        if sovereign_line is None:
            return None
        decision = "Frame the question through sovereign balance-sheet pressure first."
        summary = sovereign_line
        recommendation = (
            "Translate the country setup into debt, fiscal, currency, and policy transmission rather than using company-style quality language."
        )
        return decision, summary, recommendation

    def _stream_event_from_graph_event(self, event: dict[str, Any], refs: ThreadRefs) -> str | None:
        name = event.get("name")
        if name == "LangGraph":
            return None
        if event["event"] == "on_chain_start":
            return self._event("node_started", {"thread_id": refs.thread_id, "run_id": refs.run_id, "node": name})
        if event["event"] != "on_chain_end":
            return None
        payload = {"thread_id": refs.thread_id, "run_id": refs.run_id, "node": name}
        output = event["data"].get("output", {})
        if name in {"intake_router", "context_builder", "freshness_adjudicator", "execution_planner", "response_controller"}:
            payload["state"] = self._jsonable(output)
            if name == "intake_router":
                return self._event("route", payload)
            if name == "freshness_adjudicator" and "freshness_map" in output:
                return self._event("confidence_update", {**payload, "freshness": output["freshness_map"]})
            if name == "execution_planner":
                return self._event("budget_update", {**payload, "tool_budget": output.get("tool_budget"), "policy": output.get("execution_policy")})
            if name == "response_controller":
                return self._event("confidence_update", {**payload, "render_contract": output.get("render_contract")})
        if name in {"retriever", "reranker", "retrieval_judge"}:
            payload["state"] = self._jsonable(output)
            if name == "retriever":
                return self._event("source_found", payload)
            if name == "retrieval_judge" and output.get("retrieval_decisions", {}).get("judge", {}).get("passed") is False:
                return self._event("evidence_insufficient", payload)
        if name in {"sufficiency_gate_1", "sufficiency_gate_2"} and output.get("termination_record", {}).get("stop"):
            return self._event("sufficiency_passed", {**payload, "termination": output["termination_record"]})
        if name == "claim_auditor":
            return self._event("claim_audit_summary", {**payload, "claims": output.get("claim_set", [])})
        if name == "approval_gate" and output.get("approval_requests"):
            return self._event("approval_required", {**payload, "approval_requests": output["approval_requests"]})
        if name == "output_packager":
            return self._event("termination_reason", {**payload, "termination": output.get("output_package", {}).get("termination_reason")})
        return self._event("node_completed", payload)

    @staticmethod
    def _event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    @staticmethod
    def _text_query(inputs: list[V4InputItem]) -> str:
        for item in inputs:
            if item.type == "text" and item.content:
                return item.content.strip()
        return ""

    @staticmethod
    def _fallback_resolved_entities(query: str) -> ResolvedEntities:
        lowered = query.lower().strip()
        company_match = re.search(r"\b[A-Z]{2,5}\b", query)
        company_ticker = company_match.group(0) if company_match else None
        country_codes: list[str] = []
        if "india" in lowered:
            country_codes.append("IND")
        if "us " in lowered or "u.s." in lowered or "united states" in lowered:
            country_codes.append("USA")
        event_scope = None
        if "india" in lowered:
            event_scope = "india"
        elif re.search(r"\bus\b", lowered):
            event_scope = "us"
        elif "global" in lowered:
            event_scope = "global"
        if company_ticker in {"US", "USA", "IND", "IN", "UK", "EU", "FED", "RBI", "ECB"}:
            company_ticker = None
        if country_codes and any(token in lowered for token in ("sovereign", "macro", "country", "policy", "debt", "fiscal", "currency", "inflation", "rates", "pressure")):
            company_ticker = None
        return ResolvedEntities(
            company_ticker=company_ticker,
            country_codes=country_codes,
            event_scope=event_scope,
            confidence=0.45 if any((company_ticker, country_codes, event_scope)) else 0.2,
        )

    @staticmethod
    def _normalize_resolved_entities(query: str, resolved: ResolvedEntities) -> ResolvedEntities:
        lowered = query.lower()
        market_aliases = {
            "btc": "X:BTCUSD",
            "bitcoin": "X:BTCUSD",
            "eth": "X:ETHUSD",
            "ethereum": "X:ETHUSD",
            "gold": "X:XAUUSD",
            "xau": "X:XAUUSD",
            "crude": "CMD:CRUDE",
            "oil": "CMD:CRUDE",
            "nifty": "INDEX:NIFTY50",
            "sensex": "INDEX:SENSEX",
            "banknifty": "INDEX:BANKNIFTY",
            "dxy": "INDEX:DXY",
            "us10y": "MACRO:US10Y",
        }

        if resolved.market_ticker is None:
            for token, ticker in market_aliases.items():
                if re.search(rf"\b{re.escape(token)}\b", lowered):
                    resolved.market_ticker = ticker
                    break

        if resolved.market_ticker is None and "inr" in lowered and "usd" in lowered:
            inr_index = lowered.find("inr")
            usd_index = lowered.find("usd")
            resolved.market_ticker = "FX:INRUSD" if inr_index <= usd_index else "FX:USDINR"

        if resolved.market_ticker is not None and (resolved.company_ticker or "").upper() in {
            "BTC",
            "BITCOIN",
            "ETH",
            "ETHEREUM",
            "INR",
            "USD",
            "DXY",
            "XAU",
            "GOLD",
            "CRUDE",
            "OIL",
            "NIFTY",
            "SENSEX",
            "BANKNIFTY",
        }:
            resolved.company_ticker = None

        return resolved

    @staticmethod
    def _should_run_company_analysis(*, query: str, resolved: ResolvedEntities) -> bool:
        ticker = (resolved.company_ticker or "").upper()
        if not ticker:
            return False
        if ticker in {"US", "USA", "IND", "IN", "UK", "EU", "FED", "RBI", "ECB"}:
            return False
        if resolved.market_ticker:
            return False

        lowered = query.lower()
        company_markers = (
            "company",
            "stock",
            "shares",
            "ticker",
            "single-name",
            "earnings",
            "valuation",
            "multiple",
            "quality",
            "free cash flow",
            "guidance",
            "buyback",
        )
        macro_markers = ("sovereign", "macro", "country", "policy", "debt", "fiscal", "currency", "inflation", "rates", "pressure")
        if any(marker in lowered for marker in company_markers):
            return True
        if resolved.country_codes and any(marker in lowered for marker in macro_markers):
            return False
        return len(ticker) >= 3

    @staticmethod
    def _extract_world_state(facts_internal: dict[str, Any]) -> dict[str, Any]:
        world_bucket = facts_internal.get("world_state", {})
        if isinstance(world_bucket, dict):
            nested = world_bucket.get("world_state")
            if isinstance(nested, dict):
                return nested
            return world_bucket
        return {}

    @staticmethod
    def _extract_country_snapshots(facts_internal: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
        snapshots: list[tuple[str, dict[str, Any]]] = []
        for key, payload in facts_internal.items():
            if not key.startswith("country:") or not isinstance(payload, dict):
                continue
            country_code = key.split(":", 1)[1]
            snapshot = payload.get("country")
            if isinstance(snapshot, dict):
                snapshots.append((country_code, snapshot))
        return snapshots

    @staticmethod
    def _world_state_summary(world_state: dict[str, Any]) -> str | None:
        if not world_state:
            return None
        inflation = world_state.get("inflation")
        rates = world_state.get("interest_rate") or world_state.get("rates")
        oil = world_state.get("oil") or world_state.get("commodity_index")
        parts: list[str] = []
        if inflation is not None:
            parts.append(f"global inflation is {float(inflation):.1f}")
        if rates is not None:
            parts.append(f"rates are {float(rates):.1f}")
        if oil is not None:
            parts.append(f"commodity pressure is {float(oil):.1f}")
        if not parts:
            return None
        return "World macro backdrop: " + ", ".join(parts[:3]) + "."

    @staticmethod
    def _country_snapshot_summary(country_code: str, snapshot: dict[str, Any]) -> str | None:
        if not snapshot:
            return None
        label = {"IND": "India", "USA": "US"}.get(country_code, country_code)
        debt_gdp = snapshot.get("debt_gdp")
        fiscal_deficit = snapshot.get("fiscal_deficit")
        political_stability = snapshot.get("political_stability")
        currency_volatility = snapshot.get("currency_volatility")
        if debt_gdp is not None and fiscal_deficit is not None:
            return (
                f"{label} sovereign snapshot: debt-to-GDP is {float(debt_gdp):.1f} and fiscal deficit is {float(fiscal_deficit):.1f}, "
                "which sets the near-term balance-sheet pressure."
            )
        if currency_volatility is not None and political_stability is not None:
            return (
                f"{label} sovereign snapshot: currency volatility is {float(currency_volatility):.2f} and political stability is {float(political_stability):.2f}."
            )
        return None

    @staticmethod
    def _has_substantive_internal_facts(facts_internal: dict[str, Any]) -> bool:
        return any(key != "memory_context" for key in facts_internal)

    @staticmethod
    def _needs_clarification(query: str) -> bool:
        lowered = query.strip().lower()
        if not lowered:
            return True
        if V4GraphRuntime._is_conversational_query(query):
            return False
        generic_phrases = {
            "what to do in this",
            "what should i do",
            "what to do",
            "help me",
            "now what",
            "tell me",
        }
        if lowered in generic_phrases:
            return True
        if len(lowered.split()) <= 4 and not any(
            token in lowered
            for token in (
                "price",
                "btc",
                "bitcoin",
                "eth",
                "ethereum",
                "aapl",
                "portfolio",
                "risk",
                "macro",
                "oil",
                "inflation",
                "india",
                "us",
                "market",
                "gold",
                "crude",
            )
        ):
            return True
        return False

    @staticmethod
    def _is_conversational_query(query: str) -> bool:
        lowered = query.strip().lower()
        if not lowered:
            return False
        exact_matches = {
            "hi",
            "hello",
            "hey",
            "yo",
            "good morning",
            "good evening",
            "help",
            "what can you do",
            "who are you",
        }
        if lowered in exact_matches:
            return True
        return any(
            phrase in lowered
            for phrase in (
                "how can you help",
                "what can stratos do",
                "what do you do",
                "how are you",
            )
        )

    @staticmethod
    def _authority_for_url(url: str | None) -> Literal["A0", "A1", "A2", "A3", "A4"]:
        if not url:
            return "A4"
        domain = urlparse(url).netloc.lower()
        if any(token in domain for token in ("sec.gov", "rbi.org", "federalreserve.gov", "worldbank.org")):
            return "A1"
        if any(token in domain for token in ("reuters.com", "bloomberg.com", "cnbc.com")):
            return "A2"
        return "A4"

    @staticmethod
    def _query_term_match(query: str, text: str) -> bool:
        terms = {token for token in re.split(r"\W+", query.lower()) if len(token) > 3}
        haystack = text.lower()
        return any(term in haystack for term in terms)

    @staticmethod
    def _jsonable(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, dict):
            return {k: V4GraphRuntime._jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [V4GraphRuntime._jsonable(item) for item in value]
        return value


def readable_specialist_title(name: str) -> str:
    mapping = {
        "macro": "Macro view",
        "portfolio": "Portfolio manager",
        "events": "Event pulse",
        "research": "Quality research",
        "risk": "Risk judge",
        "presentation": "Presentation",
    }
    return mapping.get(name, name.replace("_", " ").title())


@lru_cache
def build_v4_runtime(
    settings: Settings,
    tools: ToolRegistry,
    general_runtime: LangChainAgentRuntime | None = None,
) -> V4GraphRuntime:
    return V4GraphRuntime(settings=settings, tools=tools, general_runtime=general_runtime)
