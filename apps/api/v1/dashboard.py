"""管理后台 Dashboard API。"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db, require_permission
from services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _parse_period(period: str | None) -> tuple[date, date]:
    today = date.today()
    if period == "today":
        return today, today
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    if period == "last_month":
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        return last_month_end.replace(day=1), last_month_end
    return today.replace(day=1), today


@router.get("")
async def get_dashboard(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    data = await dashboard_service.get_dashboard(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/refresh", summary="刷新Dashboard效能数据")
async def refresh_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("efficiency:write")),
):
    data = await dashboard_service.request_refresh()
    return {"code": 200, "message": "刷新任务已提交", "data": data}


@router.get("/refresh/{task_id}", summary="查询Dashboard刷新任务状态")
async def get_dashboard_refresh_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    data = dashboard_service.get_refresh_status(task_id)
    return {"code": 200, "message": "ok", "data": data}
