"""Efficiency report repository."""

import datetime
from datetime import timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import EfficiencyReport, EfficiencySuggestion

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
    suggestion.status_updated_at = datetime.datetime.now(timezone.utc)
    await session.flush()
    return suggestion
