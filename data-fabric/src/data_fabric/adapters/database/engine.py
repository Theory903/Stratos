"""SQLAlchemy async database module — engine, session, and ORM base."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from data_fabric.config import Settings


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all ORM models."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> AsyncEngine:
    """Create the global async engine (called once at startup)."""
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.postgres_url,
        echo=settings.debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory (for DI)."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_engine() first")
    return _session_factory


def get_engine() -> AsyncEngine:
    """Return the global async engine."""
    if _engine is None:
        raise RuntimeError("Database not initialized — call init_engine() first")
    return _engine


async def create_tables() -> None:
    """Create all tables (development only)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Clean up the engine on shutdown."""
    if _engine is not None:
        await _engine.dispose()
