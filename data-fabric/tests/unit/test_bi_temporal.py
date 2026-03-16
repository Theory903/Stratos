from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from data_fabric.adapters.database.postgres import PostgresDataStore


@pytest.mark.asyncio
async def test_get_world_state_snapshot_builds_ordered_query() -> None:
    session_factory = MagicMock()
    session = AsyncMock()
    session_factory.return_value.__aenter__.return_value = session

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    store = PostgresDataStore(session_factory)
    cutoff = datetime(2023, 1, 1, 12, 0, 0)
    await store.get_world_state_snapshot(as_of=cutoff)

    statement = str(session.execute.call_args.args[0])
    assert "world_state_snapshots" in statement
    assert "stored_at <=" in statement
    assert "computed_at DESC" in statement


@pytest.mark.asyncio
async def test_get_company_snapshot_builds_ordered_query() -> None:
    session_factory = MagicMock()
    session = AsyncMock()
    session_factory.return_value.__aenter__.return_value = session

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    store = PostgresDataStore(session_factory)
    cutoff = datetime(2023, 1, 1, 12, 0, 0)
    await store.get_company_snapshot("AAPL", as_of=cutoff)

    statement = str(session.execute.call_args.args[0])
    assert "company_feature_snapshots" in statement
    assert "stored_at <=" in statement
    assert "computed_at DESC" in statement
