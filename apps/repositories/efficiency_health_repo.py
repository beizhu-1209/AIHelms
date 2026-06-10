"""Efficiency health repository."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_mcp_health_rows(session: AsyncSession) -> list:
    sql = text(
        "SELECT s.id, s.name, s.server_name, s.status, s.last_health_check,"
        " s.health_check_error, s.is_active, s.is_published, COUNT(t.id) AS tool_count"
        " FROM aihelms.mcp_servers s"
        " LEFT JOIN aihelms.mcp_tools t ON t.server_id = s.id AND t.is_active = true"
        " WHERE s.is_active = true"
        " GROUP BY s.id, s.name, s.server_name, s.status, s.last_health_check,"
        " s.health_check_error, s.is_active, s.is_published"
        " ORDER BY s.updated_at DESC, s.id DESC"
    )
    return list((await session.execute(sql)).fetchall())


async def get_model_health_rows(session: AsyncSession) -> list:
    sql = text(
        "SELECT m.id, m.name, COALESCE(m.model_id, ''), m.category, m.is_published,"
        " COUNT(d.id) FILTER (WHERE d.is_active = true) AS active_deployments,"
        " COUNT(d.id) AS total_deployments, MAX(d.updated_at) AS last_update"
        " FROM aihelms.models m"
        " LEFT JOIN aihelms.model_deployments d ON d.model_id = m.id"
        " WHERE m.is_active = true"
        " GROUP BY m.id, m.name, m.model_id, m.category, m.is_published"
        " ORDER BY active_deployments DESC, m.updated_at DESC, m.id DESC"
    )
    return list((await session.execute(sql)).fetchall())


async def get_data_update_row(session: AsyncSession):
    sql = text("""
        SELECT
            (SELECT NULLIF(GREATEST(
            COALESCE((SELECT MAX(last_aggregated_at)::timestamptz FROM aihelms.cost_summary_daily), '-infinity'::timestamptz),
            COALESCE((SELECT MAX(started_at) FROM aihelms.llm_call_logs), '-infinity'::timestamptz),
            COALESCE((SELECT MAX(called_at)::timestamptz FROM aihelms.mcp_call_logs), '-infinity'::timestamptz)
        ), '-infinity'::timestamptz)) AS latest_at,
            (SELECT MAX(summary_date) FROM aihelms.cost_summary_daily) AS latest_date
    """)
    return (await session.execute(sql)).first()
