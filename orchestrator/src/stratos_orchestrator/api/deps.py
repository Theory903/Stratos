"""Dependency injection wiring."""

from __future__ import annotations

from functools import lru_cache

from stratos_orchestrator.adapters.llm.ollama import OllamaProvider
from stratos_orchestrator.adapters.llm.openai import OpenAIProvider
from stratos_orchestrator.adapters.tools.registry import ToolRegistry, get_registry
from stratos_orchestrator.application import LangChainAgentRuntime, OrchestrateUseCase, V2OrchestrateUseCase, V2StreamOrchestrateUseCase
from stratos_orchestrator.application.execute_tool import ExecuteToolUseCase
from stratos_orchestrator.application.generate_memo import GenerateMemoUseCase
from stratos_orchestrator.application.plan_tasks import PlanTasksUseCase
from stratos_orchestrator.application.stream_orchestrate import StreamOrchestrateUseCase
from stratos_orchestrator.config import Settings
from stratos_orchestrator.domain.ports import LLMProvider


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()

    if settings.llm_provider == "ollama":
        return OllamaProvider(model=settings.ollama_model)
    if settings.llm_provider == "nvidia":
        from stratos_orchestrator.adapters.llm.nvidia import NVIDIAProvider

        return NVIDIAProvider(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            temperature=settings.nvidia_temperature,
            top_p=settings.nvidia_top_p,
            max_tokens=settings.nvidia_max_tokens,
            reasoning_budget=settings.nvidia_reasoning_budget,
            enable_thinking=settings.nvidia_enable_thinking,
        )
    if settings.llm_provider == "groq":
        return OpenAIProvider(
            model=settings.groq_model,
            temperature=0.1,
            api_key=settings.groq_api_key,
            api_base=settings.groq_api_base,
        )
    return OpenAIProvider(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    )


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return get_registry()


@lru_cache
def get_tool_registry_v2() -> ToolRegistry:
    settings = get_settings()
    return get_registry(settings.data_fabric_v2_url)


def get_plan_tasks_use_case() -> PlanTasksUseCase:
    return PlanTasksUseCase(llm=get_llm_provider(), tools=get_tool_registry())


def get_execute_tool_use_case() -> ExecuteToolUseCase:
    return ExecuteToolUseCase(executor=get_tool_registry())


def get_generate_memo_use_case() -> GenerateMemoUseCase:
    return GenerateMemoUseCase(llm=get_llm_provider())


def get_orchestrate_use_case() -> OrchestrateUseCase:
    return OrchestrateUseCase(llm=get_llm_provider(), tools=get_tool_registry())


def get_stream_orchestrate_use_case() -> StreamOrchestrateUseCase:
    return StreamOrchestrateUseCase(
        planner=get_plan_tasks_use_case(),
        executor=get_execute_tool_use_case(),
        memo_generator=get_generate_memo_use_case(),
    )


def get_v2_orchestrate_use_case() -> V2OrchestrateUseCase:
    settings = get_settings()
    tools = get_tool_registry_v2()
    return V2OrchestrateUseCase(
        planner=PlanTasksUseCase(llm=get_llm_provider(), tools=tools),
        executor=ExecuteToolUseCase(executor=tools),
        memo_generator=get_generate_memo_use_case(),
        tools=tools,
        max_budget=settings.max_tool_budget,
    )


def get_v2_stream_orchestrate_use_case() -> V2StreamOrchestrateUseCase:
    settings = get_settings()
    tools = get_tool_registry_v2()
    return V2StreamOrchestrateUseCase(
        planner=PlanTasksUseCase(llm=get_llm_provider(), tools=tools),
        executor=ExecuteToolUseCase(executor=tools),
        memo_generator=get_generate_memo_use_case(),
        tools=tools,
        max_budget=settings.max_tool_budget,
    )


@lru_cache
def get_langchain_agent_runtime() -> LangChainAgentRuntime:
    return LangChainAgentRuntime(
        settings=get_settings(),
        tools=get_tool_registry_v2(),
    )
