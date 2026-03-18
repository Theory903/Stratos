"""Orchestrator application layer — core agent logic."""

from __future__ import annotations

from stratos_orchestrator.domain.entities import (
    AgentTask,
    ConfidenceBand,
    ExecutionPlan,
    StrategicMemo,
    TaskStatus,
)
from stratos_orchestrator.domain.ports import LLMProvider, OutputFormatter, ToolExecutor
from stratos_orchestrator.application.langchain_v3 import LangChainAgentRuntime
from stratos_orchestrator.application.finance_council import FinanceCouncilRuntime
from stratos_orchestrator.application.v4_graph import V4GraphRuntime
from stratos_orchestrator.application.v5_runtime import V5GraphRuntime
from stratos_orchestrator.application.v2 import V2OrchestrateUseCase, V2StreamOrchestrateUseCase


class OrchestrateUseCase:
    """Main orchestration: decompose query → execute tools → generate memo."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolExecutor,
        formatter: OutputFormatter | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._formatter = formatter

    async def execute(self, query: str) -> StrategicMemo:
        # Step 1: Plan
        plan = await self._plan(query)

        # Step 2: Execute each task
        for task in plan.tasks:
            task.status = TaskStatus.EXECUTING
            try:
                task.result = await self._tools.execute(task.tool_name, task.arguments)
                task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.error = str(e)
                task.status = TaskStatus.FAILED

        # Step 3: Synthesize into memo
        results = {t.tool_name: t.result for t in plan.tasks if t.result}
        return await self._synthesize(plan, results)

    async def _plan(self, query: str) -> ExecutionPlan:
        """Use LLM to decompose query into tool calls."""
        response = await self._llm.generate_structured(
            messages=[
                {"role": "system", "content": "Decompose this financial query into tool calls."},
                {"role": "user", "content": query},
            ],
            schema={
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string"},
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool_name": {"type": "string"},
                                "arguments": {"type": "object"},
                            },
                            "required": ["tool_name", "arguments"],
                        },
                    },
                },
                "required": ["tasks"],
            },
        )
        tasks = [
            AgentTask(
                tool_name=t.get("tool_name") or t.get("tool", ""),
                arguments=t.get("arguments") or t.get("args", {}),
            )
            for t in response.get("tasks", [])
        ]
        return ExecutionPlan(
            query=query,
            tasks=tasks,
            reasoning=response.get("reasoning", ""),
        )

    async def _synthesize(self, plan: ExecutionPlan, results: dict) -> StrategicMemo:
        """Use LLM to synthesize results into a strategic memo."""
        synthesis = await self._llm.generate(
            messages=[
                {"role": "system", "content": "Synthesize these tool results into a strategic memo."},
                {"role": "user", "content": f"Query: {plan.query}\nResults: {results}"},
            ]
        )
        return StrategicMemo(
            query=plan.query,
            plan_summary=plan.reasoning or "Task summary pending.",
            tasks=plan.tasks,
            recommendation=synthesis,
            confidence_band=ConfidenceBand.from_score(0.0),  # TODO: calibrate
            risk_policy_status="PASS",
            scenario_tree=[],
            worst_case="",
            risk_band="unknown",
        )


__all__ = [
    "FinanceCouncilRuntime",
    "LangChainAgentRuntime",
    "V4GraphRuntime",
    "V5GraphRuntime",
    "OrchestrateUseCase",
    "V2OrchestrateUseCase",
    "V2StreamOrchestrateUseCase",
]
