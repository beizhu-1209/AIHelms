"""AI 效能分析 API。"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from services import efficiency_service

router = APIRouter(prefix="/efficiency")


def _parse_period(period: str | None) -> tuple[date, date]:
    """Convert frontend period param to start_date/end_date."""
    today = date.today()
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    # Default: current month
    return today.replace(day=1), today


@router.get("/overview")
async def get_overview(
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
    data = await efficiency_service.get_overview(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption")
async def get_adoption(
    period: str | None = Query(None),
    dimension: str = Query("department"),
    metric: str = Query("dau"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    data = await efficiency_service.get_adoption(session, start, end, dimension, metric)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/agents")
async def get_adoption_agents(
    period: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    data = await efficiency_service.get_adoption_agents(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/resources")
async def get_adoption_resources(
    period: str | None = Query(None),
    type: str = Query("mcp"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    data = await efficiency_service.get_adoption_resources(session, start, end, type)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/unused-users")
async def get_unused_users(
    period: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    data = await efficiency_service.get_unused_users(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/cost")
async def get_cost(
    period: str | None = Query(None),
    resource_type: str = Query(""),
    department: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    cost_type = resource_type if resource_type else "all"
    dept_id = int(department) if department.isdigit() else None
    data = await efficiency_service.get_cost(session, start, end, cost_type, dept_id)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/cost/detail")
async def get_cost_detail(
    period: str | None = Query(None),
    tab: str = Query("department"),
    resource_type: str = Query(""),
    department: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = _parse_period(period)
    cost_type = resource_type if resource_type else "all"
    dept_id = int(department) if department.isdigit() else None
    data = await efficiency_service.get_cost_detail(
        session, start, end, tab, cost_type, dept_id
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/budget")
async def get_budget(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.get_budget(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/budget/alerts")
async def get_budget_alerts(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.get_budget_alerts(session)
    return {"code": 200, "message": "ok", "data": data}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.get("/reports")
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    items, total = await efficiency_service.list_reports(session, page, page_size)
    return {
        "code": 200,
        "message": "ok",
        "data": {"items": items, "total": total, "page": page, "page_size": page_size},
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.get_report_detail(session, report_id)
    if not data:
        return {"code": 404, "message": "报告不存在", "data": None}
    return {"code": 200, "message": "ok", "data": data}


class CreateReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(weekly|monthly|custom)$")
    period_start: date
    period_end: date
    model_used: str | None = None
    filters: dict | None = None


@router.post("/reports", summary="生成分析报告")
async def create_report(
    req: CreateReportRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.create_report(
        session,
        report_type=req.report_type,
        period_start=req.period_start,
        period_end=req.period_end,
        created_by=current_user["id"],
        model_used=req.model_used,
        filters=req.filters,
    )
    return {"code": 200, "message": "报告创建成功", "data": data}


class UpdateSuggestionRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|accepted|rejected|implemented)$")
    note: str = ""


@router.put("/suggestions/{suggestion_id}/status", summary="更新建议状态")
async def update_suggestion(
    suggestion_id: int,
    req: UpdateSuggestionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.update_suggestion_status(
        session, suggestion_id, req.status, req.note, current_user["id"]
    )
    if not data:
        return {"code": 404, "message": "建议不存在", "data": None}
    return {"code": 200, "message": "建议状态更新成功", "data": data}
