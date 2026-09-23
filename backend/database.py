from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


class Base(DeclarativeBase):
    """Declarative base for all CareerForge models."""


engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db() -> None:
    """Create the async engine and session factory on startup.

    On first call the engine is created; subsequent calls are no-ops.
    """
    global engine, _session_factory
    if engine is not None:
        return
    engine = create_async_engine(
        settings.db_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _session_factory = async_sessionmaker(
        engine, class_=AsyncSession
    )


async def shutdown_db() -> None:
    """Dispose the engine on application shutdown."""
    global engine
    if engine is not None:
        await engine.dispose()
        engine = None
        _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Ensure the app lifespan ran.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
