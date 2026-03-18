from __future__ import annotations

import json

import pytest

from stratos_orchestrator.adapters.tools.registry import ToolRegistry
from stratos_orchestrator.application.langchain_v3 import LangChainAgentRuntime
from stratos_orchestrator.application.persistence import SqliteRunCoordinator
from stratos_orchestrator.application.v4_graph import ResolvedEntities, V4GraphRuntime, V4InputItem
from stratos_orchestrator.config import Settings
from stratos_orchestrator.domain.entities import ConfidenceBand, StrategicMemo


class FakeTool:
    def __init__(self, name: str, result: dict) -> None:
        self._name = name
        self._result = result
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._name

    @property
    def parameters_schema(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, arguments: dict) -> dict:
        self.calls.append(arguments)
        return self._result


class DynamicCountryTool(FakeTool):
    def __init__(self, responses: dict[str, dict]) -> None:
        super().__init__("macro_analyze_country", {})
        self._responses = responses

    async def execute(self, arguments: dict) -> dict:
        self.calls.append(arguments)
        country_code = arguments["country_code"]
        return self._responses[country_code]


class ResolverStubRuntime(V4GraphRuntime):
    def __init__(
        self,
        *,
        settings: Settings,
        tools: ToolRegistry,
        resolutions: dict[str, ResolvedEntities] | None = None,
        general_runtime: LangChainAgentRuntime | None = None,
    ) -> None:
        super().__init__(settings=settings, tools=tools, general_runtime=general_runtime)
        self._resolutions = resolutions or {}

    async def _resolve_query_entities(self, query: str) -> ResolvedEntities:
        return self._resolutions.get(query, ResolvedEntities(confidence=0.0))


class FakeLangChainRuntime:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(self, query: str, *, thread_id: str, user_id: str) -> StrategicMemo:
        self.calls.append(query)
        return StrategicMemo(
            query=query,
            plan_summary="LangChain runtime handled the request.",
            tasks=[],
            confidence_band=ConfidenceBand.from_score(0.82),
            risk_policy_status="PASS",
            recommendation="Ask me about markets, documents, workflows, or portfolio scenarios and I will decide whether tools are needed.",
            worst_case="This reply is only as useful as the context provided.",
            risk_band="Low",
            intent="research",
            role="general",
            decision="Ready.",
            summary="I can answer directly when no tools are needed and call tools when the question depends on fresh or external context.",
            key_findings=[],
            historical_context=[],
            portfolio_impact=[],
            recommended_actions=["Try a market, portfolio, or research question next."],
            watch_items=[],
            data_quality=["No tool calls were needed for this conversational reply."],
            evidence_blocks=[],
        )

    async def stream(self, query: str, *, thread_id: str, user_id: str):
        memo = await self.execute(query, thread_id=thread_id, user_id=user_id)
        yield (
            'event: final_memo\ndata: '
            + json.dumps(
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
                }
            )
            + "\n\n"
        )


