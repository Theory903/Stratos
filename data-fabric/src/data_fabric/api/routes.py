"""API routes — thin layer delegating to use cases."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from data_fabric.api.deps import get_query_company_use_case
from data_fabric.application import QueryCompanyUseCase
from data_fabric.domain.entities import CompanyProfile

router = APIRouter(tags=["Data Fabric"])


@router.get("/company/{ticker}", response_model=dict)
async def get_company(
    ticker: str,
    use_case: QueryCompanyUseCase = Depends(get_query_company_use_case),
) -> CompanyProfile:
    """Fetch company profile by ticker."""
    return await use_case.execute(ticker)
