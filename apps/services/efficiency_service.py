"""AI 效能 Service 层。"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from celery_app import celery_app

from core.config import settings

from repositories import dashboard_repo, efficiency_repo
from services.efficiency_adoption_service import (
    get_adoption_agents,
    get_adoption_resources,
    get_adoption_scope_users,
    get_unused_users,
)
from services.efficiency_budget_service import get_budget, get_budget_alerts
from services.efficiency_cost_service import get_cost, get_cost_detail
from services.efficiency_health_service import get_ai_health
from services.efficiency_report_service import (
    create_report,
    get_report_detail,
    list_reports,
    update_suggestion_status,
)

logger = logging.getLogger(__name__)

REFRESH_STATE_KEY = "aihelms:efficiency:refresh_task_id"
REFRESH_STATE_TTL_SECONDS = 3600


async def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def _set_refresh_task(task_id: str) -> None:
    client = await _redis()
    try:
        await client.set(REFRESH_STATE_KEY, task_id, ex=REFRESH_STATE_TTL_SECONDS)
    finally:
        await client.aclose()


async def _get_refresh_task_id() -> str:
    client = await _redis()
    try:
        value = await client.get(REFRESH_STATE_KEY)
    finally:
        await client.aclose()
    return str(value or "")


def _task_update_status(task_id: str) -> str:
    if not task_id:
        return "idle"
    state = celery_app.AsyncResult(task_id).state
    if state in {"PENDING", "STARTED", "RETRY"}:
        return "running"
    if state == "FAILURE":
        return "failed"
    return "idle"


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


def _format_freshness(value: datetime | None) -> str:
    if not value:
        return "--"
    if value.tzinfo is None:
        now = datetime.now()
    else:
        now = datetime.now(value.tzinfo)
    diff_minutes = max(0, int((now - value).total_seconds() // 60))
    if diff_minutes < 60:
        return "刚刚" if diff_minutes < 1 else f"{diff_minutes}分钟前"
    return value.strftime("%Y-%m-%d %H:%M")


async def get_freshness(session: AsyncSession) -> dict:
    last_updated_at = await dashboard_repo.get_last_updated_at(session)
    refresh_task_id = await _get_refresh_task_id()
    return {
        "last_updated_at": _iso_or_none(last_updated_at),
        "last_updated_label": _format_freshness(last_updated_at),
        "update_status": _task_update_status(refresh_task_id),
        "task_id": refresh_task_id or None,
    }


async def request_refresh(scope: str = "all") -> dict:
    """Submit aggregation and expose one shared refresh state for all admins."""
    try:
        existing_task_id = await _get_refresh_task_id()
        existing_status = _task_update_status(existing_task_id)
        if existing_status == "running":
            return {"update_status": "running", "task_id": existing_task_id, "scope": scope}

        from tasks.efficiency_tasks import aggregate_cost_summary

        task = aggregate_cost_summary.delay()
        await _set_refresh_task(task.id)
        return {"update_status": "queued", "task_id": task.id, "scope": scope}
    except Exception:  # pragma: no cover - depends on worker runtime
        logger.exception("efficiency refresh request failed")
        return {"update_status": "unavailable", "reason": "刷新任务创建失败", "scope": scope}


def get_refresh_status(task_id: str) -> dict:
    result = celery_app.AsyncResult(task_id)
    state = result.state
    return {
        "task_id": task_id,
        "state": state,
        "ready": result.ready(),
        "successful": result.successful(),
        "failed": result.failed(),
    }


def _calc_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def _prev_period(start_date: date, end_date: date) -> tuple[date, date]:
    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    return prev_end - timedelta(days=days - 1), prev_end


async def get_overview(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    granularity: str = "day",
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> dict:
    dimension = "project" if dimension == "project" else "department"
    dimension_label = "项目" if dimension == "project" else "部门"
    total_users = await efficiency_repo.get_total_user_count(
        session, department_ids, project_ids
    )
    active_ids = await efficiency_repo.get_active_user_ids(
        session, start_date, end_date, department_ids, project_ids
    )
    active_count = len(active_ids)
    total_cost = await efficiency_repo.get_total_cost(
        session, start_date, end_date, department_ids, project_ids
    )
    coverage_rate = round(active_count / total_users * 100, 1) if total_users > 0 else 0
    active_per_capita = round(total_cost / active_count, 2) if active_count > 0 else 0

    prev_start, prev_end = _prev_period(start_date, end_date)
    prev_active_ids = await efficiency_repo.get_active_user_ids(
        session, prev_start, prev_end, department_ids, project_ids
    )
    prev_total_cost = await efficiency_repo.get_total_cost(
        session, prev_start, prev_end, department_ids, project_ids
    )
    prev_coverage = (
        round(len(prev_active_ids) / total_users * 100, 1) if total_users > 0 else 0
    )
    prev_active_per_capita = (
        round(prev_total_cost / len(prev_active_ids), 2) if len(prev_active_ids) > 0 else 0
    )

    trend = await efficiency_repo.get_daily_cost_and_users(
        session, start_date, end_date, granularity, department_ids, project_ids
    )
    current_rows = await efficiency_repo.get_scope_overview(
        session, start_date, end_date, dimension, department_ids, project_ids
    )
    previous_rows = await efficiency_repo.get_scope_overview(
        session, prev_start, prev_end, dimension, department_ids, project_ids
    )
    previous_map = {row["id"]: row for row in previous_rows}

    ranking_items, table_items = [], []
    for row in current_rows:
        total_members = row["total_users"]
        active_members = row["active_users"]
        scope_cost = row["total_cost"]
        coverage = round(active_members / total_members * 100, 1) if total_members > 0 else 0
        row_active_per_capita = round(scope_cost / active_members, 2) if active_members > 0 else 0
        previous = previous_map.get(row["id"], {})
        prev_active = int(previous.get("active_users", 0) or 0)
        prev_scope_cost = float(previous.get("total_cost", 0) or 0)
        prev_active_per_capita_row = round(prev_scope_cost / prev_active, 2) if prev_active > 0 else 0

        ranking_items.append(
            {
                "name": row["name"],
                "coverage_rate": coverage,
                "per_capita_cost": row_active_per_capita,
            }
        )
        table_items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "path": row["path"],
                "total_members": total_members,
                "active_members": active_members,
                "coverage_rate": coverage,
                "total_cost": scope_cost,
                "per_capita_cost": row_active_per_capita,
                "active_per_capita_cost": row_active_per_capita,
                "cost_change": _calc_change(scope_cost, prev_scope_cost),
                "active_per_capita_change": _calc_change(
                    row_active_per_capita, prev_active_per_capita_row
                ),
                "change": _calc_change(scope_cost, prev_scope_cost),
                "active_people": row.get("active_people", []),
            }
        )

    conclusion = (
        f"AI 覆盖 {coverage_rate}% 员工，"
        f"总投入 ¥{total_cost:,.0f}，活跃人均 ¥{active_per_capita:,.0f}"
    )
    warnings = [
        f"{item['name']}活跃人均成本偏高（¥{item['per_capita_cost']:,.0f}）"
        for item in ranking_items
        if item["per_capita_cost"] > active_per_capita * 1.5 and active_per_capita > 0
    ]

    return {
        "conclusion": conclusion,
        "warnings": warnings,
        "dimension": dimension,
        "dimension_label": dimension_label,
        "kpi": {
            "coverage_rate": coverage_rate,
            "total_cost": total_cost,
            "per_capita_cost": active_per_capita,
            "active_per_capita_cost": active_per_capita,
            "coverage_change": _calc_change(coverage_rate, prev_coverage),
            "cost_change": _calc_change(total_cost, prev_total_cost),
            "per_capita_change": _calc_change(active_per_capita, prev_active_per_capita),
        },
        "trend": {
            "dates": [t["date"] for t in trend],
            "active_users": [t["active_users"] for t in trend],
            "cost": [t["cost"] for t in trend],
        },
        "department_ranking": ranking_items,
        "department_table": table_items,
        "alerts": [],
    }


async def get_trend(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    granularity: str = "day",
    user_id: int | None = None,
) -> list[dict]:
    return await efficiency_repo.get_summary_trend(
        session, start_date, end_date, granularity, user_id
    )


async def get_user_overview(
    session: AsyncSession, start_date: date, end_date: date, user_id: int
) -> dict:
    """个人用量概览（web 端 scope=self）。"""
    from sqlalchemy import select, func
    from models.db import CostSummaryDaily

    result = await session.execute(
        select(
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0),
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0),
        ).where(
            CostSummaryDaily.user_id == user_id,
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
        )
    )
    row = result.one()
    total_requests = int(row[0])
    total_cost = float(row[1])

    return {
        "total_cost": total_cost,
        "total_requests": total_requests,
    }


# ---------------------------------------------------------------------------
# Adoption
# ---------------------------------------------------------------------------


async def get_adoption(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    metric: str = "dau",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> dict:
    total_users = await efficiency_repo.get_total_user_count(
        session, department_ids, project_ids
    )
    active_ids = await efficiency_repo.get_active_user_ids(
        session, start_date, end_date, department_ids, project_ids
    )
    active_count = len(active_ids)
    coverage_rate = round(active_count / total_users * 100, 1) if total_users > 0 else 0
    days = (end_date - start_date).days + 1

    prev_start, prev_end = _prev_period(start_date, end_date)
    prev_active_ids = await efficiency_repo.get_active_user_ids(
        session, prev_start, prev_end, department_ids, project_ids
    )
    new_active = len(active_ids - prev_active_ids)

    user_calls = await efficiency_repo.get_user_call_counts(
        session, start_date, end_date, department_ids, project_ids
    )
    daily_avg_frequency = 0.0
    heavy_user_count = 0
    if user_calls and days > 0:
        total_calls = sum(u["calls"] for u in user_calls)
        daily_avg_frequency = (
            round(total_calls / active_count / days, 1) if active_count > 0 else 0
        )
        heavy_user_count = sum(1 for u in user_calls if u["calls"] > 20 * days)
    heavy_user_ratio = (
        round(heavy_user_count / active_count * 100, 1) if active_count > 0 else 0
    )

    light_t, heavy_t = 5 * days, 20 * days
    light = sum(1 for u in user_calls if u["calls"] < light_t)
    medium = sum(1 for u in user_calls if light_t <= u["calls"] < heavy_t)
    heavy = sum(1 for u in user_calls if u["calls"] >= heavy_t)

    active_trend_raw = await efficiency_repo.get_daily_active_users(
        session, start_date, end_date, department_ids, project_ids
    )

    heavy_trend_raw = await efficiency_repo.get_daily_heavy_user_ratio(
        session, start_date, end_date, 10, department_ids, project_ids
    )

    if dimension == "project":
        raw_table = await efficiency_repo.get_project_adoption_table(
            session, start_date, end_date, project_ids
        )
    else:
        raw_table = await efficiency_repo.get_dept_adoption_table(
            session, start_date, end_date, department_ids
        )

    department_table = [
        {
            "id": row["id"],
            "name": row["name"],
            "total_members": row["total"],
            "active_members": row["active"],
            "coverage_rate": row["coverage"],
            "daily_avg_calls": row["daily_calls"],
            "heavy_user_ratio": 0,
            "change": 0,
        }
        for row in raw_table
    ]

    return {
        "kpi": {
            "coverage_rate": coverage_rate,
            "new_active": new_active,
            "daily_avg_frequency": daily_avg_frequency,
            "heavy_user_ratio": heavy_user_ratio,
        },
        "active_trend": {
            "dates": [item["date"] for item in active_trend_raw],
            "values": [item["dau"] for item in active_trend_raw],
        },
        "depth_distribution": {"light": light, "medium": medium, "heavy": heavy},
        "heavy_trend": {
            "dates": [item["date"] for item in heavy_trend_raw],
            "ratios": [item["ratio"] for item in heavy_trend_raw],
        },
        "department_table": department_table,
    }
