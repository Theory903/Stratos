"""Guardrailed V2 orchestration use cases."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from stratos_orchestrator.application.execute_tool import ExecuteToolUseCase
from stratos_orchestrator.application.generate_memo import GenerateMemoUseCase
from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.domain.entities import AgentTask, ConfidenceBand, ExecutionPlan, StrategicMemo, TaskStatus


def _normalize_arguments(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"))


def _classify_intent(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ("portfolio", "holding", "rebalance", "book", "position")):
        return "portfolio"
    if any(token in lowered for token in ("scenario", "what if", "shock", "oil", "inflation", "btc")):
        return "scenario"
    if any(token in lowered for token in ("policy", "regulation", "rbi", "fed")):
        return "policy"
    if any(token in lowered for token in ("valuation", "dcf", "multiple")):
        return "valuation"
    if any(token in lowered for token in ("macro", "country", "rates", "inflation")):
        return "macro"
    return "research"


def _classify_role(query: str) -> str:
    lowered = query.lower()
    if "ceo" in lowered:
        return "ceo"
    if "cfo" in lowered or "treasury" in lowered:
        return "cfo"
    if "analyst" in lowered or "cfa" in lowered or "ca " in lowered:
        return "analyst"
    return "pm"


def _requires_live_consumer_price(query: str) -> bool:
    lowered = query.lower()
    return (
        any(token in lowered for token in ("petrol", "diesel", "fuel price", "gas price", "pump price"))
        and any(token in lowered for token in ("current", "today", "latest", "right now", "now"))
    )


def _seed_tasks(query: str, intent: str, role: str) -> list[AgentTask]:
    lowered = query.lower()
    seeded: list[AgentTask] = []
    if _requires_live_consumer_price(query):
        return seeded

    portfolio_context = any(token in lowered for token in ("portfolio", "book", "position", "holding", "rebalance", "exposure"))
    scenario_context = any(token in lowered for token in ("scenario", "what if", "shock"))
    india_context = "india" in lowered or "ind " in lowered or "rbi" in lowered
    us_context = any(token in lowered for token in ("us ", "usa", "fomc", "fed"))
    macro_context = any(token in lowered for token in ("macro", "rates", "inflation", "sovereign", "policy", "debt", "fiscal"))

    if portfolio_context or intent in {"portfolio", "scenario"} or scenario_context:
        scenario = None
        if any(token in lowered for token in ("oil", "inflation", "india", "btc")):
            scenario = "oil_sticky_india_btc"
        seeded.extend(
            [
                AgentTask(tool_name="portfolio_analyze", arguments={"name": "primary", **({"scenario": scenario} if scenario else {})}),
                AgentTask(tool_name="events_analyze", arguments={"scope": "global", "query": query[:120]}),
                AgentTask(tool_name="history_analyze", arguments={"entity_type": "market_regime", "entity_id": "global"}),
            ]
        )
        return seeded

    if macro_context or india_context or us_context:
        if india_context:
            seeded.append(
                AgentTask(tool_name="macro_analyze_country", arguments={"country_code": "IND", "include_world_state": True})
            )
            seeded.append(
                AgentTask(tool_name="events_analyze", arguments={"scope": "india", "query": query[:120]})
            )
        if us_context:
            seeded.append(
                AgentTask(tool_name="macro_analyze_country", arguments={"country_code": "USA", "include_world_state": True})
            )
            seeded.append(
                AgentTask(tool_name="events_analyze", arguments={"scope": "us", "query": query[:120]})
            )
        if india_context and "sovereign" in lowered:
            seeded.append(
                AgentTask(
                    tool_name="history_analyze",
                    arguments={"entity_type": "country", "entity_id": "IND", "metric": "sovereign_risk_spread"},
                )
            )
        seeded.append(AgentTask(tool_name="events_analyze", arguments={"scope": "global", "query": query[:120]}))
        seeded.append(AgentTask(tool_name="history_analyze", arguments={"entity_type": "market_regime", "entity_id": "global"}))
    return seeded


def _unsupported_query_memo(query: str, intent: str, role: str) -> StrategicMemo:
    return StrategicMemo(
        query=query,
        plan_summary="No compatible internal tool for live retail fuel pricing.",
        tasks=[],
        confidence_band=ConfidenceBand.from_score(0.15),
        risk_policy_status="PASS",
        recommendation=(
            "Use a live public fuel-price source or state-run OMC website for the current petrol price; "
            "the STRATOS stack does not carry live retail pump pricing."
        ),
        worst_case="Acting on an inferred price here would be misleading.",
        risk_band="Low",
        system_regime="normal",
        regime_stability=1.0,
        scenario_tree=[],
        intent=intent,
        role=role,
        decision="Do not use STRATOS for live pump-price lookup.",
        summary=(
            "This workspace can analyze macro, market, event, and portfolio signals, but it does not have a "
            "live India retail petrol price feed. A direct price answer from the current tools would be unreliable."
        ),
        key_findings=[
            "No tool in the current registry returns live India retail petrol prices.",
            "The available tools are portfolio, macro, events, history, research, and scenario analytics.",
            "A live consumer-price lookup needs an external source outside the current stack.",
        ],
        historical_context=[],
        portfolio_impact=[],
        recommended_actions=[
            "Check a live fuel-price source for the exact city-level petrol rate.",
            "Ask STRATOS a follow-up such as how higher fuel prices affect India inflation, RBI, or your portfolio.",
        ],
        watch_items=[
            "India CPI and core inflation",
            "Brent or crude oil trend",
            "Rupee weakness versus USD",
        ],
        data_quality=[
            "No live retail fuel-price feed is connected.",
            "A direct current-price answer would require external web or API access.",
        ],
        evidence_blocks=[
            {
                "title": "Tool coverage",
                "detail": "Current registry covers macro, events, history, portfolio, policy, and company workflows, not live pump prices.",
            }
        ],
    )


class GuardrailedPlan:
    """Validate tool existence, schema shape, budget, and duplicates."""

    def __init__(self, tools, max_budget: int) -> None:
        self._tools = tools
        self._max_budget = max_budget

    def apply(self, plan: ExecutionPlan) -> ExecutionPlan:
        validated: list[AgentTask] = []
        seen: set[tuple[str, str]] = set()
        for task in plan.tasks:
            if len(validated) >= self._max_budget:
                break
            if not self._tools.has_tool(task.tool_name):
                task.status = TaskStatus.FAILED
                task.error = f"Unknown tool: {task.tool_name}"
                continue
            if not self._is_valid(task.tool_name, task.arguments):
                task.status = TaskStatus.FAILED
                task.error = f"Invalid arguments for tool: {task.tool_name}"
                continue
            key = (task.tool_name, _normalize_arguments(task.arguments))
            if key in seen:
                continue
            seen.add(key)
            validated.append(task)
        plan.tasks = validated
        return plan

    def _is_valid(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        schema = self._tools.get_schema(tool_name)
        if schema is None:
            return False
        parameters = schema.get("parameters", {})
        required = set(parameters.get("required", []))
        properties = parameters.get("properties", {})
        if not required.issubset(arguments.keys()):
            return False
        for key, value in arguments.items():
            spec = properties.get(key)
            if spec is None:
                return False
            expected_type = spec.get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False
            if expected_type == "integer" and not isinstance(value, int):
                return False
            if expected_type == "number" and not isinstance(value, (int, float)):
                return False
            if expected_type == "boolean" and not isinstance(value, bool):
                return False
            if expected_type == "object" and not isinstance(value, dict):
                return False
        return True


def _merge_seeded_tasks(plan: ExecutionPlan, intent: str, role: str) -> ExecutionPlan:
    existing = {(task.tool_name, _normalize_arguments(task.arguments)) for task in plan.tasks}
    for task in _seed_tasks(plan.query, intent, role):
        key = (task.tool_name, _normalize_arguments(task.arguments))
        if key not in existing:
            plan.tasks.append(task)
            existing.add(key)
    return plan


class V2OrchestrateUseCase:
    """Validated, budgeted orchestration for V2 routes."""

    def __init__(
        self,
        *,
        planner: PlanTasksUseCase,
        executor: ExecuteToolUseCase,
        memo_generator: GenerateMemoUseCase,
        tools,
        max_budget: int,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._memo_generator = memo_generator
        self._guardrails = GuardrailedPlan(tools, max_budget)

    async def execute(self, query: str) -> StrategicMemo:
        intent = _classify_intent(query)
        role = _classify_role(query)
        if _requires_live_consumer_price(query):
            return _unsupported_query_memo(query, intent, role)
        plan = await self._planner.execute(query)
        plan = _merge_seeded_tasks(plan, intent, role)
        plan = self._guardrails.apply(plan)
        for task in plan.tasks:
            await self._executor.execute(task, vix=20.0, correlation=0.5, stability=1.0)
        return await self._memo_generator.execute(
            plan,
            regime="normal",
            stability=1.0,
            intent=intent,
            role=role,
        )


class V2StreamOrchestrateUseCase:
    """Streaming orchestration with the same V2 guardrails."""

    def __init__(
        self,
        *,
        planner: PlanTasksUseCase,
        executor: ExecuteToolUseCase,
        memo_generator: GenerateMemoUseCase,
        tools,
        max_budget: int,
    ) -> None:
        self._planner = planner
        self._executor = executor
        self._memo_generator = memo_generator
        self._guardrails = GuardrailedPlan(tools, max_budget)

    async def execute(self, query: str) -> AsyncGenerator[str, None]:
        intent = _classify_intent(query)
        role = _classify_role(query)
        yield self._event("status", "Planning execution strategy...")
        yield self._event("context", {"intent": intent, "role": role})
        if _requires_live_consumer_price(query):
            memo = _unsupported_query_memo(query, intent, role)
            yield self._event("plan", [])
            yield self._event("status", "No compatible live-price tool available...")
            yield self._event(
                "final_memo",
                {
                    "intent": memo.intent,
                    "role": memo.role,
                    "decision": memo.decision,
                    "summary": memo.summary,
                    "recommendation": memo.recommendation,
                    "key_findings": memo.key_findings,
                    "historical_context": memo.historical_context,
                    "portfolio_impact": memo.portfolio_impact,
                    "recommended_actions": memo.recommended_actions,
                    "watch_items": memo.watch_items,
                    "data_quality": memo.data_quality,
                    "evidence_blocks": memo.evidence_blocks,
                    "confidence_score": memo.confidence_band.score,
                    "confidence_calibration": memo.confidence_band.calibration,
                    "risk_band": memo.risk_band,
                    "scenario_tree": memo.scenario_tree,
                    "worst_case": memo.worst_case,
                },
            )
            return
        plan = await self._planner.execute(query)
        plan = _merge_seeded_tasks(plan, intent, role)
        plan = self._guardrails.apply(plan)
        yield self._event(
            "plan",
            [{"tool_name": task.tool_name, "arguments": task.arguments} for task in plan.tasks],
        )

        for task in plan.tasks:
            yield self._event("status", f"Executing {task.tool_name}...")
            await self._executor.execute(task, vix=20.0, correlation=0.5, stability=1.0)
            if task.status == TaskStatus.COMPLETED:
                yield self._event(
                    "task_result",
                    {
                        "tool": task.tool_name,
                        "status": "success",
                        "result_summary": str(task.result)[:200],
                    },
                )
            else:
                yield self._event(
                    "task_result",
                    {"tool": task.tool_name, "status": "failed", "error": task.error},
                )

        yield self._event("status", "Synthesizing strategic memo...")
        memo = await self._memo_generator.execute(
            plan,
            regime="normal",
            stability=1.0,
            intent=intent,
            role=role,
        )
        yield self._event(
            "final_memo",
            {
                "intent": memo.intent,
                "role": memo.role,
                "decision": memo.decision,
                "summary": memo.summary,
                "recommendation": memo.recommendation,
                "key_findings": memo.key_findings,
                "historical_context": memo.historical_context,
                "portfolio_impact": memo.portfolio_impact,
                "recommended_actions": memo.recommended_actions,
                "watch_items": memo.watch_items,
                "data_quality": memo.data_quality,
                "evidence_blocks": memo.evidence_blocks,
                "confidence_score": memo.confidence_band.score,
                "confidence_calibration": memo.confidence_band.calibration,
                "risk_band": memo.risk_band,
                "scenario_tree": memo.scenario_tree,
                "worst_case": memo.worst_case,
            },
        )

    @staticmethod
    def _event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
