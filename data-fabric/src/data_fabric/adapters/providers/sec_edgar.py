"""SEC EDGAR provider adapter."""

from __future__ import annotations

from typing import Any

import httpx


class SecEdgarSource:
    """Fetch SEC company facts and submission metadata."""

    def __init__(
        self,
        *,
        base_url: str,
        ticker_map_url: str,
        user_agent: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._ticker_map_url = ticker_map_url
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
            headers={"User-Agent": user_agent, "Accept": "application/json"},
        )
        self._ticker_map: dict[str, dict[str, Any]] | None = None

    @property
    def source_name(self) -> str:
        return "sec"

    async def fetch(self, **params: object) -> list[dict]:
        ticker = str(params["ticker"]).upper()
        bundle = await self.fetch_company_bundle(ticker)
        return [bundle]

    async def fetch_company_bundle(self, ticker: str) -> dict[str, Any]:
        mapping = await self._get_ticker_map()
        item = mapping.get(ticker.upper())
        if item is None:
            raise ValueError(f"SEC mapping not found for ticker '{ticker}'")

        cik = str(item["cik_str"]).zfill(10)
        submissions_response = await self._client.get(
            f"{self._base_url}/submissions/CIK{cik}.json"
        )
        companyfacts_response = await self._client.get(
            f"{self._base_url}/api/xbrl/companyfacts/CIK{cik}.json"
        )

        submissions_response.raise_for_status()
        companyfacts_response.raise_for_status()

        submissions = submissions_response.json()
        companyfacts = companyfacts_response.json()
        recent = submissions.get("filings", {}).get("recent", {})
        filings: list[dict[str, Any]] = []
        for accession, form, filing_date, primary_document in zip(
            recent.get("accessionNumber", []),
            recent.get("form", []),
            recent.get("filingDate", []),
            recent.get("primaryDocument", []),
        ):
            filings.append(
                {
                    "accession_number": accession,
                    "form": form,
                    "filing_date": filing_date,
                    "primary_document": primary_document,
                }
            )

        return {
            "ticker": ticker.upper(),
            "cik": cik,
            "name": submissions.get("name", ticker.upper()),
            "submissions": submissions,
            "companyfacts": companyfacts,
            "filings": filings,
        }

    async def health_check(self) -> bool:
        try:
            mapping = await self._get_ticker_map()
            return bool(mapping)
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()

    async def _get_ticker_map(self) -> dict[str, dict[str, Any]]:
        if self._ticker_map is not None:
            return self._ticker_map
        response = await self._client.get(self._ticker_map_url)
        response.raise_for_status()
        payload = response.json()
        self._ticker_map = {
            str(item["ticker"]).upper(): item
            for item in payload.values()
        }
        return self._ticker_map
