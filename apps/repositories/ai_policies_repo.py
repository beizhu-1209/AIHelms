from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiPoliciesAudit, AiPoliciesRiskCatalog, AiPoliciesSettings


async def create_audit(
    session: AsyncSession, audit: AiPoliciesAudit
) -> AiPoliciesAudit:
    session.add(audit)
    await session.flush()
    await session.refresh(audit)
    return audit


async def find_by_id(session: AsyncSession, audit_id: int) -> AiPoliciesAudit | None:
    result = await session.execute(
        select(AiPoliciesAudit).where(AiPoliciesAudit.id == audit_id)
    )
    return result.scalar_one_or_none()


async def find_by_audit_id(
    session: AsyncSession, audit_id: str
) -> AiPoliciesAudit | None:
    result = await session.execute(
        select(AiPoliciesAudit).where(AiPoliciesAudit.audit_id == audit_id)
    )
    return result.scalar_one_or_none()


async def find_by_ids(
    session: AsyncSession, audit_ids: list[int]
) -> list[AiPoliciesAudit]:
    if not audit_ids:
        return []
    result = await session.execute(
        select(AiPoliciesAudit).where(AiPoliciesAudit.id.in_(audit_ids))
    )
    return list(result.scalars().all())


async def find_active_by_skill(
    session: AsyncSession, skill_id: int
) -> AiPoliciesAudit | None:
    result = await session.execute(
        select(AiPoliciesAudit)
        .where(
            AiPoliciesAudit.audit_type == "skill",
            AiPoliciesAudit.skill_id == skill_id,
            AiPoliciesAudit.status.in_(["queued", "running"]),
        )
        .order_by(AiPoliciesAudit.created_at.desc(), AiPoliciesAudit.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _apply_filters(
    stmt,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
):
    if audit_type:
        stmt = stmt.where(AiPoliciesAudit.audit_type == audit_type)
    if skill_id:
        stmt = stmt.where(AiPoliciesAudit.skill_id == skill_id)
    if status:
        stmt = stmt.where(AiPoliciesAudit.status == status)
    if decision:
        stmt = stmt.where(AiPoliciesAudit.decision == decision)
    if q:
        stmt = stmt.where(AiPoliciesAudit.skill_name.ilike(f"%{q}%"))
    if unfinished is True:
        stmt = stmt.where(AiPoliciesAudit.finished_at.is_(None))
    elif unfinished is False:
        stmt = stmt.where(AiPoliciesAudit.finished_at.is_not(None))
    if finished_from:
        stmt = stmt.where(AiPoliciesAudit.finished_at >= finished_from)
    if finished_to:
        stmt = stmt.where(AiPoliciesAudit.finished_at <= finished_to)
    return stmt


async def find_all(
    session: AsyncSession,
    page: int,
    page_size: int,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
) -> list[AiPoliciesAudit]:
    stmt = select(AiPoliciesAudit).order_by(
        AiPoliciesAudit.created_at.desc(), AiPoliciesAudit.id.desc()
    )
    stmt = _apply_filters(
        stmt,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    stmt = stmt.limit(page_size).offset((page - 1) * page_size)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    audit_type: str | None = None,
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
) -> int:
    stmt = select(func.count(AiPoliciesAudit.id))
    stmt = _apply_filters(
        stmt,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def list_catalog(session: AsyncSession) -> list[AiPoliciesRiskCatalog]:
    result = await session.execute(
        select(AiPoliciesRiskCatalog).order_by(AiPoliciesRiskCatalog.sort_order)
    )
    return list(result.scalars().all())


async def get_settings(session: AsyncSession) -> AiPoliciesSettings:
    settings = await session.get(AiPoliciesSettings, 1)
    if settings:
        return settings
    settings = AiPoliciesSettings(id=1)
    session.add(settings)
    await session.flush()
    await session.refresh(settings)
    return settings
