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


class OrchestrateUseCase:
    """Main orchestration: decompose query → execute tools → generate memo."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolExecutor,
        formatter: OutputFormatter,
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
        return await self._synthesize(query, results)

    async def _plan(self, query: str) -> ExecutionPlan:
        """Use LLM to decompose query into tool calls."""
        response = await self._llm.generate_structured(
            messages=[
                {"role": "system", "content": "Decompose this financial query into tool calls."},
                {"role": "user", "content": query},
            ],
            schema={"type": "object", "properties": {"tasks": {"type": "array"}}},
        )
        tasks = [
            AgentTask(tool_name=t.get("tool", ""), arguments=t.get("args", {}))
            for t in response.get("tasks", [])
        ]
        return ExecutionPlan(query=query, tasks=tasks)

    async def _synthesize(self, query: str, results: dict) -> StrategicMemo:
        """Use LLM to synthesize results into a strategic memo."""
        synthesis = await self._llm.generate(
            messages=[
                {"role": "system", "content": "Synthesize these tool results into a strategic memo."},
                {"role": "user", "content": f"Query: {query}\nResults: {results}"},
            ]
        )
        return StrategicMemo(
            query=query,
            recommendation=synthesis,
            confidence=ConfidenceBand.from_score(0.0),  # TODO: calibrate
            scenario_tree=[],
            worst_case="",
            risk_band="unknown",
        )
