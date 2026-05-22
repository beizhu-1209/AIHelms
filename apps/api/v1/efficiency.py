"""AI 效能分析 API。"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from services import efficiency_service

router = APIRouter(prefix="/efficiency", tags=["AI效能"])


def _default_date_range() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    return start, today


@router.get("/overview")
async def get_overview(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_overview(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/trend")
async def get_trend(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    group_by: str = Query("day"),
    cost_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_trend(session, start, end, group_by, cost_type)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/composition")
async def get_composition(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_composition(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/key-type-comparison")
async def get_key_type_comparison(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_key_type_comparison(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/ranking")
async def get_ranking(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    dimension: str = Query("department"),
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_ranking(session, start, end, dimension, limit)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/analysis/{dimension}")
async def get_analysis(
    dimension: str,
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    cost_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_analysis(session, start, end, dimension, cost_type)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/budget/overview")
async def get_budget_overview(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    start, end = start_date or _default_date_range()[0], end_date or _default_date_range()[1]
    data = await efficiency_service.get_budget_overview(session, start, end)
    return {"code": 200, "message": "ok", "data": data}


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
    report_type: str = Field(..., pattern="^(daily|weekly|monthly|quarterly|custom)$")
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
