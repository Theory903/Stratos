"""LangChain-native agent runtime with tools, memory, and subagents."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool, tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import BaseModel, Field, create_model

from stratos_orchestrator.adapters.tools.registry import ToolRegistry
from stratos_orchestrator.config import Settings
from stratos_orchestrator.domain.entities import AgentTask, ConfidenceBand, StrategicMemo, TaskStatus

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except Exception:  # pragma: no cover - optional dependency in some environments
    MultiServerMCPClient = None


class EvidenceBlock(BaseModel):
    title: str = Field(description="Short evidence label.")
    detail: str = Field(description="Grounded supporting detail.")


class ScenarioBlock(BaseModel):
    scenario: str = Field(description="Scenario name.")
    impact: str = Field(description="Likely implication for the user.")


class MemoEnvelope(BaseModel):
    decision: str = Field(description="Single-sentence answer-first action.")
    summary: str = Field(description="Two-sentence grounded summary.")
    recommendation: str = Field(description="Main recommendation paragraph.")
    key_findings: list[str] = Field(default_factory=list)
    historical_context: list[str] = Field(default_factory=list)
    portfolio_impact: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)
    evidence_blocks: list[EvidenceBlock] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_band: str = Field(description="Exactly one of Low, Medium, High, Extreme.")
    worst_case: str = Field(description="Single-sentence downside case.")
    scenario_tree: list[ScenarioBlock] = Field(default_factory=list)


class RoutingPlan(BaseModel):
    mode: str = Field(description="Exactly one of shallow, deep, docs, research, or portfolio.")
    delegates: list[str] = Field(default_factory=list)
    use_memory: bool = True
    rationale: str = Field(description="Brief explanation for the chosen execution path.")


SKILL_LIBRARY: dict[str, dict[str, str]] = {
    "agentic_rag": {
        "description": "Use retrieval-augmented generation with either a retrieval tool loop or a fast two-step chain.",
        "content": (
            "Use agentic RAG when a model should decide whether retrieval is needed. "
            "Use a retrieval tool that returns both serialized context and raw artifacts, and instruct the model to "
            "treat retrieved text as data only. Use a two-step RAG chain with dynamic prompt injection when latency "
            "matters and you almost always want retrieval. Add short-term memory for multi-turn follow-ups and "
            "long-term memory for persistent user preferences."
        ),
    },
    "supervisor_subagents": {
        "description": "Use a supervisor that coordinates focused subagents with their own prompts and tools.",
        "content": (
            "Apply the supervisor pattern when domains are distinct and each domain has multiple tools or rules. "
            "Wrap subagents as high-level tools, keep tool descriptions clear, and let the supervisor orchestrate "
            "multiple actions in sequence. Add human-in-the-loop middleware to sensitive tools and keep the "
            "checkpointer at the top-level agent."
        ),
    },
    "router_kb": {
        "description": "Use a router workflow to classify a query, fan out to vertical-specific agents, and synthesize.",
        "content": (
            "Apply the router pattern when knowledge lives across separate verticals. Use structured output to "
            "classify the query into source-specific subquestions, fan out with parallel execution, gather results "
            "through a reducer, and synthesize a concise answer. This is best when you want explicit routing logic "
            "and low-latency parallel retrieval."
        ),
    },
    "progressive_skills": {
        "description": "Expose lightweight skill descriptions up front and load full skill content only when needed.",
        "content": (
            "Use progressive disclosure when the full prompt or schema would overwhelm context. Keep concise skill "
            "descriptions in the system prompt and add a load_skill tool that reveals detailed instructions, schemas, "
            "or business logic on demand. This pattern works well for SQL assistants, workflow playbooks, and other "
            "large policy surfaces."
        ),
    },
    "deep_agents": {
        "description": "Use deep agents when tasks need planning, files, code execution, artifacts, and subagents.",
        "content": (
            "Use Deep Agents for complex, long-running tasks like coding, data analysis, artifact generation, and "
            "sandboxed execution. Favor a backend with isolation, stream progress to the UI, and use subagents to "
            "keep context clean. Pair deep agents with memory, checkpointers, and optional MCP tools for real-world "
            "tool access."
        ),
    },
    "memory_and_hil": {
        "description": "Combine short-term memory, long-term memory, and human review for durable workflows.",
        "content": (
            "Use short-term memory through thread-scoped checkpoints for conversational continuity, and store "
            "cross-thread facts in long-term memory namespaces. Add human-in-the-loop review to sensitive tools like "
            "email, deployment, or external side effects. Resume from interrupts with explicit approvals, edits, or "
            "rejections."
        ),
    },
}


@dataclass
class AgentContext:
    user_id: str
    thread_id: str


def _classify_intent(query: str) -> str:
    lowered = query.lower()
    if any(token in lowered for token in ("portfolio", "holding", "rebalance", "book", "position")):
        return "portfolio"
    if any(token in lowered for token in ("scenario", "what if", "shock", "oil", "inflation", "btc")):
        return "scenario"
    if any(token in lowered for token in ("policy", "regulation", "rbi", "fed")):
        return "policy"
    if any(token in lowered for token in ("valuation", "dcf", "multiple")):
        return "valuation"
    if any(token in lowered for token in ("macro", "country", "rates", "inflation")):
        return "macro"
    if "langchain" in lowered or "docs.langchain.com" in lowered:
        return "docs"
    return "research"


def _classify_role(query: str) -> str:
    lowered = query.lower()
    if "ceo" in lowered:
        return "ceo"
    if "cfo" in lowered or "treasury" in lowered:
        return "cfo"
    if "analyst" in lowered or "cfa" in lowered or "ca " in lowered:
        return "analyst"
    return "pm"


def _python_type_for_schema(spec: dict[str, Any]) -> type[Any]:
    expected = spec.get("type")
    if expected == "integer":
        return int
    if expected == "number":
        return float
    if expected == "boolean":
        return bool
    if expected == "array":
        return list
    if expected == "object":
        return dict
    return str


def _tool_summary(content: Any) -> str:
    if isinstance(content, str):
        return content[:500]
    if isinstance(content, list):
        flattened = " ".join(str(part) for part in content)
        return flattened[:500]
    return json.dumps(content, ensure_ascii=True)[:500]


def _message_text(message: BaseMessage) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "\n".join(parts)
    return str(content)


@lru_cache
def _langchain_docs_index_cache() -> str:
    response = httpx.get("https://docs.langchain.com/llms.txt", timeout=20.0)
    response.raise_for_status()
    return response.text[:50000]


def _filtered_docs_index(query: str, max_lines: int = 80) -> str:
    index_text = _langchain_docs_index_cache()
    lines = [line for line in index_text.splitlines() if line.strip()]
    if not query.strip():
        return "\n".join(lines[:max_lines])

    query_terms = {token for token in query.lower().split() if len(token) > 2}
    ranked: list[tuple[int, str]] = []
    for line in lines:
        lowered = line.lower()
        score = sum(1 for term in query_terms if term in lowered)
        if score > 0:
            ranked.append((score, line))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [line for _, line in ranked[:max_lines]]
    if not selected:
        selected = lines[:max_lines]
    return "\n".join(selected)


class LangChainAgentRuntime:
    """Stateful LangChain agent runtime with short-term and long-term memory."""

    def __init__(self, *, settings: Settings, tools: ToolRegistry) -> None:
        self._settings = settings
        self._tools = tools
        self._checkpointer = InMemorySaver()
        self._store = InMemoryStore()
        self._agent = None
        self._docs_agent = None
        self._research_agent = None
        self._portfolio_agent = None
        self._skill_agent = None
        self._memo_model = None
        self._init_lock = asyncio.Lock()

    async def execute(self, query: str, *, thread_id: str, user_id: str) -> StrategicMemo:
        intent = _classify_intent(query)
        role = _classify_role(query)
        try:
            agent = await self._ensure_agent()
            routing_plan = await self._plan_routing(query=query, intent=intent, role=role)
            memory_context = self._recall_memories(user_id=user_id, query=query) if routing_plan.use_memory else ""
            input_text = query.strip()
            if memory_context:
                input_text += "\n\nRelevant stored context:\n" + memory_context

            runner = self._select_runner(intent=intent, routing_plan=routing_plan, default_runner=agent)
            result = await asyncio.wait_for(
                self._invoke_runner(
                    runner=runner,
                    query=input_text,
                    routing_plan=routing_plan,
                    thread_id=thread_id,
                    user_id=user_id,
                ),
                timeout=45,
            )
            messages = result.get("messages", [])
            memo = await self._synthesize_memo(
                query=query,
                intent=intent,
                role=role,
                messages=messages,
                memory_context=memory_context,
            )
            tasks = self._extract_tasks(messages)
            strategic_memo = StrategicMemo(
                query=query,
                plan_summary=self._plan_summary(tasks),
                tasks=tasks,
                confidence_band=ConfidenceBand.from_score(memo.confidence_score),
                risk_policy_status="PASS",
                recommendation=memo.recommendation,
                worst_case=memo.worst_case,
                risk_band=memo.risk_band,
                system_regime="normal",
                regime_stability=1.0,
                scenario_tree=[item.model_dump() for item in memo.scenario_tree],
                intent=intent,
                role=role,
                decision=memo.decision,
                summary=memo.summary,
                key_findings=memo.key_findings,
                historical_context=memo.historical_context,
                portfolio_impact=memo.portfolio_impact,
                recommended_actions=memo.recommended_actions,
                watch_items=memo.watch_items,
                data_quality=memo.data_quality,
                evidence_blocks=[item.model_dump() for item in memo.evidence_blocks],
            )
            await self._store_memory(user_id=user_id, thread_id=thread_id, query=query, memo=strategic_memo)
            return strategic_memo
        except Exception as exc:
            return self._fallback_memo(query=query, intent=intent, role=role, error=str(exc))

    async def stream(self, query: str, *, thread_id: str, user_id: str):
        intent = _classify_intent(query)
        role = _classify_role(query)
        yield self._event("status", "Building LangChain execution context...")
        yield self._event("context", {"intent": intent, "role": role, "thread_id": thread_id})
        await self._ensure_agent()
        routing_plan = await self._plan_routing(query=query, intent=intent, role=role)
        yield self._event(
            "strategy",
            {
                "mode": routing_plan.mode,
                "delegates": routing_plan.delegates,
                "use_memory": routing_plan.use_memory,
                "rationale": routing_plan.rationale,
            },
        )
        memo = await self.execute(query, thread_id=thread_id, user_id=user_id)
        yield self._event(
            "plan",
            [{"tool_name": task.tool_name, "arguments": task.arguments} for task in memo.tasks],
        )
        for task in memo.tasks:
            payload = {"tool": task.tool_name, "status": "success" if task.status == TaskStatus.COMPLETED else "failed"}
            if task.status == TaskStatus.COMPLETED:
                payload["result_summary"] = _tool_summary(task.result)
            else:
                payload["error"] = task.error
            yield self._event("task_result", payload)
        yield self._event(
            "final_memo",
            {
                "intent": memo.intent,
                "role": memo.role,
                "decision": memo.decision,
                "summary": memo.summary,
                "recommendation": memo.recommendation,
                "key_findings": memo.key_findings,
                "historical_context": memo.historical_context,
                "portfolio_impact": memo.portfolio_impact,
                "recommended_actions": memo.recommended_actions,
                "watch_items": memo.watch_items,
                "data_quality": memo.data_quality,
                "evidence_blocks": memo.evidence_blocks,
                "confidence_score": memo.confidence_band.score,
                "confidence_calibration": memo.confidence_band.calibration,
                "risk_band": memo.risk_band,
                "scenario_tree": memo.scenario_tree,
                "worst_case": memo.worst_case,
            },
        )

    async def _ensure_agent(self):
        if self._agent is not None:
            return self._agent
        async with self._init_lock:
            if self._agent is not None:
                return self._agent

            model = self._build_model()
            self._memo_model = model

            direct_tools = self._build_registry_tools()
            docs_tools = self._build_docs_tools()
            skill_tools = self._build_skill_tools()
            mcp_tools = await self._load_mcp_tools()

            research_agent = create_agent(
                model=model,
                tools=direct_tools["research"],
                system_prompt=(
                    "You are the STRATOS research subagent. Use tools aggressively for current facts, "
                    "web lookups, market events, company context, and macro research."
                ),
                name="research_assistant",
                checkpointer=self._checkpointer,
                store=self._store,
                context_schema=AgentContext,
            )
            docs_agent = create_agent(
                model=model,
                tools=docs_tools,
                system_prompt=(
                    "You are the STRATOS docs subagent. For LangChain questions, first inspect a filtered docs index "
                    "slice from llms.txt relevant to the question, then search or read specific docs pages before answering."
                ),
                name="docs_assistant",
                checkpointer=self._checkpointer,
                store=self._store,
                context_schema=AgentContext,
            )
            portfolio_agent = create_agent(
                model=model,
                tools=direct_tools["portfolio"],
                system_prompt=(
                    "You are the STRATOS portfolio subagent. Use portfolio, regime, history, company, "
                    "and calculator tools to answer exposure, scenario, sizing, and allocation questions."
                ),
                name="portfolio_assistant",
                checkpointer=self._checkpointer,
                store=self._store,
                context_schema=AgentContext,
            )
            skill_agent = create_agent(
                model=model,
                tools=skill_tools,
                system_prompt=(
                    "You are the STRATOS architecture skill assistant. Help with LangChain and LangGraph patterns "
                    "such as RAG, supervisor subagents, router workflows, progressive skills, deep agents, memory, "
                    "and human-in-the-loop. Load skills before answering when implementation guidance is needed."
                ),
                name="skill_assistant",
                checkpointer=self._checkpointer,
                store=self._store,
                context_schema=AgentContext,
            )

            @tool
            async def docs_assistant(question: str) -> str:
                """Answer LangChain documentation questions using the official docs site and llms.txt index."""
                sub_result = await docs_agent.ainvoke(
                    {"messages": [{"role": "user", "content": question}]},
                )
                return self._final_text(sub_result.get("messages", []))

            @tool
            async def research_assistant(question: str) -> str:
                """Research current facts, external docs, macro context, and company information."""
                sub_result = await research_agent.ainvoke(
                    {"messages": [{"role": "user", "content": question}]},
                )
                return self._final_text(sub_result.get("messages", []))

            @tool
            async def portfolio_assistant(question: str) -> str:
                """Analyze portfolio risk, scenarios, exposures, and implementation actions."""
                sub_result = await portfolio_agent.ainvoke(
                    {"messages": [{"role": "user", "content": question}]},
                )
                return self._final_text(sub_result.get("messages", []))

            @tool
            def recall_memory(query: str, user_id: str = "anonymous") -> str:
                """Recall prior STRATOS conclusions or user preferences from long-term memory."""
                return self._recall_memories(user_id=user_id, query=query)

            @tool
            async def skill_assistant(question: str) -> str:
                """Load architectural patterns and implementation skills for RAG, multi-agent systems, and deep agents."""
                sub_result = await skill_agent.ainvoke(
                    {"messages": [{"role": "user", "content": question}]},
                )
                return self._final_text(sub_result.get("messages", []))

            all_tools = [docs_assistant, research_assistant, portfolio_assistant, skill_assistant, recall_memory, *mcp_tools]
            self._docs_agent = docs_agent
            self._research_agent = research_agent
            self._portfolio_agent = portfolio_agent
            self._skill_agent = skill_agent
            self._agent = create_agent(
                model=model,
                tools=all_tools,
                system_prompt=(
                    "You are STRATOS, a senior investment operator. Use tools whenever the request depends on "
                    "latest information, documentation details, calculations, prior context, or portfolio state. "
                    "Route LangChain documentation questions to docs_assistant. "
                    "Route research and docs work to research_assistant. Route holdings, sizing, and scenario work "
                    "to portfolio_assistant. Route architecture, RAG, multi-agent, LangGraph, memory, MCP, and "
                    "deep-agent implementation work to skill_assistant. Prefer grounded tool outputs over unsupported model guesses."
                ),
                name="stratos_supervisor",
                checkpointer=self._checkpointer,
                store=self._store,
                context_schema=AgentContext,
            )
        return self._agent

    async def _plan_routing(self, *, query: str, intent: str, role: str) -> RoutingPlan:
        model = self._memo_model or self._build_model()
        heuristic_mode = self._heuristic_route(intent=intent, query=query)
        try:
            planner = model.with_structured_output(RoutingPlan)
            plan = await planner.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Choose the cheapest execution path that will still be accurate. "
                            "Use shallow for simple reasoning that does not need tools or latest facts. "
                            "Use docs for LangChain documentation questions. "
                            "Use research for current facts, external information, or broad investigation. "
                            "Use portfolio for holdings, allocation, risk, and scenario questions. "
                            "Use deep only when the query spans multiple specialties or requires coordinator synthesis."
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"Intent: {intent}\nRole: {role}\nHeuristic default: {heuristic_mode}\n"
                            f"User query: {query}"
                        )
                    ),
                ]
            )
            if isinstance(plan, RoutingPlan):
                return plan
            if hasattr(plan, "model_dump"):
                return RoutingPlan.model_validate(plan.model_dump())
            return RoutingPlan.model_validate(plan)
        except Exception:
            return RoutingPlan(
                mode=heuristic_mode,
                delegates=[heuristic_mode],
                use_memory=True,
                rationale="Fallback heuristic routing was used.",
            )

    def _heuristic_route(self, *, intent: str, query: str) -> str:
        lowered = query.lower()
        if intent == "docs":
            return "docs"
        if intent == "portfolio":
            return "portfolio"
        if any(token in lowered for token in ("latest", "today", "current", "news", "price", "yield")):
            return "research"
        if any(token in lowered for token in ("compare", "tradeoff", "workflow", "architecture", "design", "multi agent", "subagent", "router", "rag", "deep agent", "langgraph", "skill")):
            return "deep"
        if len(query.split()) <= 12 and "?" in query:
            return "shallow"
        return "research"

    def _select_runner(self, *, intent: str, routing_plan: RoutingPlan, default_runner: Any):
        mode = routing_plan.mode or self._heuristic_route(intent=intent, query="")
        if mode == "docs" and self._docs_agent is not None:
            return self._docs_agent
        if mode == "portfolio" and self._portfolio_agent is not None:
            return self._portfolio_agent
        if mode == "research" and self._research_agent is not None:
            return self._research_agent
        if mode == "deep":
            return "deep"
        if mode == "shallow":
            return "shallow"
        return default_runner

    async def _invoke_runner(
        self,
        *,
        runner: Any,
        query: str,
        routing_plan: RoutingPlan,
        thread_id: str,
        user_id: str,
    ) -> dict[str, list[BaseMessage]]:
        if runner == "shallow":
            return await self._invoke_shallow(query=query, thread_id=thread_id, user_id=user_id)
        if runner == "deep":
            return await self._invoke_deep(
                query=query,
                routing_plan=routing_plan,
                thread_id=thread_id,
                user_id=user_id,
            )
        result = await runner.ainvoke(
            {"messages": [{"role": "user", "content": query}]},
            context=AgentContext(user_id=user_id, thread_id=thread_id),
            config={
                "configurable": {"thread_id": thread_id},
                "metadata": {
                    "routing_mode": routing_plan.mode,
                    "delegates": routing_plan.delegates,
                },
            },
        )
        return result

    async def _invoke_shallow(self, *, query: str, thread_id: str, user_id: str) -> dict[str, list[BaseMessage]]:
        model = self._memo_model or self._build_model()
        response = await model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "You are STRATOS in shallow mode. Answer directly and concisely. "
                        "If the question requires current facts, tools, or external verification, say that clearly."
                    )
                ),
                HumanMessage(content=query),
            ],
            config={"metadata": {"routing_mode": "shallow", "thread_id": thread_id, "user_id": user_id}},
        )
        return {"messages": [HumanMessage(content=query), response]}

    async def _invoke_deep(
        self,
        *,
        query: str,
        routing_plan: RoutingPlan,
        thread_id: str,
        user_id: str,
    ) -> dict[str, list[BaseMessage]]:
        delegates = routing_plan.delegates or self._default_delegates(query)
        delegate_map = {
            "docs": self._docs_agent,
            "research": self._research_agent,
            "portfolio": self._portfolio_agent,
            "skills": self._skill_agent,
        }
        selected = [(name, delegate_map.get(name)) for name in delegates if delegate_map.get(name) is not None]
        if not selected:
            return await self._invoke_shallow(query=query, thread_id=thread_id, user_id=user_id)

        async def run_delegate(name: str, agent: Any) -> tuple[str, dict[str, Any]]:
            delegate_query = self._delegate_prompt(name=name, query=query)
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": delegate_query}]},
                context=AgentContext(user_id=user_id, thread_id=f"{thread_id}:{name}"),
                config={
                    "configurable": {"thread_id": f"{thread_id}:{name}"},
                    "metadata": {"routing_mode": "deep", "delegate": name},
                },
            )
            return name, result

        delegate_results = await asyncio.gather(*(run_delegate(name, agent) for name, agent in selected))
        synthesis_messages: list[BaseMessage] = [HumanMessage(content=query)]
        synthesis_blocks: list[str] = []

        for name, result in delegate_results:
            messages = result.get("messages", [])
            synthesis_messages.extend(messages)
            synthesis_blocks.append(f"{name.upper()}:\n{self._final_text(messages) or 'No final answer returned.'}")

        model = self._memo_model or self._build_model()
        synthesis = await model.ainvoke(
            [
                SystemMessage(
                    content=(
                        "You are STRATOS in deep coordination mode. Combine specialist outputs into one answer. "
                        "Keep the answer grounded, resolve overlap, and call out uncertainty or conflicts explicitly."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Original query:\n{query}\n\n"
                        "Specialist outputs:\n" + "\n\n".join(synthesis_blocks)
                    )
                ),
            ],
            config={"metadata": {"routing_mode": "deep", "delegates": delegates}},
        )
        synthesis_messages.append(synthesis)
        return {"messages": synthesis_messages}

    @staticmethod
    def _default_delegates(query: str) -> list[str]:
        lowered = query.lower()
        delegates: list[str] = ["skills"]
        if "langchain" in lowered or "langgraph" in lowered or "docs" in lowered:
            delegates.append("docs")
        if any(token in lowered for token in ("news", "current", "market", "macro", "company", "policy")):
            delegates.append("research")
        if any(token in lowered for token in ("portfolio", "allocation", "holding", "scenario", "risk")):
            delegates.append("portfolio")
        return list(dict.fromkeys(delegates))

    @staticmethod
    def _delegate_prompt(*, name: str, query: str) -> str:
        if name == "skills":
            return (
                "Use the available skills to extract the best implementation pattern for this request. "
                "Focus on architecture, tradeoffs, and LangChain/LangGraph primitives.\n\n"
                f"{query}"
            )
        return f"Focus on the {name} dimension of this request and return only the most relevant grounded output.\n\n{query}"

    def _build_model(self) -> BaseChatModel:
        provider = self._settings.llm_provider
        explicit_model = self._settings.langchain_agent_model
        if provider == "ollama":
            return ChatOllama(
                model=explicit_model or self._settings.ollama_model,
                base_url="http://host.docker.internal:11434",
                temperature=0.1,
            )
        if provider == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA

            return ChatNVIDIA(
                model=explicit_model or self._settings.nvidia_model,
                api_key=self._settings.nvidia_api_key,
                temperature=self._settings.nvidia_temperature,
                top_p=self._settings.nvidia_top_p,
                max_tokens=self._settings.nvidia_max_tokens,
                reasoning_budget=self._settings.nvidia_reasoning_budget,
                chat_template_kwargs={"enable_thinking": self._settings.nvidia_enable_thinking},
            )
        if provider == "groq":
            return ChatOpenAI(
                model=explicit_model or self._settings.groq_model,
                api_key=self._settings.groq_api_key,
                base_url=self._settings.groq_api_base,
                temperature=0.1,
                max_tokens=self._settings.langchain_agent_max_tokens,
            )
        return ChatOpenAI(
            model=explicit_model or self._settings.openai_model,
            api_key=self._settings.openai_api_key,
            temperature=0.1,
            max_tokens=self._settings.langchain_agent_max_tokens,
        )

    def _build_registry_tools(self) -> dict[str, list[StructuredTool]]:
        wrapped: dict[str, StructuredTool] = {}
        for tool_name in self._tools.list_tools():
            schema = self._tools.get_schema(tool_name)
            if schema is None:
                continue
            args_model = self._build_args_model(tool_name, schema["parameters"])

            async def _execute_tool(_tool_name: str = tool_name, **kwargs: Any) -> dict:
                return await self._tools.execute(_tool_name, kwargs)

            wrapped[tool_name] = StructuredTool.from_function(
                coroutine=_execute_tool,
                name=tool_name,
                description=schema["description"],
                args_schema=args_model,
            )

        research_names = [
            "web_search",
            "webpage_read",
            "calculator",
            "events_analyze",
            "history_analyze",
            "macro_analyze_country",
            "company_analyze",
            "policy_analyze",
            "industry_analyze_sector",
            "geopolitics_simulate",
            "regime_detect",
        ]
        portfolio_names = [
            "portfolio_analyze",
            "portfolio_allocate",
            "calculator",
            "company_analyze",
            "history_analyze",
            "regime_detect",
            "tax_optimize",
        ]
        return {
            "research": [wrapped[name] for name in research_names if name in wrapped],
            "portfolio": [wrapped[name] for name in portfolio_names if name in wrapped],
        }

    def _build_docs_tools(self) -> list:
        @tool
        def langchain_docs_index(query: str = "", max_lines: int = 80) -> str:
            """Fetch a filtered LangChain docs index slice from llms.txt before exploring docs further."""
            return _filtered_docs_index(query=query, max_lines=max_lines)

        @tool
        async def langchain_docs_search(query: str) -> str:
            """Search the public LangChain docs site for relevant Python documentation pages."""
            result = await self._tools.execute(
                "web_search",
                {"query": query, "site": "docs.langchain.com", "limit": 5},
            )
            return json.dumps(result, ensure_ascii=True)

        @tool
        async def langchain_docs_read(url: str, max_chars: int = 8000) -> str:
            """Read a LangChain documentation page and return a cleaned text extract."""
            result = await self._tools.execute(
                "webpage_read",
                {"url": url, "max_chars": max_chars},
            )
            return json.dumps(result, ensure_ascii=True)

        return [langchain_docs_index, langchain_docs_search, langchain_docs_read]

    def _build_skill_tools(self) -> list:
        @tool
        def list_skills(query: str = "") -> str:
            """List available architecture and implementation skills for LangChain, LangGraph, RAG, and deep agents."""
            query_terms = {token for token in query.lower().split() if len(token) > 2}
            items = []
            for name, skill in SKILL_LIBRARY.items():
                haystack = f"{name} {skill['description']} {skill['content']}".lower()
                score = sum(1 for term in query_terms if term in haystack)
                items.append((score, name, skill))
            items.sort(key=lambda item: item[0], reverse=True)
            selected = items[:4] if query_terms else items
            return "\n".join(f"- {name}: {skill['description']}" for _, name, skill in selected)

        @tool
        def load_skill(skill_name: str) -> str:
            """Load the full content of an implementation skill into context."""
            skill = SKILL_LIBRARY.get(skill_name)
            if skill is None:
                available = ", ".join(sorted(SKILL_LIBRARY))
                return f"Skill '{skill_name}' not found. Available skills: {available}"
            return f"Loaded skill: {skill_name}\n\n{skill['content']}"

        return [list_skills, load_skill]

    async def _load_mcp_tools(self) -> list:
        server_config = self._settings.mcp_server_config()
        if not server_config or MultiServerMCPClient is None:
            return []
        client = MultiServerMCPClient(server_config)
        try:
            return await client.get_tools()
        except Exception:
            return []

    def _build_args_model(self, tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
        required = set(schema.get("required", []))
        fields: dict[str, tuple[Any, Any]] = {}
        for field_name, spec in schema.get("properties", {}).items():
            py_type = _python_type_for_schema(spec)
            default = ... if field_name in required else spec.get("default", None)
            fields[field_name] = (
                py_type,
                Field(default=default, description=spec.get("description", "")),
            )
        return create_model(f"{tool_name.title().replace('_', '')}Args", **fields)

    async def _synthesize_memo(
        self,
        *,
        query: str,
        intent: str,
        role: str,
        messages: list[BaseMessage],
        memory_context: str,
    ) -> MemoEnvelope:
        transcript = []
        for message in messages:
            if isinstance(message, ToolMessage):
                transcript.append(f"Tool {message.name or 'tool'}: {_tool_summary(message.content)}")
            elif isinstance(message, AIMessage):
                if message.tool_calls:
                    transcript.append("Tool calls: " + json.dumps(message.tool_calls, ensure_ascii=True))
                elif _message_text(message).strip():
                    transcript.append("Assistant: " + _message_text(message))
            elif isinstance(message, HumanMessage):
                transcript.append("User: " + _message_text(message))

        prompt = [
            SystemMessage(
                content=(
                    f"You are STRATOS, producing a final memo for a {role.upper()} workflow with {intent} intent. "
                    "Use only the grounded transcript and tool outputs. Do not invent live prices, PnL, timing, "
                    "or unsupported metrics. If evidence is partial, state that and lower confidence."
                )
            ),
            HumanMessage(
                content=(
                    f"Original query:\n{query}\n\n"
                    f"Recalled memory:\n{memory_context or 'None'}\n\n"
                    "Agent transcript:\n" + "\n".join(transcript[-40:])
                )
            ),
        ]
        try:
            structured = self._memo_model.with_structured_output(MemoEnvelope)
            result = await structured.ainvoke(prompt)
            if isinstance(result, MemoEnvelope):
                return result
            if hasattr(result, "model_dump"):
                return MemoEnvelope.model_validate(result.model_dump())
            return MemoEnvelope.model_validate(result)
        except Exception:
            fallback = self._final_text(messages)
            return MemoEnvelope(
                decision=fallback[:160] or "Hold until better evidence is available.",
                summary=fallback[:320] or "The agent could not produce a fully structured grounded memo.",
                recommendation=fallback or "The LangChain agent returned an incomplete response.",
                key_findings=[],
                historical_context=[],
                portfolio_impact=[],
                recommended_actions=[],
                watch_items=[],
                data_quality=["Structured memo synthesis failed; using raw agent output fallback."],
                evidence_blocks=[],
                confidence_score=0.35,
                risk_band="Medium",
                worst_case="Acting on an incompletely structured answer may introduce avoidable error.",
                scenario_tree=[],
            )

    def _extract_tasks(self, messages: list[BaseMessage]) -> list[AgentTask]:
        tasks: list[AgentTask] = []
        pending_by_id: dict[str, AgentTask] = {}
        for message in messages:
            if isinstance(message, AIMessage):
                for tool_call in getattr(message, "tool_calls", []) or []:
                    task = AgentTask(
                        tool_name=str(tool_call.get("name", "unknown_tool")),
                        arguments=dict(tool_call.get("args", {})),
                        status=TaskStatus.EXECUTING,
                    )
                    tasks.append(task)
                    if tool_call.get("id"):
                        pending_by_id[str(tool_call["id"])] = task
            elif isinstance(message, ToolMessage):
                tool_call_id = getattr(message, "tool_call_id", None)
                task = pending_by_id.get(str(tool_call_id)) if tool_call_id is not None else None
                if task is None:
                    task = AgentTask(
                        tool_name=message.name or "tool",
                        arguments={},
                        status=TaskStatus.PENDING,
                    )
                    tasks.append(task)
                task.result = {"content": _message_text(message)}
                task.status = TaskStatus.COMPLETED
        for task in tasks:
            if task.status == TaskStatus.EXECUTING:
                task.status = TaskStatus.FAILED
                task.error = "Tool call did not return a matching ToolMessage."
        return tasks

    def _final_text(self, messages: list[BaseMessage]) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                text = _message_text(message).strip()
                if text:
                    return text
        return ""

    def _recall_memories(self, *, user_id: str, query: str, limit: int = 3) -> str:
        items = self._store.search(("memories", user_id), limit=20)
        query_terms = {token for token in query.lower().split() if len(token) > 2}

        def score(item) -> int:
            payload = item.value or {}
            haystack = " ".join(
                str(payload.get(key, "")) for key in ("query", "decision", "summary", "recommendation")
            ).lower()
            return sum(1 for term in query_terms if term in haystack)

        ranked = [item for item in items if score(item) > 0]
        ranked.sort(key=score, reverse=True)
        selected = ranked[:limit] or items[:1]
        lines = []
        for item in selected:
            payload = item.value or {}
            lines.append(
                f"- Query: {payload.get('query', '')}\n"
                f"  Decision: {payload.get('decision', '')}\n"
                f"  Summary: {payload.get('summary', '')}"
            )
        return "\n".join(lines)

    async def _store_memory(self, *, user_id: str, thread_id: str, query: str, memo: StrategicMemo) -> None:
        key = f"{thread_id}:{int(time.time())}"
        self._store.put(
            ("memories", user_id),
            key,
            {
                "query": query,
                "decision": memo.decision,
                "summary": memo.summary,
                "recommendation": memo.recommendation,
                "generated_at": memo.generated_at.isoformat(),
            },
        )

    @staticmethod
    def _plan_summary(tasks: list[AgentTask]) -> str:
        if not tasks:
            return "No tool calls were required."
        names = ", ".join(task.tool_name for task in tasks[:4])
        suffix = "" if len(tasks) <= 4 else f" and {len(tasks) - 4} more"
        return f"LangChain agent executed: {names}{suffix}."

    @staticmethod
    def _event(event_type: str, data: Any) -> str:
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    @staticmethod
    def _fallback_memo(*, query: str, intent: str, role: str, error: str) -> StrategicMemo:
        return StrategicMemo(
            query=query,
            plan_summary="LangChain runtime could not complete because the configured model backend was unavailable.",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(0.2),
            risk_policy_status="FAILED",
            recommendation=(
                "Reconnect the configured LLM backend or switch the orchestrator to a reachable OpenAI-compatible "
                "or Groq model before relying on the LangChain agent path."
            ),
            worst_case="The agent appears live in the UI but cannot ground answers because the model backend is unreachable.",
            risk_band="Low",
            system_regime="degraded",
            regime_stability=0.0,
            scenario_tree=[],
            intent=intent,
            role=role,
            decision="Do not trust the LangChain agent output until the model backend is reachable.",
            summary="The LangChain agent runtime is wired, but the active model provider did not respond successfully.",
            key_findings=[
                "The v3 LangChain route started and accepted the request.",
                "The model backend failed before the agent could complete tool-driven reasoning.",
                "This is an infrastructure/provider availability issue, not a docs/tool registry issue.",
            ],
            historical_context=[],
            portfolio_impact=[],
            recommended_actions=[
                "Start a reachable Ollama instance or switch to OpenAI/Groq in orchestrator settings.",
                "Retry the same thread after the model backend is healthy.",
            ],
            watch_items=[
                "Model endpoint reachability",
                "Ollama service health",
                "Configured provider credentials",
            ],
            data_quality=[
                "No final model reasoning was produced.",
                f"Provider error: {error[:240]}",
            ],
            evidence_blocks=[
                {
                    "title": "Runtime status",
                    "detail": "The request reached the LangChain v3 route, but model execution failed before memo synthesis.",
                }
            ],
        )
