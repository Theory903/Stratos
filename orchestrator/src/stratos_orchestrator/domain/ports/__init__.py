"""Orchestrator domain ports — abstract interfaces for LLM and tooling.

The orchestrator core NEVER knows concrete LLM providers or tool implementations.
Everything is injected via these protocols (Dependency Inversion).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract LLM provider — swap OpenAI/Anthropic/local without touching orchestrator."""

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...
    async def generate_structured(
        self, messages: list[dict[str, str]], schema: dict, **kwargs: Any
    ) -> dict: ...


@runtime_checkable
class ToolExecutor(Protocol):
    """Execute a tool by name with arguments."""

    async def execute(self, tool_name: str, arguments: dict) -> dict: ...
    def list_tools(self) -> list[str]: ...


@runtime_checkable
class AgentMemory(Protocol):
    """Agent memory — short-term (conversation) or long-term (RAG)."""

    async def store(self, key: str, content: str, metadata: dict | None = None) -> None: ...
    async def recall(self, query: str, limit: int = 5) -> list[dict]: ...


@runtime_checkable
class OutputFormatter(Protocol):
    """Format agent output into structured memos."""

    def format(self, raw_output: dict) -> str: ...
