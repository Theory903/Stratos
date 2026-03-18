"""Anthropic LLM provider."""

from __future__ import annotations

import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from stratos_orchestrator.domain.ports import LLMProvider


class AnthropicProvider:
    """Anthropic Adapter (Claude 3)."""

    def __init__(self, model: str = "claude-3-opus-20240229", temperature: float = 0.0) -> None:
        self.model_name = model
        self.temperature = temperature
        self._client = None

    def _load(self) -> None:
        if self._client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is required to use the Anthropic provider.")
            self._client = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                anthropic_api_key=api_key,
            )

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self._load()
        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
                
        response = await self._client.ainvoke(lc_messages, **kwargs)
        return str(response.content)

    async def generate_structured(
        self, messages: list[dict[str, str]], schema: dict, **kwargs: Any
    ) -> dict:
        self._load()
        structured_llm = self._client.with_structured_output(schema)
        
        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))

        return await structured_llm.ainvoke(lc_messages, **kwargs)
