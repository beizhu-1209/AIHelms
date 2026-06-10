"""Dashboard repository."""

from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_range_status(session: AsyncSession, start_date: date, end_date: date) -> dict:
    """Return dashboard data range status from platform tables."""
    sql = text("""
        WITH platform_logs AS (
            SELECT user_id, 'llm' AS cost_type, internal_cost, external_cost
            FROM aihelms.llm_call_logs
            WHERE started_at::date >= :start
              AND started_at::date <= :end
            UNION ALL
            SELECT NULLIF(user_id, 0) AS user_id, 'mcp' AS cost_type, internal_cost, external_cost
            FROM aihelms.mcp_call_logs
            WHERE called_at::date >= :start
              AND called_at::date <= :end
        )
        SELECT
            COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) AS active_users,
            COUNT(*) AS requests,
            COUNT(*) FILTER (WHERE cost_type = 'llm') AS llm_requests,
            COUNT(*) FILTER (WHERE cost_type = 'mcp') AS mcp_requests,
            COALESCE(SUM(internal_cost), 0) AS internal_cost,
            COALESCE(SUM(external_cost), 0) AS external_cost
        FROM platform_logs
    """)
    row = (await session.execute(sql, {"start": start_date, "end": end_date})).one()
    return {
        "activeUsers": int(row.active_users or 0),
        "totalRequests": int(row.requests or 0),
        "llmRequests": int(row.llm_requests or 0),
        "mcpRequests": int(row.mcp_requests or 0),
        "internalCost": round(float(row.internal_cost or 0), 2),
        "externalCost": round(float(row.external_cost or 0), 2),
    }


async def get_request_trend(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    days = (end_date - start_date).days + 1
    if days <= 1:
        llm_sql = text("""
            SELECT EXTRACT(HOUR FROM started_at)::int AS h, COUNT(*) AS cnt
            FROM aihelms.llm_call_logs
            WHERE started_at::date = :day
            GROUP BY 1
        """)
        mcp_sql = text("""
            SELECT EXTRACT(HOUR FROM called_at)::int AS h, COUNT(*) AS cnt
            FROM aihelms.mcp_call_logs
            WHERE called_at::date = :day
            GROUP BY 1
        """)
        hourly = {h: 0 for h in range(24)}
        for result in [
            await session.execute(llm_sql, {"day": start_date}),
            await session.execute(mcp_sql, {"day": start_date}),
        ]:
            for row in result.fetchall():
                hourly[int(row[0])] += int(row[1])
        return [{"label": f"{h}:00", "hour": h, "requests": c} for h, c in hourly.items()]

    sql = text("""
        WITH platform_logs AS (
            SELECT started_at::date AS d
            FROM aihelms.llm_call_logs
            WHERE started_at::date >= :start
              AND started_at::date <= :end
            UNION ALL
            SELECT called_at::date AS d
            FROM aihelms.mcp_call_logs
            WHERE called_at::date >= :start
              AND called_at::date <= :end
        )
        SELECT d, COUNT(*) AS requests
        FROM platform_logs
        GROUP BY 1 ORDER BY 1
    """)
    result = await session.execute(sql, {"start": start_date, "end": end_date})
    daily = {start_date + timedelta(days=i): 0 for i in range(days)}
    for row in result.fetchall():
        daily[row[0]] = int(row[1] or 0)
    return [
        {"label": day.strftime("%m-%d"), "hour": 0, "requests": requests}
        for day, requests in daily.items()
    ]


async def get_model_health_summary(session: AsyncSession) -> dict:
    sql = text("""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE active_deployments > 0) AS healthy
        FROM (
            SELECT m.id, COUNT(d.id) FILTER (WHERE d.is_active = true) AS active_deployments
            FROM aihelms.models m
            LEFT JOIN aihelms.model_deployments d ON d.model_id = m.id
            WHERE m.is_active = true
            GROUP BY m.id
        ) model_health
    """)
    row = (await session.execute(sql)).one()
    return {"total": int(row.total or 0), "healthy": int(row.healthy or 0)}


async def get_last_updated_at(session: AsyncSession) -> datetime | None:
    result = await session.execute(text("""SELECT NULLIF(GREATEST(
            COALESCE((SELECT MAX(last_aggregated_at)::timestamptz FROM aihelms.cost_summary_daily), '-infinity'::timestamptz),
            COALESCE((SELECT MAX(started_at) FROM aihelms.llm_call_logs), '-infinity'::timestamptz),
            COALESCE((SELECT MAX(called_at)::timestamptz FROM aihelms.mcp_call_logs), '-infinity'::timestamptz)
        ), '-infinity'::timestamptz)"""))
    return result.scalar()
