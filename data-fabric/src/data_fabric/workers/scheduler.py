"""Scheduler entrypoint for tracked refresh requests."""

from __future__ import annotations

import asyncio

from data_fabric.adapters.scheduler import TrackedRefreshScheduler
from data_fabric.application import RefreshRequestManager
from data_fabric.workers.runtime import build_runtime, close_runtime


async def main() -> None:
    runtime = await build_runtime()
    scheduler = TrackedRefreshScheduler(
        settings=runtime.settings,
        refreshes=RefreshRequestManager(runtime.documents, runtime.events),
    )
    try:
        await scheduler.run_forever()
    finally:
        await close_runtime(runtime)


if __name__ == "__main__":
    asyncio.run(main())