@pytest.fixture
def runtime(tmp_path) -> tuple[V4GraphRuntime, dict[str, FakeTool]]:
    registry = ToolRegistry()
    tools = {
        "portfolio_analyze": FakeTool("portfolio_analyze", {"positions": [{"ticker": "AAPL", "weight": 0.25}], "risk": "moderate"}),
        "company_analyze": FakeTool(
            "company_analyze",
            {
                "profile": {
                    "ticker": "AAPL",
                    "earnings_quality": 0.71,
                    "free_cash_flow_stability": 0.52,
                    "leverage_ratio": 0.77,
                    "fraud_score": 0.48,
                    "moat_score": 0.48,
                },
                "recent_market_data": [
                    {
                        "ticker": "AAPL",
                        "close": "250.12",
                        "timestamp": "2026-03-16T00:00:00+00:00",
                    }
                ],
            },
        ),
        "market_analyze": FakeTool(
            "market_analyze",
            {
                "ticker": "X:BTCUSD",
                "latest": {
                    "ticker": "X:BTCUSD",
                    "close": "72810.00",
                    "timestamp": "2026-03-17T00:00:00+00:00",
                },
                "bars": [],
            },
        ),
        "market_analyze_fx": FakeTool(
            "market_analyze",
            {
                "ticker": "FX:INRUSD",
                "latest": {
                    "ticker": "FX:INRUSD",
                    "close": "0.0121",
                    "timestamp": "2026-03-17T00:00:00+00:00",
                },
                "bars": [],
            },
        ),
        "market_analyze_eth": FakeTool(
            "market_analyze",
            {
                "ticker": "X:ETHUSD",
                "pending": True,
                "status": "pending",
                "suggested_retry_seconds": 30,
                "latest": None,
                "bars": [],
            },
        ),
        "company_news_analyze": FakeTool(
            "company_news_analyze",
            {
                "ticker": "AAPL",
                "items": [
                    {"title": "Apple suppliers signal steadier iPhone demand", "summary": "Checks improved versus prior month."},
                    {"title": "Apple expands buyback authorization", "summary": "Capital return remains a support."},
                ],
            },
        ),
        "policy_events_analyze": FakeTool(
            "policy_events_analyze",
            {
                "scope": "us",
                "items": [
                    {"title": "Fed speakers reiterate data-dependent path", "summary": "Cuts still depend on inflation progress."},
                ],
            },
        ),
        "macro_analyze_country": DynamicCountryTool(
            {
                "IND": {
                    "country": {
                        "country_code": "IND",
                        "debt_gdp": 82.1,
                        "fiscal_deficit": 5.4,
                        "political_stability": 0.62,
                        "currency_volatility": 0.34,
                    }
                },
                "USA": {
                    "country": {
                        "country_code": "USA",
                        "debt_gdp": 121.0,
                        "fiscal_deficit": 6.3,
                        "political_stability": 0.71,
                        "currency_volatility": 0.18,
                    }
                },
            }
        ),
        "macro_analyze_world": FakeTool("macro_analyze_world", {"world_state": {"inflation": 4.1, "oil": 82}}),
        "events_analyze": FakeTool(
            "events_analyze",
            {
                "pulse": {"headline": "Global event pulse remains mixed but not disorderly."},
                "clusters": [{"title": "Tariff noise"}, {"title": "AI capex"}],
            },
        ),
        "history_analyze": FakeTool(
            "history_analyze",
            {
                "analogs": [
                    {"label": "2024 soft landing wobble"},
                    {"label": "2025 duration scare"},
                ]
            },
        ),
        "regime_detect": FakeTool("regime_detect", {"regime": "sideways"}),
        "web_search": FakeTool(
            "web_search",
            {
                "results": [
                    {"title": "Reuters | Oil prices rise on supply concerns", "url": "https://www.reuters.com/markets/oil-prices-rise"},
                    {"title": "Bloomberg | Crude rises as inventories tighten", "url": "https://www.bloomberg.com/news/oil"},
                ]
            },
        ),
        "webpage_read": FakeTool(
            "webpage_read",
            {
                "url": "https://www.sec.gov/example",
                "title": "SEC filing",
                "content": "Form 10-K highlights demand softening and rising input cost pressure.",
            },
        ),
    }
    for key in (
        "portfolio_analyze",
        "company_analyze",
        "market_analyze",
        "company_news_analyze",
        "policy_events_analyze",
        "macro_analyze_country",
        "macro_analyze_world",
        "events_analyze",
        "history_analyze",
        "regime_detect",
        "web_search",
        "webpage_read",
    ):
        registry.register(tools[key])
    resolutions = {
        "price of bitcoin": ResolvedEntities(market_ticker="X:BTCUSD", confidence=0.96),
        "What should I watch in AAPL quality, event pulse, and regime history before adding risk?": ResolvedEntities(
            company_ticker="AAPL",
            event_scope="global",
            confidence=0.93,
        ),
        "How should I frame India sovereign risk versus US macro pressure this week?": ResolvedEntities(
            country_codes=["IND", "USA"],
            event_scope="global",
            confidence=0.9,
        ),
        "price of APPL": ResolvedEntities(company_ticker="AAPL", confidence=0.88),
        "latest AAPL news": ResolvedEntities(company_ticker="AAPL", confidence=0.94),
        "latest fed news today": ResolvedEntities(country_codes=["USA"], event_scope="us", confidence=0.9),
    }
    settings = Settings(runtime_persistence_dir=str(tmp_path / "runtime-state"), _env_file=())
    return ResolverStubRuntime(settings=settings, tools=registry, resolutions=resolutions), tools


