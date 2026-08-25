"""AI 效能数据查询仓库层。"""

import logging
import datetime
from datetime import date, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.efficiency_budget_repo import (
    get_all_keys_with_budget,
    get_budget_usage_by_key,
    get_budget_used_for_key,
    get_budget_used_for_keys,
    get_cumulative_cost_by_date,
    get_dept_budget_usage,
    get_key_top10_budget,
    get_project_budget_usage,
    get_scope_budget_key_ids,
    get_user_budget_top10,
    get_user_personal_key_budget,
)
from repositories.efficiency_cost_repo import (
    get_cost_attribution_detail,
    get_cost_by_dept,
    get_cost_by_dimension,
    get_cost_by_type,
    get_cost_detail_by_date,
    get_cost_detail_by_department,
    get_cost_detail_by_dimension,
    get_cost_detail_by_mcp,
    get_cost_detail_by_model,
    get_cost_detail_scope_users,
    get_cost_trend,
    get_dept_per_capita_cost,
    get_per_capita_cost_by_dimension,
    get_user_top10,
)
from repositories.efficiency_report_repo import (
    create_report,
    get_report_by_id,
    list_reports,
    list_suggestions_by_report,
    update_suggestion_status,
)
from repositories.efficiency_scope_filter import build_id_filter, build_scope_filter
from repositories.efficiency_scope_metrics_repo import (
    get_active_user_ids,
    get_daily_cost_and_users,
    get_total_cost,
    get_total_user_count,
)

logger = logging.getLogger(__name__)


async def get_summary_trend(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    granularity: str = "day",
    user_id: int | None = None,
) -> list[dict]:
    if granularity == "week":
        trunc = "date_trunc('week', summary_date)::date"
    elif granularity == "month":
        trunc = "date_trunc('month', summary_date)::date"
    else:
        trunc = "summary_date::date"

    filters = ["summary_date >= :start", "summary_date <= :end"]
    params: dict = {"start": start_date, "end": end_date}
    if user_id is not None:
        filters.append("user_id = :user_id")
        params["user_id"] = user_id

    sql = text(
        f"SELECT {trunc} AS d, cost_type,"
        " COALESCE(SUM(internal_cost), 0) AS cost,"
        " COALESCE(SUM(total_requests), 0) AS requests,"
        " COALESCE(SUM(input_tokens), 0) AS input_tokens,"
        " COALESCE(SUM(output_tokens), 0) AS output_tokens,"
        " COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,"
        " COALESCE(SUM(cache_creation_tokens), 0) AS cache_creation_tokens"
        " FROM aihelms.cost_summary_daily"
        f" WHERE {' AND '.join(filters)}"
        " GROUP BY 1, 2 ORDER BY 1, 2"
    )
    result = await session.execute(sql, params)
    return [
        {
            "period": str(r[0]),
            "cost_type": r[1] or "all",
            "cost": float(r[2]),
            "requests": int(r[3]),
            "input_tokens": int(r[4]),
            "output_tokens": int(r[5]),
            "cache_read_tokens": int(r[6]),
            "cache_creation_tokens": int(r[7]),
        }
        for r in result.fetchall()
    ]


async def get_period_token_stats(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> dict:
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "token_stats"
    )
    sql = text(
        "SELECT COALESCE(SUM(c.input_tokens),0), COALESCE(SUM(c.output_tokens),0),"
        " COALESCE(SUM(c.cache_read_tokens),0),"
        " COALESCE(SUM(c.cache_creation_tokens),0)"
        " FROM aihelms.cost_summary_daily c"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        f"{scope_filter}"
    )
    row = (await session.execute(sql, params)).one()
    input_tokens, output_tokens = int(row[0]), int(row[1])
    cache_read_tokens, cache_creation_tokens = int(row[2]), int(row[3])
    return {
        "total": (
            input_tokens
            + output_tokens
            + cache_read_tokens
            + cache_creation_tokens
        ),
        "input": input_tokens,
        "output": output_tokens,
        "cache_read": cache_read_tokens,
        "cache_creation": cache_creation_tokens,
    }


