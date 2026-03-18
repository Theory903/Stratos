"""V5 persistence — checkpointers and stores.

LangGraph persistence is foundational, not an add-on.
It powers interrupts, memory, replay, and fault recovery.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver
    from langgraph.store.base import BaseStore

    from stratos_orchestrator.config import Settings

logger = logging.getLogger(__name__)


def create_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    """Return the best available checkpointer for the current environment.

    Priority:
      1. PostgresSaver (if ``v5_postgres_dsn`` is set)
      2. SqliteSaver  (if ``langgraph-checkpoint-sqlite`` is installed)
      3. InMemorySaver (always available, dev-only)
    """
    dsn = getattr(settings, "v5_postgres_dsn", None) or ""
    if dsn:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore[import-untyped]

            logger.info("V5 persistence: using AsyncPostgresSaver")
            return AsyncPostgresSaver.from_conn_string(dsn)  # type: ignore[return-value]
        except ImportError:
            logger.warning(
                "v5_postgres_dsn is set but langgraph-checkpoint-postgres is not installed. "
                "Falling back."
            )

    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # type: ignore[import-untyped]

        db_path = getattr(settings, "v5_sqlite_path", None) or ":memory:"
        logger.info("V5 persistence: using AsyncSqliteSaver at %s", db_path)
        return AsyncSqliteSaver.from_conn_string(db_path)  # type: ignore[return-value]
    except ImportError:
        pass

    logger.info("V5 persistence: using InMemorySaver (dev-only, no durability)")
    return InMemorySaver()


def create_store(settings: Settings) -> BaseStore:
    """Return a long-term memory store.

    Currently always ``InMemoryStore``.  A Postgres-backed store can replace
    this later without changing callers.
    """
    _ = settings  # reserved for future store config
    return InMemoryStore()
