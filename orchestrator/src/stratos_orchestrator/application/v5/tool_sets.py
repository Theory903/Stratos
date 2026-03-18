"""V5 tool sets — mode-scoped tool collections.

Tool policy:
  - fast_path gets lookup-only tools
  - council gets specialist-domain tools
  - research gets broad investigation tools
  - replay gets history tools only

Keeping tool assignment here prevents accidental scope creep where someone
adds a portfolio tool to the fast path and the system starts doing allocation
work for simple price questions.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model

from stratos_orchestrator.adapters.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helper: wrap registry tools as LangChain StructuredTool
# ---------------------------------------------------------------------------


def _wrap_tool(registry: ToolRegistry, tool_name: str) -> StructuredTool | None:
    """Wrap a single registry tool as a LangChain ``StructuredTool``."""
    schema = registry.get_schema(tool_name)
    if schema is None:
        return None

    args_model = _build_args_model(tool_name, schema["parameters"])

    async def _execute(_tool_name: str = tool_name, **kwargs: Any) -> dict:
        return await registry.execute(_tool_name, kwargs)

    return StructuredTool.from_function(
        coroutine=_execute,
        name=tool_name,
        description=schema["description"],
        args_schema=args_model,
    )


def _build_args_model(tool_name: str, params: dict[str, Any]) -> type[BaseModel]:
    """Build a Pydantic model from a JSON Schema ``parameters`` block."""
    required = set(params.get("required", []))
    properties = params.get("properties", {})
    fields: dict[str, tuple[type, Any]] = {}

    type_map: dict[str, type] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
    }

    for name, prop in properties.items():
        py_type = type_map.get(prop.get("type", "string"), str)
        default = ... if name in required else prop.get("default", "")
        fields[name] = (py_type, default)

    model_name = f"{tool_name}_args"
    return create_model(model_name, **fields)  # type: ignore[call-overload]


def _collect(registry: ToolRegistry, names: list[str]) -> list[StructuredTool]:
    """Wrap several tools, silently skipping missing ones."""
    tools: list[StructuredTool] = []
    for name in names:
        wrapped = _wrap_tool(registry, name)
        if wrapped is not None:
            tools.append(wrapped)
        else:
            logger.debug("Tool '%s' not found in registry, skipping", name)
    return tools


# ---------------------------------------------------------------------------
# Public tool set builders
# ---------------------------------------------------------------------------


def build_fast_path_tools(registry: ToolRegistry) -> list[StructuredTool]:
    """Lookup-only tools — no analysis, no portfolio mutation."""
    return _collect(
        registry,
        [
            "web_search",
            "webpage_read",
            "calculator",
            "yahoo_finance",
        ],
    )


def build_council_tools(registry: ToolRegistry) -> dict[str, list[StructuredTool]]:
    """Domain-scoped tools for specialist council nodes.

    Returns a dict keyed by specialist domain.
    """
    return {
        "market": _collect(
            registry,
            [
                "web_search",
                "history_analyze",
                "regime_detect",
                "calculator",
                "yahoo_finance",
                "coingecko",
                "alpha_vantage",
                "finnhub",
            ],
        ),
        "news": _collect(
            registry,
            [
                "web_search",
                "webpage_read",
                "events_analyze",
                "newsapi",
                "finnhub",
            ],
        ),
        "social": _collect(
            registry,
            [
                "web_search",
            ],
        ),
        "macro": _collect(
            registry,
            [
                "macro_analyze_world",
                "macro_analyze_country",
                "policy_analyze",
                "geopolitics_simulate",
                "alpha_vantage",
            ],
        ),
        "portfolio": _collect(
            registry,
            [
                "portfolio_analyze",
                "portfolio_allocate",
                "history_analyze",
                "regime_detect",
                "tax_optimize",
                "calculator",
            ],
        ),
    }


def build_research_tools(registry: ToolRegistry) -> list[StructuredTool]:
    """Broad investigation tools for bull/bear research nodes."""
    return _collect(
        registry,
        [
            "web_search",
            "webpage_read",
            "calculator",
            "events_analyze",
            "history_analyze",
            "macro_analyze_world",
            "macro_analyze_country",
            "company_analyze",
            "policy_analyze",
            "industry_analyze_sector",
            "geopolitics_simulate",
            "regime_detect",
            "yahoo_finance",
            "coingecko",
            "alpha_vantage",
            "finnhub",
            "newsapi",
        ],
    )


def build_replay_tools(registry: ToolRegistry) -> list[StructuredTool]:
    """History-only tools for replaying past decision threads."""
    return _collect(
        registry,
        [
            "history_analyze",
            "calculator",
        ],
    )
