"""AI 效能分析 API。"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db, require_permission
from services import efficiency_service

router = APIRouter(prefix="/efficiency")


def _parse_scope_ids(scope_ids: str, scope_id: str, department: str) -> list[int]:
    raw = scope_ids or scope_id or department
    return [int(item) for item in raw.split(',') if item.strip().isdigit()]


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
    granularity: str = Query("day"),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    scope: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    if scope == "self":
        data = await efficiency_service.get_user_overview(
            session, start, end, current_user["id"]
        )
    else:
        selected_scopes = _parse_scope_ids(scope_ids, "", "")
        department_ids = selected_scopes if dimension == "department" else None
        project_ids = selected_scopes if dimension == "project" else None
        data = await efficiency_service.get_overview(
            session, start, end, granularity, dimension, department_ids, project_ids
        )
    if isinstance(data, dict):
        data["freshness"] = await efficiency_service.get_freshness(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/trend")
async def get_trend(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
    granularity: str | None = Query(None, pattern="^(day|week|month)$"),
    scope: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    bucket = granularity or group_by
    user_id = current_user["id"] if scope == "self" else None
    data = await efficiency_service.get_trend(session, start, end, bucket, user_id)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption")
async def get_adoption(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    metric: str = Query("dau"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_adoption(
        session, start, end, dimension, metric, department_ids, project_ids
    )
    if isinstance(data, dict):
        data["freshness"] = await efficiency_service.get_freshness(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/scope-users")
async def get_adoption_scope_users(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_id: int = Query(...),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    data = await efficiency_service.get_adoption_scope_users(
        session, start, end, dimension, scope_id
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/agents")
async def get_adoption_agents(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_adoption_agents(
        session, start, end, dimension, department_ids, project_ids
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/resources")
async def get_adoption_resources(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    type: str = Query("mcp"),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_adoption_resources(
        session, start, end, type, dimension, department_ids, project_ids
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/adoption/unused-users")
async def get_unused_users(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_unused_users(
        session, start, end, dimension, department_ids, project_ids
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/cost")
async def get_cost(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    resource_type: str = Query(""),
    dimension: str = Query("department", pattern="^(department|project)$"),
    department: str = Query(""),
    scope_id: str = Query(""),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    cost_type = resource_type if resource_type else "all"
    selected_scopes = _parse_scope_ids(scope_ids, scope_id, department)
    dept_id = selected_scopes if dimension == "department" else None
    project_id = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_cost(
        session, start, end, cost_type, dept_id, dimension, project_id
    )
    if isinstance(data, dict):
        data["freshness"] = await efficiency_service.get_freshness(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/cost/detail")
async def get_cost_detail(
    period: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    tab: str = Query("department"),
    resource_type: str = Query(""),
    dimension: str = Query("department", pattern="^(department|project)$"),
    department: str = Query(""),
    scope_id: str = Query(""),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = _parse_period(period)
    cost_type = resource_type if resource_type else "all"
    selected_scopes = _parse_scope_ids(scope_ids, scope_id, department)
    dept_id = selected_scopes if dimension == "department" else None
    project_id = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_cost_detail(
        session, start, end, tab, cost_type, dept_id, dimension, project_id
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/budget")
async def get_budget(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_budget(
        session, month, department_ids, project_ids
    )
    data["freshness"] = await efficiency_service.get_freshness(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/budget/alerts")
async def get_budget_alerts(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    dimension: str = Query("department", pattern="^(department|project)$"),
    scope_ids: str = Query(""),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    selected_scopes = _parse_scope_ids(scope_ids, "", "")
    department_ids = selected_scopes if dimension == "department" else None
    project_ids = selected_scopes if dimension == "project" else None
    data = await efficiency_service.get_budget_alerts(
        session, month, department_ids, project_ids
    )
    return {"code": 200, "message": "ok", "data": data}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.post("/refresh", summary="刷新效能数据")
async def refresh_efficiency(
    scope: str = Query("all"),
    current_user: dict = Depends(require_permission("efficiency:write")),
):
    data = await efficiency_service.request_refresh(scope)
    return {"code": 200, "message": "刷新任务已提交", "data": data}


@router.get("/refresh/{task_id}")
async def get_refresh_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    data = efficiency_service.get_refresh_status(task_id)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/health")
async def get_ai_health(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await efficiency_service.get_ai_health(session)
    data["freshness"] = await efficiency_service.get_freshness(session)
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
        raise HTTPException(status_code=404, detail="报告不存在")
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
        raise HTTPException(status_code=404, detail="建议不存在")
    return {"code": 200, "message": "建议状态更新成功", "data": data}
