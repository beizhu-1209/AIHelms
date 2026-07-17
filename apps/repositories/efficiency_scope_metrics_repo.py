"""Scope-aware aggregate queries shared by efficiency views."""

import datetime
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.efficiency_scope_filter import build_scope_filter


async def get_total_user_count(
    session: AsyncSession,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> int:
    params: dict = {}
    scope_filter = build_scope_filter(
        "u.id", department_ids, project_ids, params, "total_users"
    )
    result = await session.execute(
        text(
            "SELECT COUNT(u.id) FROM aihelms.users u"
            f" WHERE u.is_active = true{scope_filter}"
        ),
        params,
    )
    return result.scalar() or 0


async def get_active_user_ids(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> set[int]:
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "active_users"
    )
    result = await session.execute(
        text(
            "SELECT DISTINCT c.user_id FROM aihelms.cost_summary_daily c"
            " JOIN aihelms.users u ON u.id = c.user_id AND u.is_active = true"
            " WHERE c.summary_date >= :start AND c.summary_date <= :end"
            f" AND c.user_id IS NOT NULL{scope_filter}"
        ),
        params,
    )
    return {row[0] for row in result.fetchall()}


async def get_total_cost(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> float:
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "total_cost"
    )
    result = await session.execute(
        text(
            "SELECT COALESCE(SUM(c.internal_cost), 0) FROM aihelms.cost_summary_daily c"
            " WHERE c.summary_date >= :start AND c.summary_date <= :end"
            f"{scope_filter}"
        ),
        params,
    )
    return float(result.scalar() or 0)


async def get_daily_cost_and_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    granularity: str = "day",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    if granularity == "week":
        trunc = "date_trunc('week', c.summary_date)::date"
        current = start_date - datetime.timedelta(days=start_date.weekday())
        step = datetime.timedelta(days=7)
    elif granularity == "month":
        trunc = "date_trunc('month', c.summary_date)::date"
        current = start_date.replace(day=1)
        step = None
    else:
        trunc = "c.summary_date::date"
        current = start_date
        step = datetime.timedelta(days=1)
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "daily_cost"
    )
    sql = text(
        f"SELECT {trunc} AS d,"
        " COUNT(DISTINCT c.user_id) FILTER (WHERE u.is_active = true) AS active_users,"
        " COALESCE(SUM(c.internal_cost), 0) AS cost"
        " FROM aihelms.cost_summary_daily c"
        " LEFT JOIN aihelms.users u ON u.id = c.user_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        " AND c.user_id IS NOT NULL"
        f"{scope_filter} GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    raw = {
        r[0]: {"active_users": int(r[1]), "cost": float(r[2])}
        for r in result.fetchall()
    }
    rows = []
    while current <= end_date:
        item = raw.get(current, {"active_users": 0, "cost": 0.0})
        rows.append({"date": str(current), **item})
        if granularity == "month":
            current = (current.replace(day=28) + datetime.timedelta(days=4)).replace(
                day=1
            )
        else:
            current += step
    return rows