@pytest.mark.asyncio
async def test_v4_prefers_internal_truth_for_portfolio_question(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="What is my portfolio risk right now?")],
        thread_id="thread:internal",
        user_id="user-1",
        workspace_id="workspace-1",
    )

    assert memo.intent == "portfolio"
    assert trace["answer_mode"] == "decision_with_limits"
    assert tools["web_search"].calls == []
    assert any(task.tool_name == "portfolio" for task in memo.tasks)


@pytest.mark.asyncio
async def test_v4_uses_web_search_for_simple_freshness_query(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="latest oil news today")],
        thread_id="thread:web",
        user_id="user-2",
        workspace_id="workspace-2",
    )

    assert tools["web_search"].calls
    assert trace["answer_mode"] in {"grounded_direct", "research_with_citations"}
    assert memo.evidence_blocks


@pytest.mark.asyncio
async def test_v4_downgrades_when_retrieval_is_too_weak(tmp_path) -> None:
    registry = ToolRegistry()
    web_search = FakeTool("web_search", {"results": []})
    webpage_read = FakeTool("webpage_read", {"url": "", "title": "", "content": ""})
    registry.register(web_search)
    registry.register(webpage_read)
    graph = V4GraphRuntime(settings=Settings(runtime_persistence_dir=str(tmp_path / "v4-weak")), tools=registry)

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="compare the latest filing risk for this company")],
        thread_id="thread:weak",
        user_id="user-3",
        workspace_id="workspace-3",
        response_mode_hint="memo",
    )

    assert trace["answer_mode"] == "insufficient_evidence"
    assert "evidence" in memo.recommendation.lower()


