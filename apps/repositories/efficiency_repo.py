"""AI 效能数据查询仓库层。"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey, CostSummaryDaily, EfficiencyReport, EfficiencySuggestion, User

logger = logging.getLogger(__name__)


async def get_total_user_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )
    return result.scalar() or 0


async def get_active_user_ids(
    session: AsyncSession, start_date: date, end_date: date
) -> set[int]:
    result = await session.execute(
        select(func.distinct(CostSummaryDaily.user_id)).where(
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
            CostSummaryDaily.user_id.isnot(None),
        )
    )
    return {row[0] for row in result.fetchall()}


async def get_total_cost(
    session: AsyncSession, start_date: date, end_date: date
) -> float:
    result = await session.execute(
        select(func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0)).where(
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
        )
    )
    return float(result.scalar() or 0)


async def get_daily_cost_and_users(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT summary_date::date AS d, COUNT(DISTINCT user_id) AS active_users,"
        " COALESCE(SUM(internal_cost), 0) AS cost"
        " FROM aihelms.cost_summary_daily"
        " WHERE summary_date >= :start AND summary_date <= :end AND user_id IS NOT NULL"
        " GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [{"date": str(r[0]), "active_users": int(r[1]), "cost": float(r[2])} for r in result.fetchall()]


async def get_dept_ranking(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT d.id, d.name, COUNT(DISTINCT ud.user_id) AS total_users,"
        " COUNT(DISTINCT c.user_id) AS active_users, COALESCE(SUM(c.internal_cost), 0) AS total_cost"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = ud.user_id"
        " AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE d.is_active = true GROUP BY d.id, d.name ORDER BY total_cost DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"id": r[0], "name": r[1], "total_users": int(r[2]), "active_users": int(r[3]), "total_cost": float(r[4])}
        for r in result.fetchall()
    ]


async def get_daily_active_users(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT summary_date::date AS d, COUNT(DISTINCT user_id) AS dau"
        " FROM aihelms.cost_summary_daily"
        " WHERE summary_date >= :start AND summary_date <= :end AND user_id IS NOT NULL"
        " GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [{"date": str(r[0]), "dau": int(r[1])} for r in result.fetchall()]


async def get_user_call_counts(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT user_id, SUM(total_requests) AS calls FROM aihelms.cost_summary_daily"
        " WHERE summary_date >= :start AND summary_date <= :end AND user_id IS NOT NULL"
        " GROUP BY user_id"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [{"user_id": int(r[0]), "calls": int(r[1])} for r in result.fetchall()]


async def get_dept_adoption_table(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    days = max((end_date - start_date).days + 1, 1)
    sql = text(
        "SELECT d.id, d.name, COUNT(DISTINCT ud.user_id) AS total,"
        " COUNT(DISTINCT c.user_id) AS active, COALESCE(SUM(c.total_requests), 0) AS total_calls"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = ud.user_id"
        " AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE d.is_active = true GROUP BY d.id, d.name ORDER BY active DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    rows = []
    for r in result.fetchall():
        total = int(r[2])
        active = int(r[3])
        rows.append({
            "name": r[1], "total": total, "active": active,
            "coverage": round(active / total * 100, 1) if total > 0 else 0,
            "daily_calls": round(int(r[4]) / days, 1),
        })
    return rows


async def get_project_adoption_table(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    days = max((end_date - start_date).days + 1, 1)
    sql = text(
        "SELECT p.id, p.name, COUNT(DISTINCT up.user_id) AS total,"
        " COUNT(DISTINCT c.user_id) AS active, COALESCE(SUM(c.total_requests), 0) AS total_calls"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.user_id = up.user_id"
        " AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE p.is_active = true GROUP BY p.id, p.name ORDER BY active DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    rows = []
    for r in result.fetchall():
        total = int(r[2])
        active = int(r[3])
        rows.append({
            "name": r[1], "total": total, "active": active,
            "coverage": round(active / total * 100, 1) if total > 0 else 0,
            "daily_calls": round(int(r[4]) / days, 1),
        })
    return rows


async def get_agent_hotness(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT a.id, a.name, a.platform, COALESCE(d.name, '') AS department,"
        " a.user_count, COUNT(l.id) AS monthly_calls, a.created_at"
        " FROM aihelms.agents a"
        " LEFT JOIN aihelms.departments d ON d.id = a.department_id"
        " LEFT JOIN aihelms.agent_usage_logs l ON l.agent_id = a.id"
        " AND l.created_at >= :start AND l.created_at <= :end"
        " WHERE a.is_active = true"
        " GROUP BY a.id, a.name, a.platform, d.name, a.user_count, a.created_at"
        " ORDER BY monthly_calls DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    today = date.today()
    return [
        {
            "name": r[1], "platform": r[2], "department": r[3],
            "user_count": int(r[4]), "monthly_calls": int(r[5]),
            "days_online": (today - r[6].date()).days if r[6] else 0,
        }
        for r in result.fetchall()
    ]


async def get_mcp_hotness(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT s.id, s.name, COUNT(DISTINCT l.user_id) AS user_count,"
        " COUNT(l.id) AS monthly_calls, COALESCE(SUM(l.internal_cost), 0) AS cost"
        " FROM aihelms.mcp_servers s"
        " LEFT JOIN aihelms.mcp_call_logs l ON l.server_id = s.id"
        " AND l.called_at >= :start AND l.called_at <= :end"
        " WHERE s.is_active = true GROUP BY s.id, s.name ORDER BY monthly_calls DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"name": r[1], "user_count": int(r[2]), "monthly_calls": int(r[3]), "cost": float(r[4])}
        for r in result.fetchall()
    ]


async def get_skill_hotness(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT s.id, s.name, s.install_count, COUNT(l.id) AS monthly_downloads"
        " FROM aihelms.skills s"
        " LEFT JOIN aihelms.skill_usage_logs l ON l.skill_id = s.id"
        " AND l.created_at >= :start AND l.created_at <= :end"
        " WHERE s.is_active = true GROUP BY s.id, s.name, s.install_count"
        " ORDER BY monthly_downloads DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"name": r[1], "install_count": int(r[2]), "monthly_downloads": int(r[3])}
        for r in result.fetchall()
    ]


async def get_unused_users(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT u.id, u.display_name, COALESCE(d.name, '') AS department, u.position,"
        " CASE WHEN EXISTS (SELECT 1 FROM aihelms.ai_keys k"
        " WHERE k.owner_type = 'user' AND k.owner_id = u.id AND k.is_active = true)"
        " THEN true ELSE false END AS has_key,"
        " (SELECT MAX(c.summary_date) FROM aihelms.cost_summary_daily c WHERE c.user_id = u.id) AS last_active"
        " FROM aihelms.users u"
        " LEFT JOIN aihelms.user_departments ud ON ud.user_id = u.id"
        " LEFT JOIN aihelms.departments d ON d.id = ud.department_id"
        " WHERE u.is_active = true AND u.id NOT IN"
        " (SELECT DISTINCT user_id FROM aihelms.cost_summary_daily"
        " WHERE summary_date >= :start AND summary_date <= :end AND user_id IS NOT NULL)"
        " ORDER BY u.display_name"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {
            "display_name": r[1], "department": r[2], "position": r[3],
            "has_key": bool(r[4]), "last_active": str(r[5]) if r[5] else None,
        }
        for r in result.fetchall()
    ]


def _build_cost_filters(
    start_date: date, end_date: date, cost_type: str | None, department_id: int | None,
    table_alias: str = "",
) -> tuple[str, dict]:
    prefix = f"{table_alias}." if table_alias else ""
    filters = f"WHERE {prefix}summary_date >= :start AND {prefix}summary_date <= :end"
    params: dict = {"start": start_date, "end": end_date}
    if cost_type and cost_type != "all":
        filters += f" AND {prefix}cost_type = :cost_type"
        params["cost_type"] = cost_type
    if department_id:
        filters += f" AND {prefix}department_id = :dept_id"
        params["dept_id"] = department_id
    return filters, params


async def get_cost_trend(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id)
    sql = text(
        f"SELECT summary_date::date AS d, cost_type, COALESCE(SUM(internal_cost), 0) AS cost"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY 1, 2 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    return [{"date": str(r[0]), "cost_type": r[1], "cost": float(r[2])} for r in result.fetchall()]


async def get_cost_by_type(
    session: AsyncSession, start_date: date, end_date: date, department_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, None, department_id)
    sql = text(
        f"SELECT cost_type, COALESCE(SUM(internal_cost), 0) AS cost"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY cost_type ORDER BY cost DESC"
    )
    result = await session.execute(sql, params)
    return [{"name": r[0], "value": float(r[1])} for r in result.fetchall()]


async def get_cost_by_dept(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS cost"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.departments d ON d.id = c.department_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        " GROUP BY d.name ORDER BY cost DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [{"name": r[0], "value": float(r[1])} for r in result.fetchall()]


async def get_dept_per_capita_cost(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS cost, COUNT(DISTINCT c.user_id) AS users"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.departments d ON d.id = c.department_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end AND c.user_id IS NOT NULL"
        " GROUP BY d.name ORDER BY cost DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {"name": r[0], "value": round(float(r[1]) / int(r[2]), 2) if int(r[2]) > 0 else 0}
        for r in result.fetchall()
    ]


async def get_cost_detail_by_department(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c")
    sql = text(
        f"SELECT d.name, COALESCE(SUM(c.internal_cost), 0) AS cost,"
        f" COALESCE(SUM(c.total_requests), 0) AS requests, COUNT(DISTINCT c.user_id) AS users"
        f" FROM aihelms.cost_summary_daily c"
        f" JOIN aihelms.departments d ON d.id = c.department_id"
        f" {filters} GROUP BY d.name ORDER BY cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "name": r[0], "cost": float(r[1]), "requests": int(r[2]), "users": int(r[3]),
            "per_capita": round(float(r[1]) / int(r[3]), 2) if int(r[3]) > 0 else 0,
        }
        for r in result.fetchall()
    ]


async def get_cost_detail_by_model(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id, "c")
    sql = text(
        f"SELECT c.model, COALESCE(SUM(c.internal_cost), 0) AS cost,"
        f" COALESCE(SUM(c.total_requests), 0) AS requests,"
        f" COALESCE(SUM(c.input_tokens), 0) AS input_tokens,"
        f" COALESCE(SUM(c.output_tokens), 0) AS output_tokens"
        f" FROM aihelms.cost_summary_daily c"
        f" {filters} AND c.model IS NOT NULL GROUP BY c.model ORDER BY cost DESC"
    )
    result = await session.execute(sql, params)
    return [
        {"model": r[0], "cost": float(r[1]), "requests": int(r[2]),
         "input_tokens": int(r[3]), "output_tokens": int(r[4])}
        for r in result.fetchall()
    ]


async def get_cost_detail_by_date(
    session: AsyncSession, start_date: date, end_date: date,
    cost_type: str | None = None, department_id: int | None = None,
) -> list[dict]:
    filters, params = _build_cost_filters(start_date, end_date, cost_type, department_id)
    sql = text(
        f"SELECT summary_date::date AS d, COALESCE(SUM(internal_cost), 0) AS cost,"
        f" COALESCE(SUM(total_requests), 0) AS requests, COUNT(DISTINCT user_id) AS users"
        f" FROM aihelms.cost_summary_daily {filters} GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    return [
        {"date": str(r[0]), "cost": float(r[1]), "requests": int(r[2]), "users": int(r[3])}
        for r in result.fetchall()
    ]


async def get_all_keys_with_budget(session: AsyncSession) -> list[AiKey]:
    result = await session.execute(
        select(AiKey).where(AiKey.is_active.is_(True), AiKey.budget_limit.isnot(None), AiKey.budget_limit > 0)
    )
    return list(result.scalars().all())


async def get_dept_budget_usage(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT d.id, d.name, COALESCE(SUM(k.budget_limit), 0) AS budget,"
        " COALESCE(SUM(k.budget_used), 0) AS used"
        " FROM aihelms.departments d"
        " JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = ud.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE d.is_active = true GROUP BY d.id, d.name ORDER BY used DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [{"id": r[0], "name": r[1], "budget": float(r[2]), "used": float(r[3])} for r in result.fetchall()]


async def get_project_budget_usage(session: AsyncSession) -> list[dict]:
    sql = text(
        "SELECT p.id, p.name, COALESCE(SUM(k.budget_limit), 0) AS budget,"
        " COALESCE(SUM(k.budget_used), 0) AS used"
        " FROM aihelms.projects p"
        " JOIN aihelms.user_projects up ON up.project_id = p.id"
        " JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = up.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE p.is_active = true GROUP BY p.id, p.name ORDER BY used DESC"
    )
    result = await session.execute(sql)
    return [{"id": r[0], "name": r[1], "budget": float(r[2]), "used": float(r[3])} for r in result.fetchall()]


async def get_key_top10_budget(session: AsyncSession) -> list[dict]:
    sql = text(
        "SELECT k.id, k.name, u.display_name AS owner, k.key_type, k.budget_limit, k.budget_used"
        " FROM aihelms.ai_keys k"
        " LEFT JOIN aihelms.users u ON u.id = k.owner_id AND k.owner_type = 'user'"
        " WHERE k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " ORDER BY k.budget_used DESC LIMIT 10"
    )
    result = await session.execute(sql)
    return [
        {
            "name": r[1], "owner": r[2] or "", "key_type": r[3],
            "budget": float(r[4]), "used": float(r[5]),
            "rate": round(float(r[5]) / float(r[4]) * 100, 1) if float(r[4]) > 0 else 0,
        }
        for r in result.fetchall()
    ]


async def get_cumulative_cost_by_date(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    sql = text(
        "SELECT summary_date::date AS d, COALESCE(SUM(internal_cost), 0) AS daily_cost"
        " FROM aihelms.cost_summary_daily"
        " WHERE summary_date >= :start AND summary_date <= :end GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    rows = []
    cumulative = 0.0
    for r in result.fetchall():
        cumulative += float(r[1])
        rows.append({"date": str(r[0]), "actual": round(cumulative, 2)})
    return rows


async def list_reports(
    session: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[EfficiencyReport], int]:
    count_result = await session.execute(select(func.count(EfficiencyReport.id)))
    total = count_result.scalar() or 0
    q = (
        select(EfficiencyReport)
        .order_by(EfficiencyReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(q)
    return list(result.scalars().all()), total


async def get_report_by_id(session: AsyncSession, report_id: int) -> EfficiencyReport | None:
    return await session.get(EfficiencyReport, report_id)


async def create_report(session: AsyncSession, report: EfficiencyReport) -> EfficiencyReport:
    session.add(report)
    await session.flush()
    return report


async def list_suggestions_by_report(session: AsyncSession, report_id: int) -> list[EfficiencySuggestion]:
    result = await session.execute(
        select(EfficiencySuggestion).where(EfficiencySuggestion.report_id == report_id).order_by(EfficiencySuggestion.id)
    )
    return list(result.scalars().all())


async def update_suggestion_status(
    session: AsyncSession, suggestion_id: int, status: str, note: str, updated_by: int,
) -> EfficiencySuggestion | None:
    suggestion = await session.get(EfficiencySuggestion, suggestion_id)
    if not suggestion:
        return None
    suggestion.status = status
    suggestion.status_note = note
    suggestion.status_updated_by = updated_by
    suggestion.status_updated_at = datetime.now(timezone.utc)
    await session.flush()
    return suggestion
