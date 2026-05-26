from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from services import audit_log_service

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: int | None = Query(None),
    method: str | None = Query(None),
    status: str | None = Query(None),
    action: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("audit_log:read")),
):
    result = await audit_log_service.list_logs(
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
    return {"code": 200, "message": "ok", "data": result}


@router.get("/filters")
async def get_audit_log_filters(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("audit_log:read")),
):
    result = await audit_log_service.list_filters(session)
    return {"code": 200, "message": "ok", "data": result}