@pytest.mark.asyncio
async def test_v4_stream_emits_thread_and_run_ids(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, _ = runtime

    events = []
    context_event = None
    async for raw in graph.stream(
        inputs=[V4InputItem(type="text", content="latest oil news today")],
        thread_id="thread:stream",
        user_id="user-4",
        workspace_id="workspace-4",
    ):
        if raw.startswith("event: context"):
            context_event = raw
        if raw.startswith("event: final_output"):
            events.append(raw)

    assert events
    assert context_event is not None
    context_payload = context_event.split("\n")[1].replace("data: ", "")
    context_data = json.loads(context_payload)
    assert context_data["intent"] == "scenario"
    assert context_data["role_lens"] == "pm"
    payload = events[0].split("\n")[1].replace("data: ", "")
    data = json.loads(payload)
    assert data["thread_id"] == "thread:stream"
    assert data["run_id"].startswith("run:")


@pytest.mark.asyncio
async def test_v4_presentation_requires_resume_and_survives_runtime_restart(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(
        FakeTool(
            "market_analyze",
            {
                "ticker": "X:BTCUSD",
                "latest": {
                    "ticker": "X:BTCUSD",
                    "close": "72810.00",
                    "timestamp": "2026-03-17T00:00:00+00:00",
                },
                "bars": [],
            },
        )
    )
    settings = Settings(runtime_persistence_dir=str(tmp_path / "v4-approval"))
    first_runtime = ResolverStubRuntime(
        settings=settings,
        tools=registry,
        resolutions={"price of bitcoin": ResolvedEntities(market_ticker="X:BTCUSD", confidence=0.96)},
    )

    paused_memo, paused_trace = await first_runtime.execute(
        inputs=[V4InputItem(type="text", content="price of bitcoin")],
        thread_id="thread:resume",
        user_id="user-approval",
        workspace_id="workspace-approval",
        response_mode_hint="presentation",
    )

    assert paused_trace["status"] == "interrupted"
    assert paused_trace["approval_requests"]
    assert "paused" in paused_memo.summary.lower()

    resumed_runtime = ResolverStubRuntime(
        settings=settings,
        tools=registry,
        resolutions={"price of bitcoin": ResolvedEntities(market_ticker="X:BTCUSD", confidence=0.96)},
    )
    memo, trace = await resumed_runtime.execute(
        inputs=[V4InputItem(type="text", content="price of bitcoin")],
        thread_id="thread:resume",
        user_id="user-approval",
        workspace_id="workspace-approval",
        response_mode_hint="presentation",
        approval_response={"approved": True},
    )

    assert trace["answer_mode"] == "presentation"
    assert trace["thread_refs"]["thread_id"] == "thread:resume"
    assert memo.evidence_blocks


def test_sqlite_run_coordinator_rejects_same_thread_across_instances(tmp_path) -> None:
    path = tmp_path / "runtime-control.sqlite3"
    first = SqliteRunCoordinator(path)
    second = SqliteRunCoordinator(path)

    first.acquire_run(
        assistant_id="stratos-v4",
        thread_id="thread:shared",
        run_id="run:1",
        workspace_id="workspace:shared",
        user_id="user:shared",
        max_runs_per_workspace=4,
        max_runs_per_thread=1,
    )

    with pytest.raises(RuntimeError, match="already active"):
        second.acquire_run(
            assistant_id="stratos-v4",
            thread_id="thread:shared",
            run_id="run:2",
            workspace_id="workspace:shared",
            user_id="user:shared",
            max_runs_per_workspace=4,
            max_runs_per_thread=1,
        )

    first.complete_run(thread_id="thread:shared", run_id="run:1", status="completed")
    second.acquire_run(
        assistant_id="stratos-v4",
        thread_id="thread:shared",
        run_id="run:3",
        workspace_id="workspace:shared",
        user_id="user:shared",
        max_runs_per_workspace=4,
        max_runs_per_thread=1,
    )


@pytest.mark.asyncio
async def test_v4_answers_market_price_from_internal_market_snapshot(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="price of bitcoin")],
        thread_id="thread:btc",
        user_id="user-5",
        workspace_id="workspace-5",
    )

    assert memo.intent == "market"
    assert trace["answer_mode"] == "grounded_direct"
    assert tools["market_analyze"].calls
    assert "72810.00" in memo.recommendation


@pytest.mark.asyncio
async def test_v4_vague_query_requests_context(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, _ = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="what to do in this")],
        thread_id="thread:vague",
        user_id="user-6",
        workspace_id="workspace-6",
    )

    assert trace["answer_mode"] == "insufficient_evidence"
    assert "Ask with a portfolio, ticker, country, market, event, or scenario" in memo.summary


@pytest.mark.asyncio
async def test_v4_delegates_general_greeting_to_langchain_runtime(tmp_path) -> None:
    registry = ToolRegistry()
    general_runtime = FakeLangChainRuntime()
    graph = ResolverStubRuntime(
        settings=Settings(runtime_persistence_dir=str(tmp_path / "v4-general")),
        tools=registry,
        general_runtime=general_runtime,
    )

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="hi")],
        thread_id="thread:general",
        user_id="user-general",
        workspace_id="workspace-general",
        role_lens="general",
    )

    assert general_runtime.calls == ["hi"]
    assert trace["path"] == "langchain_v3_delegate"
    assert memo.decision == "Ready."
    assert "call tools when the question depends on fresh or external context" in memo.summary
    assert memo.role == "general"
    assert trace["role"] == "general"


