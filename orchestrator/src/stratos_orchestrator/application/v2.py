"""Guardrailed V2 orchestration use cases."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from stratos_orchestrator.application.execute_tool import ExecuteToolUseCase
from stratos_orchestrator.application.generate_memo import GenerateMemoUseCase
from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.domain.entities import AgentTask, ExecutionPlan, StrategicMemo, TaskStatus


def _normalize_arguments(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"))


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
        plan = self._guardrails.apply(await self._planner.execute(query))
        for task in plan.tasks:
            await self._executor.execute(task, vix=20.0, correlation=0.5, stability=1.0)
        return await self._memo_generator.execute(plan, regime="normal", stability=1.0)


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
        yield self._event("status", "Planning execution strategy...")
        plan = self._guardrails.apply(await self._planner.execute(query))
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
        memo = await self._memo_generator.execute(plan, regime="normal", stability=1.0)
        yield self._event(
            "final_memo",
            {
                "recommendation": memo.recommendation,
                "confidence_score": memo.confidence_band.score,
                "risk_band": memo.risk_band,
                "scenario_tree": memo.scenario_tree,
                "worst_case": memo.worst_case,
            },
        )

    @staticmethod
    def _event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
