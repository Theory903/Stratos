"""NVIDIA NIM / AI Endpoints LLM provider."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from stratos_orchestrator.domain.ports import LLMProvider


class NVIDIAProvider(LLMProvider):
    """LangChain adapter for NVIDIA chat endpoints."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        temperature: float,
        top_p: float,
        max_tokens: int,
        reasoning_budget: int,
        enable_thinking: bool,
    ) -> None:
        self._client = ChatNVIDIA(
            model=model,
            api_key=api_key,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            reasoning_budget=reasoning_budget,
            chat_template_kwargs={"enable_thinking": enable_thinking},
        )

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        response = await self._client.ainvoke(self._convert_messages(messages), **kwargs)
        return str(response.content)

    async def generate_structured(
        self, messages: list[dict[str, str]], schema: dict, **kwargs: Any
    ) -> dict:
        try:
            structured_llm = self._client.with_structured_output(schema)
            result = await structured_llm.ainvoke(self._convert_messages(messages), **kwargs)
            if isinstance(result, dict):
                return result
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return dict(result)
        except Exception:
            response = await self._client.ainvoke(
                self._convert_messages(
                    [
                        {
                            "role": "system",
                            "content": "Return only valid JSON matching this schema exactly:\n" + json.dumps(schema),
                        },
                        *messages,
                    ]
                ),
                **kwargs,
            )
            return json.loads(str(response.content))

    async def astream(self, messages: list[dict[str, str]], **kwargs: Any):
        async for chunk in self._client.astream(self._convert_messages(messages), **kwargs):
            reasoning = chunk.additional_kwargs.get("reasoning_content") if chunk.additional_kwargs else None
            if reasoning:
                yield reasoning
            if chunk.content:
                yield str(chunk.content)

    def _convert_messages(self, messages: list[dict[str, str]]) -> list[BaseMessage]:
        lc_messages: list[BaseMessage] = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
        return lc_messages
