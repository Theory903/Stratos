"""Test V2 orchestration guardrails."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from stratos_orchestrator.application.execute_tool import ExecuteToolUseCase
from stratos_orchestrator.application.generate_memo import GenerateMemoUseCase
from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.application.v2 import GuardrailedPlan, V2OrchestrateUseCase
from stratos_orchestrator.domain.entities import AgentTask, ConfidenceBand, ExecutionPlan, StrategicMemo, TaskStatus


def test_guardrailed_plan_dedupes_and_validates() -> None:
    tools = MagicMock()
    tools.has_tool.side_effect = lambda name: name == "company_analyze"
    tools.get_schema.return_value = {
        "parameters": {
            "required": ["ticker"],
            "properties": {"ticker": {"type": "string"}},
        }
    }

    plan = ExecutionPlan(
        query="Analyze Apple",
        tasks=[
            AgentTask(tool_name="company_analyze", arguments={"ticker": "AAPL"}),
            AgentTask(tool_name="company_analyze", arguments={"ticker": "AAPL"}),
            AgentTask(tool_name="company_analyze", arguments={"ticker": 123}),
        ],
    )

    validated = GuardrailedPlan(tools, max_budget=8).apply(plan)
    assert len(validated.tasks) == 1
    assert validated.tasks[0].arguments == {"ticker": "AAPL"}


@pytest.mark.asyncio
async def test_v2_orchestrate_executes_only_valid_budgeted_tasks() -> None:
    planner = MagicMock(spec=PlanTasksUseCase)
    planner.execute = AsyncMock(
        return_value=ExecutionPlan(
            query="Analyze Apple",
            tasks=[
                AgentTask(tool_name="company_analyze", arguments={"ticker": "AAPL"}),
                AgentTask(tool_name="company_analyze", arguments={"ticker": "AAPL"}),
            ],
        )
    )

    executor = MagicMock(spec=ExecuteToolUseCase)

    async def execute_task(task, **_kwargs):
        task.status = TaskStatus.COMPLETED
        task.result = {"ticker": task.arguments["ticker"]}
        return task

    executor.execute = AsyncMock(side_effect=execute_task)

    memo_generator = MagicMock(spec=GenerateMemoUseCase)
    memo_generator.execute = AsyncMock(
        return_value=StrategicMemo(
            query="Analyze Apple",
            plan_summary="summary",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(0.7),
            risk_policy_status="PASS",
            recommendation="Hold",
            worst_case="Demand slows",
            risk_band="Medium",
            scenario_tree=[],
        )
    )

    tools = MagicMock()
    tools.has_tool.return_value = True
    tools.get_schema.return_value = {
        "parameters": {
            "required": ["ticker"],
            "properties": {"ticker": {"type": "string"}},
        }
    }

    use_case = V2OrchestrateUseCase(
        planner=planner,
        executor=executor,
        memo_generator=memo_generator,
        tools=tools,
        max_budget=8,
    )
    memo = await use_case.execute("Analyze Apple")

    assert memo.recommendation == "Hold"
    executor.execute.assert_awaited_once()
