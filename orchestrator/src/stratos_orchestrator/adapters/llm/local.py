"""Local LLM provider (Ollama)."""

from __future__ import annotations

from typing import Any

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from stratos_orchestrator.domain.ports import LLMProvider


class LocalProvider:
    """Local Adapter using Ollama (e.g., Llama 3, Mistral)."""

    def __init__(self, model: str = "llama3", temperature: float = 0.0, base_url: str = "http://localhost:11434") -> None:
        self.model_name = model
        self.temperature = temperature
        self.base_url = base_url
        self._client = None

    def _load(self) -> None:
        if self._client is None:
            self._client = ChatOllama(
                model=self.model_name,
                temperature=self.temperature,
                base_url=self.base_url,
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
        # Ollama supports JSON mode, but LangChain's with_structured_output support varies.
        # Fallback to prompting or standard JSON mode if needed.
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
