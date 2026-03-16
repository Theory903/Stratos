"""Application Use Case: Plan Tasks.

Generates an execution plan from a user query.
"""

from __future__ import annotations

import json
from stratos_orchestrator.domain.entities import AgentTask, ExecutionPlan, TaskStatus
from stratos_orchestrator.domain.ports import LLMProvider, ToolExecutor


class PlanTasksUseCase:
    """Generate a plan of tasks to answer the query."""

    def __init__(self, llm: LLMProvider, tools: ToolExecutor) -> None:
        self.llm = llm
        self.tools = tools

    async def execute(self, query: str) -> ExecutionPlan:
        tool_schemas = self.tools.list_tools() if hasattr(self.tools, "list_tools") else []
        # Actually we need full schemas
        # We can cast tools to ToolRegistry or assume the port exposes schemas
        # The port in ports/__init__.py only has list_tools()->list[str]
        # But ToolRegistry has get_schemas().
        # Let's assume we can get schemas.
        # Ideally port should have get_tool_schemas()
        
        # For now, we'll prompt the LLM with available tools.
        # But wait, LLMProvider supports structured generation.
        
        # Simplified for now: We assume tools passed in are sufficient context?
        # No, LLM needs to know WHAT tools can do.
        # I need to update the Port or access the Registry directly via DI.
        # Given DI, if I inject ToolRegistry as ToolExecutor, I can call get_schemas().
        
        if hasattr(self.tools, "get_schemas"):
            schemas = self.tools.get_schemas()
        else:
            schemas = []

        system_prompt = (
            "You are a strategic financial planner. Your goal is to break down a user's complex "
            "financial query into a sequence of specific tool executions.\n"
            "Available Tools:\n" + json.dumps(schemas, indent=2) + "\n\n"
            "Output must be a JSON object complying with the schema: "
            "{'reasoning': str, 'tasks': [{'tool_name': str, 'arguments': dict}]}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        # Define output schema for strict JSON
        plan_schema = {
            "title": "ExecutionPlan",
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
            "required": ["reasoning", "tasks"],
        }

        try:
            result = await self.llm.generate_structured(messages, plan_schema)
            
            tasks = [
                AgentTask(
                    tool_name=t["tool_name"],
                    arguments=t["arguments"],
                    status=TaskStatus.PENDING
                )
                for t in result.get("tasks", [])
            ]
            
            return ExecutionPlan(
                query=query,
                reasoning=result.get("reasoning", ""),
                tasks=tasks
            )
        except Exception as e:
            # Fallback or error handling
            # Ideally log error
            return ExecutionPlan(query=query, reasoning=f"Failed to plan: {str(e)}")
