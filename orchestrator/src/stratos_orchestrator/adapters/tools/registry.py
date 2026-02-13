"""Tool registry — discovers and dispatches to tool adapters.

All tools implement a uniform interface (Open/Closed: add new tools
by creating new modules, no modification of registry needed).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Individual tool that the agent can invoke."""

    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def parameters_schema(self) -> dict: ...

    async def execute(self, arguments: dict) -> dict: ...


class ToolRegistry:
    """Registry of available tools — implements ToolExecutor port."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}. Available: {list(self._tools.keys())}")
        return await self._tools[tool_name].execute(arguments)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]
