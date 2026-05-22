"""AI 效能 Service 层。"""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from models.db import EfficiencyReport
from repositories import efficiency_repo


async def get_overview(
    session: AsyncSession,
    start_date: date,
    end_date: date,
) -> dict:
    """总览驾驶舱数据。"""
    kpi = await efficiency_repo.get_overview_kpi(session, start_date, end_date)

    # 环比：上一个同等时间段
    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    prev_kpi = await efficiency_repo.get_overview_kpi(session, prev_start, prev_end)

    def calc_change(current: float, previous: float) -> float | None:
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 2)

    kpi["cost_change"] = calc_change(kpi["total_cost"], prev_kpi["total_cost"])
    kpi["requests_change"] = calc_change(
        kpi["total_requests"], prev_kpi["total_requests"]
    )
    return kpi


async def get_trend(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    group_by: str = "day",
    cost_type: str | None = None,
) -> list[dict]:
    return await efficiency_repo.get_trend(
        session, start_date, end_date, group_by, cost_type
    )


async def get_composition(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    return await efficiency_repo.get_composition(session, start_date, end_date)


async def get_key_type_comparison(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    return await efficiency_repo.get_key_type_comparison(session, start_date, end_date)


async def get_ranking(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    limit: int = 10,
) -> list[dict]:
    return await efficiency_repo.get_ranking(
        session, start_date, end_date, dimension, limit
    )


async def get_analysis(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    cost_type: str | None = None,
) -> list[dict]:
    return await efficiency_repo.get_analysis_by_dimension(
        session, start_date, end_date, dimension, cost_type
    )


async def get_budget_overview(
    session: AsyncSession, start_date: date, end_date: date
) -> dict:
    data = await efficiency_repo.get_budget_overview(session, start_date, end_date)
    # 月底预测：已用 / 已过天数 × 月总天数
    from datetime import datetime as dt

    today = dt.now().date()
    days_passed = (today - start_date).days + 1
    total_days = (end_date - start_date).days + 1
    if days_passed > 0:
        data["predicted_total"] = round(
            data["used"] / days_passed * total_days, 4
        )
    else:
        data["predicted_total"] = data["used"]
    return data


async def list_reports(
    session: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list, int]:
    reports, total = await efficiency_repo.list_reports(session, page, page_size)
    items = [
        {
            "id": r.id,
            "report_type": r.report_type,
            "period_start": str(r.period_start),
            "period_end": str(r.period_end),
            "model_used": r.model_used,
            "summary": r.summary,
            "created_at": str(r.created_at),
        }
        for r in reports
    ]
    return items, total


async def get_report_detail(session: AsyncSession, report_id: int) -> dict | None:
    report = await efficiency_repo.get_report_by_id(session, report_id)
    if not report:
        return None
    suggestions = await efficiency_repo.list_suggestions_by_report(session, report_id)
    return {
        "id": report.id,
        "report_type": report.report_type,
        "period_start": str(report.period_start),
        "period_end": str(report.period_end),
        "filters": report.filters,
        "model_used": report.model_used,
        "summary": report.summary,
        "content_md": report.content_md,
        "created_at": str(report.created_at),
        "generation_cost": float(report.generation_cost),
        "generation_duration_ms": report.generation_duration_ms,
        "suggestions": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "priority": s.priority,
                "expected_impact": s.expected_impact,
                "status": s.status,
                "status_note": s.status_note,
            }
            for s in suggestions
        ],
    }


async def create_report(
    session: AsyncSession,
    report_type: str,
    period_start: date,
    period_end: date,
    created_by: int,
    model_used: str | None = None,
    filters: dict | None = None,
) -> dict:
    report = EfficiencyReport(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        filters=filters or {},
        model_used=model_used,
        summary="报告生成中...",
        content_md="",
        created_by=created_by,
    )
    report = await efficiency_repo.create_report(session, report)
    await session.commit()
    return {"id": report.id, "status": "created"}


async def update_suggestion_status(
    session: AsyncSession,
    suggestion_id: int,
    status: str,
    note: str,
    updated_by: int,
) -> dict | None:
    suggestion = await efficiency_repo.update_suggestion_status(
        session, suggestion_id, status, note, updated_by
    )
    if not suggestion:
        return None
    await session.commit()
    return {"id": suggestion.id, "status": suggestion.status}
