from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import ExportTask


def _apply_filters(stmt, source: str | None, status: str | None):
    if source:
        stmt = stmt.where(ExportTask.source == source)
    if status:
        stmt = stmt.where(ExportTask.status == status)
    return stmt


async def create(session: AsyncSession, task: ExportTask) -> ExportTask:
    session.add(task)
    await session.flush()
    return task


async def find_by_id(session: AsyncSession, task_id: int) -> ExportTask | None:
    result = await session.execute(select(ExportTask).where(ExportTask.id == task_id))
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int,
    page_size: int,
    source: str | None = None,
    status: str | None = None,
) -> list[ExportTask]:
    stmt = select(ExportTask).order_by(ExportTask.created_at.desc(), ExportTask.id.desc())
    stmt = _apply_filters(stmt, source, status)
    stmt = stmt.limit(page_size).offset((page - 1) * page_size)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    source: str | None = None,
    status: str | None = None,
) -> int:
    stmt = select(func.count(ExportTask.id))
    stmt = _apply_filters(stmt, source, status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_cleanup_candidates(
    session: AsyncSession, before: datetime, limit: int = 200
) -> list[ExportTask]:
    stmt = (
        select(ExportTask)
        .where(
            ExportTask.status.in_(["success", "failed", "canceled"]),
            ExportTask.created_at < before,
        )
        .order_by(ExportTask.created_at.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_stale_running(session: AsyncSession, deadline) -> list[ExportTask]:
    result = await session.execute(
        select(ExportTask).where(
            ExportTask.status == "running",
            ExportTask.started_at.isnot(None),
            ExportTask.started_at < deadline,
        )
    )
    return list(result.scalars().all())
