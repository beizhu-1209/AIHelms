from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AdminAuditLog
from repositories import audit_log_repo


async def list_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    method: str | None = None,
    status: str | None = None,
    action: str | None = None,
) -> dict:
    total = await audit_log_repo.count_logs(
        session,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        method=method,
        status=status,
        action=action,
    )
    logs = await audit_log_repo.find_logs(
        session,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        method=method,
        status=status,
        action=action,
    )
    return {
        "items": [_serialize(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def list_filters(session: AsyncSession) -> dict:
    actors = await audit_log_repo.find_distinct_actors(session)
    actions = await audit_log_repo.find_distinct_actions(session)
    return {
        "actors": [{"user_id": uid, "username": uname} for uid, uname in actors],
        "actions": actions,
    }


def _serialize(log: AdminAuditLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "identity_type": log.identity_type,
        "method": log.method,
        "path": log.path,
        "action": log.action,
        "status_code": log.status_code,
        "ip": log.ip,
        "user_agent": log.user_agent,
        "duration_ms": log.duration_ms,
        "request_summary": log.request_summary,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
