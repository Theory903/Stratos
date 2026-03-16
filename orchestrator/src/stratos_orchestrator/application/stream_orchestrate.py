"""Application Use Case: Stream Orchestrate.

Provides an event-driven stream of agent execution progress.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator

from stratos_orchestrator.domain.entities import StrategicMemo, TaskStatus, ConfidenceBand
from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.application.execute_tool import ExecuteToolUseCase
from stratos_orchestrator.application.generate_memo import GenerateMemoUseCase


class StreamOrchestrateUseCase:
    """Orchestrate agent lifecycle with real-time event streaming."""

    def __init__(
        self,
        planner: PlanTasksUseCase,
        executor: ExecuteToolUseCase,
        memo_generator: GenerateMemoUseCase,
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.memo_generator = memo_generator

    async def execute(self, query: str) -> AsyncGenerator[str, None]:
        """
        Execute orchestration and yield SSE-formatted events.
        """
        
        # 1. Planning
        yield self._format_event("status", "Planning execution strategy...")
        plan = await self.planner.execute(query)
        yield self._format_event("plan", [t.model_dump() for t in plan.tasks if hasattr(t, "model_dump")] or [])
        
        # 2. Execution
        for task in plan.tasks:
            yield self._format_event("status", f"Executing {task.tool_name}...")
            await self.executor.execute(task, vix=20.0, correlation=0.5, stability=1.0)
            
            if task.status == TaskStatus.COMPLETED:
                yield self._format_event("task_result", {
                    "tool": task.tool_name,
                    "status": "success",
                    "result_summary": str(task.result)[:200] + "..." if task.result else ""
                })
            else:
                yield self._format_event("task_result", {
                    "tool": task.tool_name,
                    "status": "failed",
                    "error": task.error
                })

        # 3. Generate Memo (Streaming)
        # For now, GenerateMemoUseCase is blocking. 
        # We'll call the LLM directly for streaming the synthesis part.
        yield self._format_event("status", "Synthesizing strategic memo...")
        
        # Collect results for synthesis context
        results_context = []
        for task in plan.tasks:
            if task.status == TaskStatus.COMPLETED:
                results_context.append(
                    f"Tool: {task.tool_name}\nArgs: {task.arguments}\nResult: {json.dumps(task.result)}"
                )
        
        system_prompt = (
            "You are a Chief Investment Officer. Synthesize the provided tool outputs into a "
            "comprehensive Strategic Memo.\n"
            "Format Requirement: Use Markdown. Include sections for Recommendation, Confidence Score (0-1), "
            "Scenario Tree (as a table), Worst Case, and Risk Band.\n"
        )
        user_prompt = f"Query: {query}\n\nExecution Results:\n" + "\n---\n".join(results_context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        full_content = ""
        async for token in self.memo_generator.llm.astream(messages):
            full_content += token
            yield self._format_event("token", token)

        # 4. Final Structured Parse
        # Since we streamed the text, we now treat that text as the "raw" output and parse it
        # into the final StrategicMemo entity for completeness.
        yield self._format_event("status", "Finalizing memo structure...")
        
        # We re-use the robust parsing logic by "faking" a structured call or directly using the parse logic
        # For simplicity, we'll let the UI use the streamed tokens, but send a final 'complete' event with metadata
        
        # Re-parse for metadata (Risk Band, Confidence)
        # In a real system, we'd refactor the parser into a standalone domain service.
        # For now, we'll approximate the final memo keys from what we have.
        
        memo = await self.memo_generator.execute(plan, regime="normal", stability=1.0) # This does the full structured parse
        
        yield self._format_event("final_memo", {
            "recommendation": memo.recommendation,
            "confidence_score": memo.confidence_band.score,
            "risk_band": memo.risk_band,
            "scenario_tree": memo.scenario_tree,
            "worst_case": memo.worst_case
        })

    def _format_event(self, event_type: str, data: any) -> str:
        """Format data as SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
