from __future__ import annotations

from stratos_orchestrator.adapters.tools.registry import get_registry
from stratos_orchestrator.application.langchain_v3 import LangChainAgentRuntime, _classify_role


def test_classify_failure_for_tool_surface_mismatch() -> None:
    classification = LangChainAgentRuntime._classify_failure(
        "tool call validation failed: attempted to call tool 'macro_analyze_world' which was not in request.tools"
    )

    assert classification[0] == "tool orchestration error"
    assert "tool surface" in classification[1].lower()


def test_classify_failure_for_source_fetch_error() -> None:
    classification = LangChainAgentRuntime._classify_failure(
        "Redirect response '307 Temporary Redirect' for url 'https://www.iocl.com'"
    )

    assert classification[0] == "source retrieval error"
    assert "external source" in classification[1].lower()


def test_registry_exposes_world_macro_tool() -> None:
    registry = get_registry("http://localhost:8000/api/v2")

    assert registry.has_tool("macro_analyze_world")


def test_classify_role_supports_new_operator_lenses() -> None:
    assert _classify_role("Act as my CA and build the month-end close checklist.") == "ca"
    assert _classify_role("Act as my CFA and write an investment memo on AAPL.") == "cfa"
    assert _classify_role("Act as my CMO and design a go-to-market launch plan.") == "cmo"
