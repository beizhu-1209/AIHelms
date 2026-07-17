"""Efficiency budget repository."""

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey
from repositories.efficiency_scope_filter import bind_scope_ids, build_id_filter


async def get_all_keys_with_budget(session: AsyncSession) -> list[AiKey]:
    result = await session.execute(
        select(AiKey).where(AiKey.is_active.is_(True), AiKey.budget_limit.isnot(None), AiKey.budget_limit > 0)
    )
    return list(result.scalars().all())


async def get_scope_budget_key_ids(
    session: AsyncSession,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> set[int] | None:
    if not department_ids and not project_ids:
        return None
    params: dict = {}
    conditions = []
    department_values = bind_scope_ids(params, "budget_department", department_ids)
    if department_values:
        conditions.append(
            "((k.owner_type = 'department' AND k.owner_id IN ("
            f"{department_values})) OR (k.owner_type = 'user' AND EXISTS ("
            "SELECT 1 FROM aihelms.user_departments ud WHERE ud.user_id = k.owner_id"
            f" AND ud.department_id IN ({department_values}))))"
        )
    project_values = bind_scope_ids(params, "budget_project", project_ids)
    if project_values:
        conditions.append(
            "((k.owner_type = 'project' AND k.owner_id IN ("
            f"{project_values})) OR (k.owner_type = 'user' AND EXISTS ("
            "SELECT 1 FROM aihelms.user_projects up WHERE up.user_id = k.owner_id"
            f" AND up.project_id IN ({project_values}))))"
        )
    sql = text(
        "SELECT DISTINCT k.id FROM aihelms.ai_keys k"
        " WHERE k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f" AND ({' OR '.join(conditions)})"
    )
    result = await session.execute(sql, params)
    return {int(row[0]) for row in result.fetchall()}


async def get_budget_used_for_keys(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    key_ids: list[int] | None = None,
) -> float:
    if key_ids == []:
        return 0.0
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("k.id", key_ids, params, "used_key")
    sql = text(
        "SELECT COALESCE(SUM(c.internal_cost), 0)"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.ai_keys k ON k.id = c.ai_key_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f"{id_filter}"
    )
    return float((await session.execute(sql, params)).scalar() or 0)


async def get_budget_used_for_key(session: AsyncSession, key_id: int, start_date: date, end_date: date) -> float:
    sql = text(
        "SELECT COALESCE(SUM(internal_cost), 0) FROM aihelms.cost_summary_daily"
        " WHERE ai_key_id = :key_id AND summary_date >= :start AND summary_date <= :end"
    )
    return float((await session.execute(sql, {"key_id": key_id, "start": start_date, "end": end_date})).scalar() or 0)


async def get_budget_usage_by_key(
    session: AsyncSession,
    key_ids: list[int],
    start_date: date,
    end_date: date,
) -> dict[int, float]:
    if not key_ids:
        return {}
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("c.ai_key_id", key_ids, params, "alert_key")
    sql = text(
        "SELECT c.ai_key_id, COALESCE(SUM(c.internal_cost), 0)"
        " FROM aihelms.cost_summary_daily c"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        f"{id_filter} GROUP BY c.ai_key_id"
    )
    result = await session.execute(sql, params)
    return {int(row[0]): float(row[1]) for row in result.fetchall()}


async def get_dept_budget_usage(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("d.id", department_ids, params, "budget_dept_row")
    project_values = bind_scope_ids(params, "budget_dept_project", project_ids)
    related_filter = ""
    if project_values:
        related_filter = (
            " AND EXISTS (SELECT 1 FROM aihelms.user_departments ud_scope"
            " JOIN aihelms.user_projects up_scope ON up_scope.user_id = ud_scope.user_id"
            " WHERE ud_scope.department_id = d.id"
            f" AND up_scope.project_id IN ({project_values}))"
        )
    row_filter = f"{id_filter}{related_filter}"
    sql = text(
        "WITH user_key_budget AS ("
        " SELECT d.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = ud.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f" WHERE d.is_active = true{row_filter} GROUP BY d.id"
        "), user_key_used AS ("
        " SELECT d.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = ud.user_id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE d.is_active = true{row_filter} GROUP BY d.id"
        "), scope_key_budget AS ("
        " SELECT d.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'department' AND k.owner_id = d.id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f" WHERE d.is_active = true{row_filter} GROUP BY d.id"
        "), scope_key_used AS ("
        " SELECT d.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'department' AND k.owner_id = d.id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE d.is_active = true{row_filter} GROUP BY d.id"
        ") SELECT d.id, d.name, COALESCE(ukb.budget,0), COALESCE(uku.used,0), COALESCE(ukb.key_count,0),"
        " COALESCE(skb.budget,0), COALESCE(sku.used,0), COALESCE(skb.key_count,0)"
        " FROM aihelms.departments d"
        " LEFT JOIN user_key_budget ukb ON ukb.id = d.id"
        " LEFT JOIN user_key_used uku ON uku.id = d.id"
        " LEFT JOIN scope_key_budget skb ON skb.id = d.id"
        " LEFT JOIN scope_key_used sku ON sku.id = d.id"
        f" WHERE d.is_active = true{row_filter} ORDER BY (COALESCE(uku.used,0) + COALESCE(sku.used,0)) DESC"
    )
    result = await session.execute(sql, params)
    rows = []
    for r in result.fetchall():
        user_budget, user_used = float(r[2]), float(r[3])
        scope_budget, scope_used = float(r[5]), float(r[6])
        rows.append({
            "id": r[0], "name": r[1], "budget": user_budget + scope_budget, "used": user_used + scope_used,
            "user_key_budget": user_budget, "user_key_used": user_used, "user_key_count": int(r[4]),
            "scope_key_budget": scope_budget, "scope_key_used": scope_used, "scope_key_count": int(r[7]),
        })
    return rows


async def get_project_budget_usage(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    project_ids: list[int] | None = None,
    department_ids: list[int] | None = None,
) -> list[dict]:
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("p.id", project_ids, params, "budget_project_row")
    department_values = bind_scope_ids(
        params, "budget_project_department", department_ids
    )
    related_filter = ""
    if department_values:
        related_filter = (
            " AND EXISTS (SELECT 1 FROM aihelms.user_projects up_scope"
            " JOIN aihelms.user_departments ud_scope ON ud_scope.user_id = up_scope.user_id"
            " WHERE up_scope.project_id = p.id"
            f" AND ud_scope.department_id IN ({department_values}))"
        )
    row_filter = f"{id_filter}{related_filter}"
    sql = text(
        "WITH user_key_budget AS ("
        " SELECT p.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = up.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f" WHERE p.is_active = true{row_filter} GROUP BY p.id"
        "), user_key_used AS ("
        " SELECT p.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = up.user_id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE p.is_active = true{row_filter} GROUP BY p.id"
        "), scope_key_budget AS ("
        " SELECT p.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'project' AND k.owner_id = p.id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f" WHERE p.is_active = true{row_filter} GROUP BY p.id"
        "), scope_key_used AS ("
        " SELECT p.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'project' AND k.owner_id = p.id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        f" WHERE p.is_active = true{row_filter} GROUP BY p.id"
        ") SELECT p.id, p.name, COALESCE(ukb.budget,0), COALESCE(uku.used,0), COALESCE(ukb.key_count,0),"
        " COALESCE(skb.budget,0), COALESCE(sku.used,0), COALESCE(skb.key_count,0)"
        " FROM aihelms.projects p"
        " LEFT JOIN user_key_budget ukb ON ukb.id = p.id"
        " LEFT JOIN user_key_used uku ON uku.id = p.id"
        " LEFT JOIN scope_key_budget skb ON skb.id = p.id"
        " LEFT JOIN scope_key_used sku ON sku.id = p.id"
        f" WHERE p.is_active = true{row_filter} ORDER BY (COALESCE(uku.used,0) + COALESCE(sku.used,0)) DESC"
    )
    result = await session.execute(sql, params)
    rows = []
    for r in result.fetchall():
        user_budget, user_used = float(r[2]), float(r[3])
        scope_budget, scope_used = float(r[5]), float(r[6])
        rows.append({
            "id": r[0], "name": r[1], "budget": user_budget + scope_budget, "used": user_used + scope_used,
            "user_key_budget": user_budget, "user_key_used": user_used, "user_key_count": int(r[4]),
            "scope_key_budget": scope_budget, "scope_key_used": scope_used, "scope_key_count": int(r[7]),
        })
    return rows


async def get_key_top10_budget(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    key_ids: list[int] | None = None,
) -> list[dict]:
    if key_ids == []:
        return []
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("k.id", key_ids, params, "top_key")
    sql = text(
        "SELECT k.id, k.name, k.owner_type, COALESCE(u.display_name, d.name, p.name, '') AS owner,"
        " k.key_type, k.budget_limit, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.ai_keys k"
        " LEFT JOIN aihelms.users u ON u.id = k.owner_id AND k.owner_type = 'user'"
        " LEFT JOIN aihelms.departments d ON d.id = k.owner_id AND k.owner_type = 'department'"
        " LEFT JOIN aihelms.projects p ON p.id = k.owner_id AND k.owner_type = 'project'"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        f"{id_filter}"
        " GROUP BY k.id, k.name, k.owner_type, u.display_name, d.name, p.name, k.key_type, k.budget_limit"
        " ORDER BY used DESC"
    )
    result = await session.execute(sql, params)
    return [
        {
            "name": r[1], "owner_type": r[2], "owner": r[3] or "", "key_type": r[4],
            "budget": float(r[5]), "used": float(r[6]),
            "rate": round(float(r[6]) / float(r[5]) * 100, 1) if float(r[5]) > 0 else 0,
        }
        for r in result.fetchall()
    ]


async def get_cumulative_cost_by_date(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    key_ids: list[int] | None = None,
) -> list[dict]:
    if key_ids == []:
        return []
    params: dict = {"start": start_date, "end": end_date}
    id_filter = build_id_filter("c.ai_key_id", key_ids, params, "trend_key")
    sql = text(
        "SELECT c.summary_date::date AS d, COALESCE(SUM(c.internal_cost), 0) AS daily_cost"
        " FROM aihelms.cost_summary_daily c"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        f"{id_filter} GROUP BY 1 ORDER BY 1"
    )
    result = await session.execute(sql, params)
    rows = []
    cumulative = 0.0
    for r in result.fetchall():
        cumulative += float(r[1])
        rows.append({"date": str(r[0]), "actual": round(cumulative, 2)})
    return rows
