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
        macro_tool,
        industry_tool,
        company_tool,
        portfolio_tool,
        policy_tool,
        tax_tool,
        geopolitics_tool,
        fraud_tool,
        regime_tool,
    )
    from stratos_orchestrator.config import Settings

    settings = Settings()
    registry = ToolRegistry()
    data_fabric_base = data_fabric_url or settings.data_fabric_url

    # Data Fabric tools (Macro, Company)
    registry.register(macro_tool.MacroTool(data_fabric_base))
    registry.register(company_tool.CompanyTool(data_fabric_base))

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

    return registry