async def get_dept_ranking(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    return await get_scope_overview(session, start_date, end_date, "department")


async def get_scope_overview(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date}
    if dimension == "project":
        id_filter = build_id_filter("p.id", project_ids, params, "overview_project")
        sql = text(
            "SELECT p.id, p.name, p.name AS path,"
            " COUNT(DISTINCT up.user_id) FILTER (WHERE u.is_active = true) AS total_users,"
            " COUNT(DISTINCT c.user_id) FILTER (WHERE u.is_active = true) AS active_users,"
            " COALESCE(SUM(c.internal_cost), 0) AS total_cost,"
            " COALESCE(string_agg(DISTINCT NULLIF(u.display_name, ''), '、')"
            " FILTER (WHERE c.user_id IS NOT NULL AND u.is_active = true), '') AS active_people"
            " FROM aihelms.projects p"
            " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
            " LEFT JOIN aihelms.users u ON u.id = up.user_id"
            " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = up.user_id"
            " AND c.summary_date >= :start AND c.summary_date <= :end"
            f" WHERE p.is_active = true{id_filter}"
            " GROUP BY p.id, p.name ORDER BY total_cost DESC"
        )
    else:
        id_filter = build_id_filter("d.id", department_ids, params, "overview_department")
        sql = text(
            "WITH RECURSIVE dept_tree AS ("
            " SELECT id, name, parent_id, name::text AS path"
            " FROM aihelms.departments WHERE parent_id IS NULL"
            " UNION ALL"
            " SELECT d.id, d.name, d.parent_id, (dt.path || ' / ' || d.name)::text"
            " FROM aihelms.departments d JOIN dept_tree dt ON dt.id = d.parent_id"
            ")"
            " SELECT d.id, d.name, COALESCE(dt.path, d.name) AS path,"
            " COUNT(DISTINCT ud.user_id) FILTER (WHERE u.is_active = true) AS total_users,"
            " COUNT(DISTINCT c.user_id) FILTER (WHERE u.is_active = true) AS active_users,"
            " COALESCE(SUM(c.internal_cost), 0) AS total_cost,"
            " COALESCE(string_agg(DISTINCT NULLIF(u.display_name, ''), '、')"
            " FILTER (WHERE c.user_id IS NOT NULL AND u.is_active = true), '') AS active_people"
            " FROM aihelms.departments d"
            " LEFT JOIN dept_tree dt ON dt.id = d.id"
            " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
            " LEFT JOIN aihelms.users u ON u.id = ud.user_id"
            " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = ud.user_id"
            " AND c.summary_date >= :start AND c.summary_date <= :end"
            f" WHERE d.is_active = true{id_filter}"
            " GROUP BY d.id, d.name, dt.path ORDER BY total_cost DESC"
        )
    result = await session.execute(sql, params)
    rows = []
    for r in result.fetchall():
        active_people = [name for name in str(r[6] or "").split("、") if name]
        rows.append(
            {
                "id": int(r[0]),
                "name": r[1],
                "path": r[2] or r[1],
                "total_users": int(r[3]),
                "active_users": int(r[4]),
                "total_cost": float(r[5]),
                "active_people": active_people[:8],
            }
        )
    return rows


async def get_daily_active_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "daily_active"
    )
    sql = text(
        "SELECT c.summary_date::date AS d, COUNT(DISTINCT c.user_id) AS dau"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.users u ON u.id = c.user_id AND u.is_active = true"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end AND c.user_id IS NOT NULL"
        f"{scope_filter}"
        " GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    raw = {r[0]: int(r[1]) for r in result.fetchall()}
    days = (end_date - start_date).days + 1
    return [
        {"date": str(day), "dau": raw.get(day, 0)}
        for day in (start_date + datetime.timedelta(days=i) for i in range(days))
    ]


async def get_user_call_counts(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "user_calls"
    )
    sql = text(
        "SELECT c.user_id, SUM(c.total_requests) AS calls FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.users u ON u.id = c.user_id AND u.is_active = true"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end AND c.user_id IS NOT NULL"
        f"{scope_filter} GROUP BY c.user_id"
    )
    result = await session.execute(sql, params)
    return [{"user_id": int(r[0]), "calls": int(r[1])} for r in result.fetchall()]


async def get_daily_heavy_user_ratio(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    heavy_threshold: int = 10,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date, "threshold": heavy_threshold}
    scope_filter = build_scope_filter(
        "c.user_id", department_ids, project_ids, params, "heavy_users"
    )
    sql = text(
        "SELECT d, COUNT(*) FILTER (WHERE calls >= :threshold)::float"
        " / NULLIF(COUNT(*), 0) * 100 AS ratio"
        " FROM ("
        "   SELECT c.summary_date::date AS d, c.user_id, SUM(c.total_requests) AS calls"
        "   FROM aihelms.cost_summary_daily c"
        "   JOIN aihelms.users u ON u.id = c.user_id AND u.is_active = true"
        "   WHERE c.summary_date >= :start AND c.summary_date <= :end AND c.user_id IS NOT NULL"
        f"{scope_filter}"
        "   GROUP BY 1, 2"
        " ) t GROUP BY d ORDER BY d"
    )
    result = await session.execute(sql, params)
    raw = {r[0]: round(float(r[1] or 0), 1) for r in result.fetchall()}
    days = (end_date - start_date).days + 1
    return [
        {"date": str(day), "ratio": raw.get(day, 0)}
        for day in (start_date + datetime.timedelta(days=i) for i in range(days))
    ]


async def get_dept_adoption_table(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
) -> list[dict]:
    days = max((end_date - start_date).days + 1, 1)
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("d.id", department_ids, params, "adoption_department")
    sql = text(
        "SELECT d.id, d.name,"
        " COUNT(DISTINCT ud.user_id) FILTER (WHERE u.is_active = true) AS total,"
        " COUNT(DISTINCT c.user_id) FILTER (WHERE u.is_active = true) AS active,"
        " COALESCE(SUM(c.total_requests) FILTER (WHERE u.is_active = true), 0) AS total_calls"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.users u ON u.id = ud.user_id"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = ud.user_id"
        " AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE d.is_active = true{id_filter} GROUP BY d.id, d.name ORDER BY active DESC"
    )
    result = await session.execute(sql, params)
    rows = []
    for r in result.fetchall():
        total = int(r[2])
        active = int(r[3])
        rows.append({
            "id": r[0], "name": r[1], "total": total, "active": active,
            "coverage": round(active / total * 100, 1) if total > 0 else 0,
            "daily_calls": round(int(r[4]) / days, 1),
        })
    return rows


async def get_project_adoption_table(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    project_ids: list[int] | None = None,
) -> list[dict]:
    days = max((end_date - start_date).days + 1, 1)
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("p.id", project_ids, params, "adoption_project")
    sql = text(
        "SELECT p.id, p.name,"
        " COUNT(DISTINCT up.user_id) FILTER (WHERE u.is_active = true) AS total,"
        " COUNT(DISTINCT c.user_id) FILTER (WHERE u.is_active = true) AS active,"
        " COALESCE(SUM(c.total_requests) FILTER (WHERE u.is_active = true), 0) AS total_calls"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.users u ON u.id = up.user_id"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = up.user_id"
        " AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE p.is_active = true{id_filter} GROUP BY p.id, p.name ORDER BY active DESC"
    )
    result = await session.execute(sql, params)
    rows = []
    for r in result.fetchall():
        total = int(r[2])
        active = int(r[3])
        rows.append({
            "id": r[0], "name": r[1], "total": total, "active": active,
            "coverage": round(active / total * 100, 1) if total > 0 else 0,
            "daily_calls": round(int(r[4]) / days, 1),
        })
    return rows


async def get_adoption_scope_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    scope_id: int,
) -> list[dict]:
    if dimension == "project":
        join_sql = "JOIN aihelms.user_projects up ON up.user_id = u.id AND up.project_id = :scope_id"
    else:
        join_sql = "JOIN aihelms.user_departments ud ON ud.user_id = u.id AND ud.department_id = :scope_id"
    sql = text(
        f"SELECT u.id, u.username, u.display_name, u.position,"
        f" COALESCE(d.name, '') AS department,"
        f" COALESCE(SUM(c.total_requests), 0) AS total_calls,"
        f" COALESCE(SUM(CASE WHEN c.cost_type = 'llm' THEN c.total_requests ELSE 0 END), 0) AS llm_calls,"
        f" COALESCE(SUM(CASE WHEN c.cost_type = 'mcp' THEN c.total_requests ELSE 0 END), 0) AS mcp_calls,"
        f" MAX(c.summary_date) AS last_active"
        f" FROM aihelms.users u {join_sql}"
        f" LEFT JOIN aihelms.user_departments ud_main ON ud_main.user_id = u.id"
        f" LEFT JOIN aihelms.departments d ON d.id = ud_main.department_id"
        f" LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = u.id"
        f" AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE u.is_active = true"
        f" GROUP BY u.id, u.username, u.display_name, u.position, d.name"
        f" ORDER BY total_calls DESC, u.id DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date, "scope_id": scope_id})
    return [
        {
            "id": r[0],
            "username": r[1],
            "name": r[2] or r[1],
            "position": r[3] or "",
            "department": r[4] or "",
            "total_calls": int(r[5] or 0),
            "llm_calls": int(r[6] or 0),
            "mcp_calls": int(r[7] or 0),
            "last_active": str(r[8].date() if hasattr(r[8], "date") else r[8]) if r[8] else "",
        }
        for r in result.fetchall()
    ]



async def get_agent_hotness(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end_next": end_date + datetime.timedelta(days=1)}
    log_filter = build_scope_filter(
        "l.user_id", department_ids, project_ids, params, "agent_usage"
    )
    if dimension == "project":
        scope_join = "LEFT JOIN aihelms.user_projects uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.projects scope ON scope.id = uscope.project_id"
    else:
        scope_join = "LEFT JOIN aihelms.user_departments uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.departments scope ON scope.id = uscope.department_id"
    sql = text(
        f"SELECT a.id, a.name, a.platform,"
        f" COALESCE(STRING_AGG(DISTINCT scope.name, ' / ') FILTER (WHERE scope.name IS NOT NULL), '') AS scope_names,"
        f" COUNT(DISTINCT l.user_id) AS user_count, COUNT(l.id) AS monthly_calls, a.created_at"
        f" FROM aihelms.agents a"
        f" LEFT JOIN aihelms.agent_usage_logs l ON l.agent_id = a.id"
        f" AND l.created_at >= :start AND l.created_at < :end_next"
        f" {log_filter}"
        f" {scope_join}"
        f" WHERE a.is_active = true"
        f" GROUP BY a.id, a.name, a.platform, a.created_at"
        f" ORDER BY monthly_calls DESC"
    )
    result = await session.execute(sql, params)
    today = date.today()
    return [
        {
            "id": r[0], "name": r[1], "platform": r[2], "department": r[3] or "",
            "scope_names": r[3] or "", "user_count": int(r[4]), "monthly_calls": int(r[5]),
            "days_online": (today - r[6].date()).days if r[6] else 0,
        }
        for r in result.fetchall()
    ]


async def get_mcp_hotness(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end_next": end_date + datetime.timedelta(days=1)}
    log_filter = build_scope_filter(
        "l.user_id", department_ids, project_ids, params, "mcp_usage"
    )
    if dimension == "project":
        scope_join = "LEFT JOIN aihelms.user_projects uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.projects scope ON scope.id = uscope.project_id"
    else:
        scope_join = "LEFT JOIN aihelms.user_departments uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.departments scope ON scope.id = uscope.department_id"
    sql = text(
        f"SELECT s.id, s.name, COUNT(DISTINCT l.user_id) AS user_count,"
        f" COUNT(l.id) AS monthly_calls, COALESCE(SUM(l.internal_cost), 0) AS cost,"
        f" COALESCE(STRING_AGG(DISTINCT scope.name, ' / ') FILTER (WHERE scope.name IS NOT NULL), '') AS scope_names"
        f" FROM aihelms.mcp_servers s"
        f" LEFT JOIN aihelms.mcp_call_logs l ON l.server_id = s.id"
        f" AND l.called_at >= :start AND l.called_at < :end_next"
        f" {log_filter}"
        f" {scope_join}"
        f" WHERE s.is_active = true GROUP BY s.id, s.name ORDER BY monthly_calls DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"id": r[0], "name": r[1], "user_count": int(r[2]), "monthly_calls": int(r[3]), "cost": float(r[4]), "scope_names": r[5] or ""}
        for r in result.fetchall()
    ]


async def get_skill_hotness(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end_next": end_date + datetime.timedelta(days=1)}
    log_filter = build_scope_filter(
        "l.user_id", department_ids, project_ids, params, "skill_usage"
    )
    if dimension == "project":
        scope_join = "LEFT JOIN aihelms.user_projects uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.projects scope ON scope.id = uscope.project_id"
    else:
        scope_join = "LEFT JOIN aihelms.user_departments uscope ON uscope.user_id = l.user_id LEFT JOIN aihelms.departments scope ON scope.id = uscope.department_id"
    sql = text(
        f"SELECT s.id, s.name, COUNT(DISTINCT l.user_id) AS operator_count, COUNT(l.id) AS monthly_downloads,"
        f" COALESCE(STRING_AGG(DISTINCT scope.name, ' / ') FILTER (WHERE scope.name IS NOT NULL), '') AS scope_names"
        f" FROM aihelms.skills s"
        f" LEFT JOIN aihelms.skill_usage_logs l ON l.skill_id = s.id"
        f" AND l.created_at >= :start AND l.created_at < :end_next"
        f" {log_filter}"
        f" {scope_join}"
        f" WHERE s.is_active = true GROUP BY s.id, s.name"
        f" ORDER BY monthly_downloads DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"id": r[0], "name": r[1], "install_count": int(r[2]), "monthly_downloads": int(r[3]), "scope_names": r[4] or ""}
        for r in result.fetchall()
    ]


async def get_unused_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    if dimension == "project":
        scope_join = "JOIN aihelms.user_projects uscope ON uscope.user_id = u.id JOIN aihelms.projects scope ON scope.id = uscope.project_id"
    else:
        scope_join = "JOIN aihelms.user_departments uscope ON uscope.user_id = u.id JOIN aihelms.departments scope ON scope.id = uscope.department_id"
    params: dict = {"start": start_date, "end": end_date}
    scope_filter = build_id_filter(
        "scope.id",
        project_ids if dimension == "project" else department_ids,
        params,
        "unused_scope",
    )
    sql = text(
        f"SELECT u.id, u.display_name, COALESCE(STRING_AGG(DISTINCT scope.name, ' / '), '') AS scope_names, u.position,"
        f" true AS has_key,"
        f" (SELECT MAX(c.summary_date) FROM aihelms.cost_summary_daily c WHERE c.user_id = u.id) AS last_active"
        f" FROM aihelms.users u {scope_join}"
        f" WHERE u.is_active = true"
        f" {scope_filter}"
        f" AND EXISTS (SELECT 1 FROM aihelms.ai_keys k WHERE k.owner_type = 'user' AND k.owner_id = u.id AND k.is_active = true)"
        f" AND u.id NOT IN (SELECT DISTINCT user_id FROM aihelms.cost_summary_daily"
        f" WHERE summary_date >= :start AND summary_date <= :end AND user_id IS NOT NULL)"
        f" GROUP BY u.id, u.display_name, u.position ORDER BY u.display_name"
    )
    result = await session.execute(sql, params)
    return [
        {
            "display_name": r[1], "department": r[2], "position": r[3],
            "has_key": bool(r[4]), "last_active": str(r[5]) if r[5] else None,
        }
        for r in result.fetchall()
    ]
