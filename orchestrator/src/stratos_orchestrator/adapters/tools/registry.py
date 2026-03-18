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

    def has_tool(self, tool_name: str) -> bool:
        return tool_name in self._tools

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

    def get_schema(self, tool_name: str) -> dict | None:
        tool = self._tools.get(tool_name)
        if tool is None:
            return None
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        }


def get_registry(data_fabric_url: str | None = None) -> ToolRegistry:
    """Factory to get fully populated registry."""
    from stratos_orchestrator.adapters.tools import (
        alpha_vantage_tool,
        calculator_tool,
        coingecko_tool,
        company_tool,
        company_news_tool,
        events_tool,
        finnhub_tool,
        geopolitics_tool,
        fraud_tool,
        history_tool,
        industry_tool,
        market_tool,
        macro_tool,
        macro_world_tool,
        newsapi_tool,
        orderbook_tool,
        policy_tool,
        policy_events_tool,
        provider_health_tool,
        replay_decision_tool,
        decision_context_tool,
        portfolio_state_tool,
        portfolio_tool,
        regime_tool,
        social_tool,
        tax_tool,
        web_search_tool,
        webpage_read_tool,
        yahoo_finance_tool,
    )
    from stratos_orchestrator.config import Settings

    settings = Settings()
    registry = ToolRegistry()
    data_fabric_base = data_fabric_url or settings.data_fabric_url

    # Data Fabric tools (Macro, Company)
    registry.register(macro_tool.MacroTool(data_fabric_base))
    registry.register(macro_world_tool.MacroWorldTool(data_fabric_base))
    registry.register(company_tool.CompanyTool(data_fabric_base))
    registry.register(company_news_tool.CompanyNewsTool(data_fabric_base))
    registry.register(social_tool.SocialTool(data_fabric_base))
    registry.register(market_tool.MarketTool(data_fabric_base))
    registry.register(orderbook_tool.OrderBookTool(data_fabric_base))
    registry.register(events_tool.EventsTool(data_fabric_base))
    registry.register(history_tool.HistoryTool(data_fabric_base))
    registry.register(policy_events_tool.PolicyEventsTool(data_fabric_base))
    registry.register(decision_context_tool.DecisionContextTool(data_fabric_base))
    registry.register(provider_health_tool.ProviderHealthTool(data_fabric_base))
    registry.register(replay_decision_tool.ReplayDecisionTool(data_fabric_base))
    registry.register(portfolio_state_tool.PortfolioStateTool(data_fabric_base))

    # External data source tools (free or paid APIs)
    registry.register(yahoo_finance_tool.YahooFinanceTool())
    registry.register(coingecko_tool.CoinGeckoTool())
    
    # Paid API tools (require API key and budget)
    registry.register(alpha_vantage_tool.AlphaVantageTool())
    registry.register(finnhub_tool.FinnhubTool())
    registry.register(newsapi_tool.NewsAPITool())

    # ML tools (Fraud, Regime)
    registry.register(fraud_tool.FraudTool(settings.ml_service_url))
    registry.register(regime_tool.RegimeTool(settings.ml_service_url))

    # NLP tools (Policy)
    registry.register(policy_tool.PolicyTool(settings.nlp_service_url))

    # Engines/Simulation tools (Geopolitics, Industry, Portfolio, Tax)
    # Geopolitics uses Data Fabric
    registry.register(geopolitics_tool.GeopoliticsTool(data_fabric_base))
    # Industry uses Data Fabric/LLM
    registry.register(industry_tool.IndustryTool(data_fabric_base))
    
    # Portfolio/Tax are mocks/self-contained for now
    registry.register(portfolio_tool.PortfolioTool(data_fabric_base))
    registry.register(tax_tool.TaxTool(data_fabric_base))
    registry.register(calculator_tool.CalculatorTool())
    registry.register(web_search_tool.WebSearchTool())
    registry.register(webpage_read_tool.WebpageReadTool())

    return registry
