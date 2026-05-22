from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Celery worker 用独立的无池引擎，避免 fork 后 event loop 冲突
_worker_engine = None
_worker_session = None


def get_worker_session_factory() -> async_sessionmaker:
    """为 Celery 异步任务提供独立的 session factory（NullPool，无连接复用）。"""
    global _worker_engine, _worker_session
    if _worker_engine is None:
        _worker_engine = create_async_engine(
            settings.database_url, echo=False, poolclass=NullPool
        )
        _worker_session = async_sessionmaker(
            _worker_engine, class_=AsyncSession, expire_on_commit=False
        )
    return _worker_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def close_engine() -> None:
    await engine.dispose()


async def dispose_pool() -> None:
    """Dispose stale connections after Celery fork. Call at start of async tasks."""
    global _worker_engine, _worker_session
    _worker_engine = None
    _worker_session = None
