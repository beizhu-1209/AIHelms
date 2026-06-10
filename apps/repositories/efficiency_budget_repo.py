"""Efficiency budget repository."""

from datetime import date

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey

async def get_all_keys_with_budget(session: AsyncSession) -> list[AiKey]:
    result = await session.execute(
        select(AiKey).where(AiKey.is_active.is_(True), AiKey.budget_limit.isnot(None), AiKey.budget_limit > 0)
    )
    return list(result.scalars().all())


async def get_budget_used_for_keys(session: AsyncSession, start_date: date, end_date: date) -> float:
    sql = text(
        "SELECT COALESCE(SUM(c.internal_cost), 0)"
        " FROM aihelms.cost_summary_daily c"
        " JOIN aihelms.ai_keys k ON k.id = c.ai_key_id"
        " WHERE c.summary_date >= :start AND c.summary_date <= :end"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
    )
    return float((await session.execute(sql, {"start": start_date, "end": end_date})).scalar() or 0)


async def get_budget_used_for_key(session: AsyncSession, key_id: int, start_date: date, end_date: date) -> float:
    sql = text(
        "SELECT COALESCE(SUM(internal_cost), 0) FROM aihelms.cost_summary_daily"
        " WHERE ai_key_id = :key_id AND summary_date >= :start AND summary_date <= :end"
    )
    return float((await session.execute(sql, {"key_id": key_id, "start": start_date, "end": end_date})).scalar() or 0)


async def get_dept_budget_usage(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "WITH user_key_budget AS ("
        " SELECT d.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = ud.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE d.is_active = true GROUP BY d.id"
        "), user_key_used AS ("
        " SELECT d.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.user_departments ud ON ud.department_id = d.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = ud.user_id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE d.is_active = true GROUP BY d.id"
        "), scope_key_budget AS ("
        " SELECT d.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'department' AND k.owner_id = d.id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE d.is_active = true GROUP BY d.id"
        "), scope_key_used AS ("
        " SELECT d.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.departments d"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'department' AND k.owner_id = d.id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE d.is_active = true GROUP BY d.id"
        ") SELECT d.id, d.name, COALESCE(ukb.budget,0), COALESCE(uku.used,0), COALESCE(ukb.key_count,0),"
        " COALESCE(skb.budget,0), COALESCE(sku.used,0), COALESCE(skb.key_count,0)"
        " FROM aihelms.departments d"
        " LEFT JOIN user_key_budget ukb ON ukb.id = d.id"
        " LEFT JOIN user_key_used uku ON uku.id = d.id"
        " LEFT JOIN scope_key_budget skb ON skb.id = d.id"
        " LEFT JOIN scope_key_used sku ON sku.id = d.id"
        " WHERE d.is_active = true ORDER BY (COALESCE(uku.used,0) + COALESCE(sku.used,0)) DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
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


async def get_project_budget_usage(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "WITH user_key_budget AS ("
        " SELECT p.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = up.user_id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE p.is_active = true GROUP BY p.id"
        "), user_key_used AS ("
        " SELECT p.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.user_projects up ON up.project_id = p.id"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'user' AND k.owner_id = up.user_id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE p.is_active = true GROUP BY p.id"
        "), scope_key_budget AS ("
        " SELECT p.id, COALESCE(SUM(k.budget_limit), 0) AS budget, COUNT(DISTINCT k.id) AS key_count"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'project' AND k.owner_id = p.id"
        " AND k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " WHERE p.is_active = true GROUP BY p.id"
        "), scope_key_used AS ("
        " SELECT p.id, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.projects p"
        " LEFT JOIN aihelms.ai_keys k ON k.owner_type = 'project' AND k.owner_id = p.id AND k.is_active = true"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE p.is_active = true GROUP BY p.id"
        ") SELECT p.id, p.name, COALESCE(ukb.budget,0), COALESCE(uku.used,0), COALESCE(ukb.key_count,0),"
        " COALESCE(skb.budget,0), COALESCE(sku.used,0), COALESCE(skb.key_count,0)"
        " FROM aihelms.projects p"
        " LEFT JOIN user_key_budget ukb ON ukb.id = p.id"
        " LEFT JOIN user_key_used uku ON uku.id = p.id"
        " LEFT JOIN scope_key_budget skb ON skb.id = p.id"
        " LEFT JOIN scope_key_used sku ON sku.id = p.id"
        " WHERE p.is_active = true ORDER BY (COALESCE(uku.used,0) + COALESCE(sku.used,0)) DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
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


async def get_key_top10_budget(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    sql = text(
        "SELECT k.id, k.name, k.owner_type, COALESCE(u.display_name, d.name, p.name, '') AS owner,"
        " k.key_type, k.budget_limit, COALESCE(SUM(c.internal_cost), 0) AS used"
        " FROM aihelms.ai_keys k"
        " LEFT JOIN aihelms.users u ON u.id = k.owner_id AND k.owner_type = 'user'"
        " LEFT JOIN aihelms.departments d ON d.id = k.owner_id AND k.owner_type = 'department'"
        " LEFT JOIN aihelms.projects p ON p.id = k.owner_id AND k.owner_type = 'project'"
        " LEFT JOIN aihelms.cost_summary_daily c ON c.ai_key_id = k.id AND c.summary_date >= :start AND c.summary_date <= :end"
        " WHERE k.is_active = true AND k.budget_limit IS NOT NULL AND k.budget_limit > 0"
        " GROUP BY k.id, k.name, k.owner_type, u.display_name, d.name, p.name, k.key_type, k.budget_limit"
        " ORDER BY used DESC"
    )
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    return [
        {
            "name": r[1], "owner_type": r[2], "owner": r[3] or "", "key_type": r[4],
            "budget": float(r[5]), "used": float(r[6]),
            "rate": round(float(r[6]) / float(r[5]) * 100, 1) if float(r[5]) > 0 else 0,
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


