from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AdminAuditLog


async def find_logs(
    session: AsyncSession,
    page: int,
    page_size: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    method: str | None = None,
    status: str | None = None,
    action: str | None = None,
) -> list[AdminAuditLog]:
    stmt = select(AdminAuditLog).order_by(AdminAuditLog.id.desc())
    stmt = _apply_filters(stmt, start_time, end_time, user_id, method, status, action)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_logs(
    session: AsyncSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    method: str | None = None,
    status: str | None = None,
    action: str | None = None,
) -> int:
    stmt = select(func.count(AdminAuditLog.id))
    stmt = _apply_filters(stmt, start_time, end_time, user_id, method, status, action)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_distinct_actors(session: AsyncSession) -> list[tuple[int, str]]:
    stmt = (
        select(AdminAuditLog.user_id, AdminAuditLog.username)
        .distinct()
        .order_by(AdminAuditLog.username)
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def find_distinct_actions(session: AsyncSession) -> list[str]:
    stmt = select(AdminAuditLog.action).distinct().order_by(AdminAuditLog.action)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def delete_before(session: AsyncSession, before: datetime) -> int:
    stmt = delete(AdminAuditLog).where(AdminAuditLog.created_at < before)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


def _apply_filters(stmt, start_time, end_time, user_id, method, status, action):
    if start_time is not None:
        stmt = stmt.where(AdminAuditLog.created_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(AdminAuditLog.created_at <= end_time)
    if user_id is not None:
        stmt = stmt.where(AdminAuditLog.user_id == user_id)
    if method:
        stmt = stmt.where(AdminAuditLog.method == method)
    if status == "success":
        stmt = stmt.where(
            AdminAuditLog.status_code >= 200,
            AdminAuditLog.status_code < 300,
        )
    elif status == "failed":
        stmt = stmt.where(
            (AdminAuditLog.status_code < 200)
            | (AdminAuditLog.status_code >= 300)
        )
    if action:
        stmt = stmt.where(AdminAuditLog.action == action)
    return stmt