@pytest.mark.asyncio
async def test_v4_auto_role_escalates_finance_query_into_finance_council(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, _ = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="What should I watch in AAPL quality, event pulse, and regime history before adding risk?")],
        thread_id="thread:auto-finance",
        user_id="user-auto",
        workspace_id="workspace-auto",
    )

    assert trace["mode"] == "finance_council"
    assert memo.decision_packet is not None
    assert memo.role == "pm"


@pytest.mark.asyncio
async def test_v4_eth_price_does_not_fall_back_to_company_quality(tmp_path) -> None:
    registry = ToolRegistry()
    market_eth = FakeTool(
        "market_analyze",
        {
            "ticker": "X:ETHUSD",
            "pending": True,
            "status": "pending",
            "suggested_retry_seconds": 30,
            "latest": None,
            "bars": [],
        },
    )
    registry.register(market_eth)
    graph = ResolverStubRuntime(
        settings=Settings(runtime_persistence_dir=str(tmp_path / "v4-eth")),
        tools=registry,
        resolutions={"price of ETH": ResolvedEntities(market_ticker="X:ETHUSD", confidence=0.95)},
    )

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="price of ETH")],
        thread_id="thread:eth",
        user_id="user-7",
        workspace_id="workspace-7",
    )

    assert trace["answer_mode"] == "grounded_direct"
    assert "Ethereum snapshot is still building" in memo.recommendation
    assert "AAPL" not in memo.recommendation


@pytest.mark.asyncio
async def test_v4_multisignal_query_surfaces_specialist_views(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="What should I watch in AAPL quality, event pulse, and regime history before adding risk?")],
        thread_id="thread:multisignal",
        user_id="user-8",
        workspace_id="workspace-8",
    )

    assert tools["company_analyze"].calls
    assert tools["events_analyze"].calls
    assert tools["history_analyze"].calls
    assert trace["specialists"]
    assert memo.specialist_views
    assert any(view["specialist"] == "research" for view in memo.specialist_views)
    assert any("Global event pulse" in finding for finding in memo.key_findings)
    assert any("prior regime analog" in item.lower() or "current market regime" in item.lower() for item in memo.historical_context)


@pytest.mark.asyncio
async def test_v4_country_risk_prompt_does_not_force_portfolio_path(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="How should I frame India sovereign risk versus US macro pressure this week?")],
        thread_id="thread:macro-country",
        user_id="user-9",
        workspace_id="workspace-9",
    )

    assert tools["portfolio_analyze"].calls == []
    assert tools["company_analyze"].calls == []
    assert trace["answer_mode"] in {"decision_with_limits", "grounded_direct"}
    assert "AAPL already represents" not in memo.summary
    assert "earnings quality" not in memo.recommendation.lower()
    assert "US macro" in memo.recommendation or "US rates" in memo.recommendation
    assert "India screens cleaner than the US" in memo.summary
    assert any("India sovereign snapshot" in item for item in memo.watch_items)
    assert any("US sovereign snapshot" in item for item in memo.watch_items)
    assert any("World macro backdrop" in item for item in memo.watch_items)


def test_v4_fallback_resolution_does_not_treat_us_macro_prompt_as_company() -> None:
    resolved = V4GraphRuntime._fallback_resolved_entities(
        "How should I frame India sovereign risk versus US macro pressure this week?"
    )

    assert resolved.company_ticker is None
    assert resolved.country_codes == ["IND", "USA"]


def test_v4_normalize_resolved_entities_maps_crypto_and_fx_to_market_tickers() -> None:
    btc = V4GraphRuntime._normalize_resolved_entities("price of BTC", ResolvedEntities(company_ticker="BTC", confidence=0.4))
    fx = V4GraphRuntime._normalize_resolved_entities("price of INR as per USD", ResolvedEntities(company_ticker="INR", confidence=0.4))

    assert btc.market_ticker == "X:BTCUSD"
    assert btc.company_ticker is None
    assert fx.market_ticker == "FX:INRUSD"


