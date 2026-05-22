"""AI 效能数据查询仓库层。"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import (
    CostSummaryDaily,
    EfficiencyReport,
    EfficiencySuggestion,
)


async def get_overview_kpi(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> dict:
    """总览 KPI：总成本、请求数、活跃用户、人均成本。"""
    result = await session.execute(
        select(
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0).label("total_cost"),
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0).label("total_requests"),
            func.count(func.distinct(CostSummaryDaily.user_id)).label("active_users"),
        ).where(
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
            CostSummaryDaily.user_id.isnot(None),
        )
    )
    row = result.one()
    total_cost = float(row.total_cost)
    total_requests = int(row.total_requests)
    active_users = int(row.active_users)
    avg_cost = total_cost / active_users if active_users > 0 else 0
    return {
        "total_cost": total_cost,
        "total_requests": total_requests,
        "active_users": active_users,
        "avg_cost_per_user": round(avg_cost, 4),
    }


async def get_trend(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    group_by: str = "day",
    cost_type: str | None = None,
) -> list[dict]:
    """成本趋势数据，按日/周/月聚合。"""
    trunc = "day" if group_by == "day" else ("week" if group_by == "week" else "month")
    filters = "WHERE summary_date >= :start AND summary_date <= :end"
    if cost_type:
        filters += " AND cost_type = :cost_type"
    sql = f"""
        SELECT date_trunc('{trunc}', summary_date)::date AS period,
               cost_type,
               COALESCE(SUM(internal_cost), 0) AS cost,
               COALESCE(SUM(total_requests), 0) AS requests
        FROM aihelms.cost_summary_daily
        {filters}
        GROUP BY 1, 2
        ORDER BY 1
    """
    params: dict = {"start": start_date, "end": end_date}
    if cost_type:
        params["cost_type"] = cost_type
    result = await session.execute(text(sql), params)
    return [
        {"period": str(r[0]), "cost_type": r[1], "cost": float(r[2]), "requests": int(r[3])}
        for r in result.fetchall()
    ]


async def get_composition(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """资源类型构成（LLM / MCP）。"""
    result = await session.execute(
        select(
            CostSummaryDaily.cost_type,
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0).label("cost"),
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0).label("requests"),
        ).where(
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
        ).group_by(CostSummaryDaily.cost_type)
    )
    return [
        {"cost_type": r[0], "cost": float(r[1]), "requests": int(r[2])}
        for r in result.fetchall()
    ]


async def get_ranking(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    limit: int = 10,
) -> list[dict]:
    """排行榜：按部门/用户/模型维度。"""
    dim_col_map = {
        "department": "department_id",
        "user": "user_id",
        "model": "model",
        "provider": "provider_id",
    }
    col = dim_col_map.get(dimension, "user_id")
    sql = f"""
        SELECT {col} AS dim_value,
               COALESCE(SUM(internal_cost), 0) AS cost,
               COALESCE(SUM(total_requests), 0) AS requests
        FROM aihelms.cost_summary_daily
        WHERE summary_date >= :start AND summary_date <= :end
          AND {col} IS NOT NULL
        GROUP BY {col}
        ORDER BY cost DESC
        LIMIT :lim
    """
    result = await session.execute(
        text(sql), {"start": start_date, "end": end_date, "lim": limit}
    )
    return [
        {"value": r[0], "cost": float(r[1]), "requests": int(r[2])}
        for r in result.fetchall()
    ]


async def get_key_type_comparison(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """主 Key vs 场景 Key 对比。"""
    result = await session.execute(
        select(
            CostSummaryDaily.key_type,
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0).label("cost"),
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0).label("requests"),
        ).where(
            CostSummaryDaily.summary_date >= start_date,
            CostSummaryDaily.summary_date <= end_date,
            CostSummaryDaily.key_type.isnot(None),
        ).group_by(CostSummaryDaily.key_type)
    )
    return [
        {"key_type": r[0], "cost": float(r[1]), "requests": int(r[2])}
        for r in result.fetchall()
    ]


async def get_analysis_by_dimension(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    cost_type: str | None = None,
) -> list[dict]:
    """多维度分析：按指定维度聚合。"""
    dim_col_map = {
        "department": "department_id",
        "project": "project_id",
        "user": "user_id",
        "model": "model",
        "provider": "provider_id",
        "resource_type": "cost_type",
        "key_type": "key_type",
    }
    col = dim_col_map.get(dimension, "user_id")
    filters = "WHERE summary_date >= :start AND summary_date <= :end"
    if cost_type:
        filters += " AND cost_type = :cost_type"
    sql = f"""
        SELECT {col} AS dim_value,
               COALESCE(SUM(internal_cost), 0) AS cost,
               COALESCE(SUM(external_cost), 0) AS ext_cost,
               COALESCE(SUM(total_requests), 0) AS requests,
               COALESCE(SUM(input_tokens), 0) AS in_tokens,
               COALESCE(SUM(output_tokens), 0) AS out_tokens
        FROM aihelms.cost_summary_daily
        {filters}
          AND {col} IS NOT NULL
        GROUP BY {col}
        ORDER BY cost DESC
    """
    params: dict = {"start": start_date, "end": end_date}
    if cost_type:
        params["cost_type"] = cost_type
    result = await session.execute(text(sql), params)
    return [
        {
            "value": r[0],
            "cost": float(r[1]),
            "external_cost": float(r[2]),
            "requests": int(r[3]),
            "input_tokens": int(r[4]),
            "output_tokens": int(r[5]),
        }
        for r in result.fetchall()
    ]


async def get_budget_overview(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> dict:
    """预算管控总览。"""
    sql = """
        SELECT
            COALESCE(SUM(internal_cost), 0) AS used,
            COALESCE(SUM(total_requests), 0) AS requests
        FROM aihelms.cost_summary_daily
        WHERE summary_date >= :start AND summary_date <= :end
    """
    result = await session.execute(text(sql), {"start": start_date, "end": end_date})
    row = result.one()
    return {"used": float(row[0]), "requests": int(row[1])}


async def list_reports(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[EfficiencyReport], int]:
    """报告列表。"""
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


async def get_report_by_id(
    session: AsyncSession, report_id: int
) -> EfficiencyReport | None:
    return await session.get(EfficiencyReport, report_id)


async def create_report(
    session: AsyncSession, report: EfficiencyReport
) -> EfficiencyReport:
    session.add(report)
    await session.flush()
    return report


async def list_suggestions_by_report(
    session: AsyncSession, report_id: int
) -> list[EfficiencySuggestion]:
    result = await session.execute(
        select(EfficiencySuggestion)
        .where(EfficiencySuggestion.report_id == report_id)
        .order_by(EfficiencySuggestion.id)
    )
    return list(result.scalars().all())


async def update_suggestion_status(
    session: AsyncSession,
    suggestion_id: int,
    status: str,
    note: str,
    updated_by: int,
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
