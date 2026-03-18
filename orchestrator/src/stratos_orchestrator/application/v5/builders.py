"""V5 builders — model factory, middleware, and structured output helpers.

Extracted from ``langchain_v3.py`` so V5 nodes can use them without
coupling to the V3 runtime class.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from stratos_orchestrator.config import Settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------


def build_model(settings: Settings) -> BaseChatModel:
    """Multi-provider model factory.

    Priority chain: explicit provider → NVIDIA → Groq → Ollama → OpenAI.
    """
    provider = settings.llm_provider
    explicit_model = settings.langchain_agent_model

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=explicit_model or settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    if provider == "nvidia":
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA  # type: ignore[import-untyped]

            return ChatNVIDIA(
                model=explicit_model or settings.nvidia_model,
                api_key=settings.nvidia_api_key,
                temperature=settings.nvidia_temperature,
                top_p=settings.nvidia_top_p,
                max_tokens=settings.nvidia_max_tokens,
                reasoning_budget=settings.nvidia_reasoning_budget,
                chat_template_kwargs={
                    "enable_thinking": settings.nvidia_enable_thinking,
                },
            )
        except Exception:
            logger.warning("NVIDIA provider failed, falling back")
            return _fallback_model(settings, explicit_model)

    if provider == "groq":
        return ChatOpenAI(
            model=explicit_model or settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_api_base,
            temperature=0.1,
            max_tokens=settings.langchain_agent_max_tokens,
        )

    # Default: OpenAI
    return ChatOpenAI(
        model=explicit_model or settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=settings.langchain_agent_max_tokens,
    )


def _fallback_model(settings: Settings, explicit_model: str | None) -> BaseChatModel:
    """Walk the fallback chain: Groq → Ollama → OpenAI."""
    if settings.groq_api_key:
        return ChatOpenAI(
            model=explicit_model or settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_api_base,
            temperature=0.1,
            max_tokens=settings.langchain_agent_max_tokens,
        )
    if settings.ollama_base_url:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )
    return ChatOpenAI(
        model=explicit_model or settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
        max_tokens=settings.langchain_agent_max_tokens,
    )


# ---------------------------------------------------------------------------
# Structured output helper
# ---------------------------------------------------------------------------


def build_structured_output(
    model: BaseChatModel,
    schema: type[T],
) -> Any:
    """Thin wrapper — returns a runnable that outputs ``schema``.

    Usage::

        planner = build_structured_output(model, SupervisorDecision)
        decision = await planner.ainvoke(messages)
    """
    return model.with_structured_output(schema)


# ---------------------------------------------------------------------------
# Middleware stack
# ---------------------------------------------------------------------------


def build_middleware(
    model: BaseChatModel,
    *,
    max_retries: int = 2,
    timeout_seconds: float = 30.0,
    call_ceiling: int = 50,
    fallback_model: BaseChatModel | None = None,
) -> BaseChatModel:
    """Wrap a model with retry, timeout, fallback, and call-count ceiling.

    Returns a new runnable chain that applies the middleware in order:
      1. Retry on transient errors
      2. Timeout
      3. Fallback model (if primary fails after retries)
    """
    chain = model.with_retry(
        stop_after_attempt=max_retries + 1,
    )

    if fallback_model is not None:
        chain = chain.with_fallbacks([fallback_model])

    return chain
