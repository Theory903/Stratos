"""OpenAI-compatible LLM provider."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from stratos_orchestrator.domain.ports import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible adapter using LangChain."""

    def __init__(
        self,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.0,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        self.model_name = model
        self.temperature = temperature
        self.api_key = api_key
        self.api_base = api_base
        self._client = None

    def _load(self) -> None:
        if self._client is None:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is required to use the OpenAI provider.")

            client_kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
                "openai_api_key": api_key,
            }
            if self.api_base:
                client_kwargs["openai_api_base"] = self.api_base

            self._client = ChatOpenAI(**client_kwargs)

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate text response."""
        self._load()

        lc_messages = self._convert_messages(messages)
        response = await self._client.ainvoke(lc_messages, **kwargs)
        return str(response.content)

    async def generate_structured(
        self, messages: list[dict[str, str]], schema: dict, **kwargs: Any
    ) -> dict:
        """Generate structured output using function calling/json mode."""
        self._load()

        lc_messages = self._convert_messages(messages)

        try:
            structured_llm = self._client.with_structured_output(schema)
            result = await structured_llm.ainvoke(lc_messages, **kwargs)
            if isinstance(result, dict):
                return result
            if hasattr(result, "model_dump"):
                return result.model_dump()
            return dict(result)
        except Exception:
            fallback_prompt = {
                "role": "system",
                "content": (
                    "Return only valid JSON that matches this schema exactly:\n"
                    f"{json.dumps(schema)}"
                ),
            }
            json_llm = self._client.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke(
                self._convert_messages([fallback_prompt, *messages]),
                **kwargs,
            )
            content = self._strip_code_fences(str(response.content))
            return json.loads(content)

    async def astream(self, messages: list[dict[str, str]], **kwargs: Any):
        """Stream response token-by-token."""
        self._load()

        async for chunk in self._client.astream(self._convert_messages(messages), **kwargs):
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

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
