"""Simple tracked-entity refresh scheduler."""

from __future__ import annotations

import asyncio


class TrackedRefreshScheduler:
    """Publishes refresh requests for tracked entities on an interval."""

    def __init__(self, *, settings, refreshes) -> None:
        self._settings = settings
        self._refreshes = refreshes

    async def publish_once(self) -> None:
        await self._refreshes.request_refresh("world_state", "global", reason="scheduled")
        for ticker in self._settings.tracked_company_list:
            await self._refreshes.request_refresh("company", ticker, reason="scheduled")
        for country in self._settings.tracked_country_list:
            await self._refreshes.request_refresh("country", country, reason="scheduled")
        for ticker in self._settings.tracked_market_list:
            await self._refreshes.request_refresh("market", ticker, reason="scheduled")

    async def run_forever(self, interval_seconds: int = 900) -> None:
        while True:
            await self.publish_once()
            await asyncio.sleep(interval_seconds)
