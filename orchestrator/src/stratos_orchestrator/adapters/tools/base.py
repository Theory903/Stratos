"""Base class for HTTP-based tools."""

from __future__ import annotations

import httpx
from typing import Any

from stratos_orchestrator.adapters.tools.registry import Tool


class HttpTool:
    """Base class for tools that wrap HTTP APIs."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Execute HTTP request."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        
        if self._client:
            response = await self._client.request(method, url, **kwargs)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
        
        response.raise_for_status()
        return response.json()
