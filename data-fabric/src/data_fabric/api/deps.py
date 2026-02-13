"""Dependency injection — wire ports to concrete adapters.

This is the ONLY place where adapters are imported.
Domain and application layers never know about concrete implementations.
"""

from __future__ import annotations

from data_fabric.application import QueryCompanyUseCase


def get_query_company_use_case() -> QueryCompanyUseCase:
    """Wire QueryCompanyUseCase with concrete adapter.

    TODO: Replace with real adapter once persistence is implemented.
    """
    raise NotImplementedError("Wire concrete DataReader adapter here")