@pytest.mark.asyncio
async def test_v4_company_price_query_uses_resolved_entity(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="price of APPL")],
        thread_id="thread:appl",
        user_id="user-10",
        workspace_id="workspace-10",
    )

    assert tools["company_analyze"].calls
    assert trace["answer_mode"] == "grounded_direct"
    assert "AAPL last closed at 250.12" in memo.recommendation
    assert memo.key_findings == []
    assert memo.watch_items == []
    assert memo.portfolio_impact == []


@pytest.mark.asyncio
async def test_v4_new_run_clears_checkpoint_state_from_prior_company_query(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, _ = runtime
    thread_id = "thread:checkpoint-reset"

    await graph.execute(
        inputs=[V4InputItem(type="text", content="What should I watch in AAPL quality, event pulse, and regime history before adding risk?")],
        thread_id=thread_id,
        user_id="user-reset",
        workspace_id="workspace-reset",
    )

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="price of bitcoin")],
        thread_id=thread_id,
        user_id="user-reset",
        workspace_id="workspace-reset",
    )

    assert trace["answer_mode"] == "grounded_direct"
    assert "Bitcoin last closed" in memo.recommendation
    assert memo.key_findings == []
    assert memo.watch_items == []
    assert memo.evidence_blocks == [{"title": "Audited claims", "detail": "STRATOS internal state was used as the primary source of truth for this answer."}]


@pytest.mark.asyncio
async def test_v4_fx_query_answers_from_internal_market_snapshot(tmp_path) -> None:
    registry = ToolRegistry()
    market_fx = FakeTool(
        "market_analyze",
        {
            "ticker": "FX:INRUSD",
            "latest": {
                "ticker": "FX:INRUSD",
                "close": "0.0121",
                "timestamp": "2026-03-17T00:00:00+00:00",
            },
            "bars": [],
        },
    )
    registry.register(market_fx)
    graph = ResolverStubRuntime(
        settings=Settings(runtime_persistence_dir=str(tmp_path / "v4-fx")),
        tools=registry,
        resolutions={"price of inr over usd": ResolvedEntities(market_ticker="FX:INRUSD", confidence=0.91)},
    )

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="price of inr over usd")],
        thread_id="thread:fx",
        user_id="user-11",
        workspace_id="workspace-11",
    )

    assert trace["answer_mode"] == "grounded_direct"
    assert "INR/USD last closed at 0.0121" in memo.recommendation
    assert memo.key_findings == []
    assert memo.watch_items == []


@pytest.mark.asyncio
async def test_v4_company_news_query_uses_realtime_news_tool(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="latest AAPL news")],
        thread_id="thread:news",
        user_id="user-12",
        workspace_id="workspace-12",
    )

    assert tools["company_news_analyze"].calls
    assert trace["answer_mode"] in {"grounded_direct", "research_with_citations"}
    assert "Apple suppliers signal steadier iPhone demand" in memo.recommendation or any(
        "Apple suppliers signal steadier iPhone demand" in item for item in memo.key_findings
    )


@pytest.mark.asyncio
async def test_v4_fed_news_query_uses_policy_and_web_routing(runtime: tuple[V4GraphRuntime, dict[str, FakeTool]]) -> None:
    graph, tools = runtime

    memo, trace = await graph.execute(
        inputs=[V4InputItem(type="text", content="latest fed news today")],
        thread_id="thread:fed",
        user_id="user-13",
        workspace_id="workspace-13",
    )

    assert tools["policy_events_analyze"].calls
    assert tools["web_search"].calls
    assert trace["answer_mode"] in {"grounded_direct", "research_with_citations", "decision_with_limits"}
