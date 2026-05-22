from datetime import datetime

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Agent, AgentCategory, AgentPlatform, AgentUsageLog


# ─── Agent ──────────────────────────────────────────────────────────────────


async def create(session: AsyncSession, agent: Agent) -> Agent:
    session.add(agent)
    await session.flush()
    await session.refresh(agent)
    return agent


async def find_by_id(session: AsyncSession, agent_id: int) -> Agent | None:
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def find_by_agent_id(session: AsyncSession, agent_id: str) -> Agent | None:
    result = await session.execute(select(Agent).where(Agent.agent_id == agent_id))
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    platform: str | None = None,
    is_published: bool | None = None,
    is_active: bool | None = None,
) -> list[Agent]:
    stmt = select(Agent).order_by(Agent.id.desc())
    if category:
        stmt = stmt.where(Agent.category == category)
    if platform:
        stmt = stmt.where(Agent.platform == platform)
    if is_published is not None:
        stmt = stmt.where(Agent.is_published == is_published)
    if is_active is not None:
        stmt = stmt.where(Agent.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    category: str | None = None,
    platform: str | None = None,
    is_published: bool | None = None,
    is_active: bool | None = None,
) -> int:
    stmt = select(func.count(Agent.id))
    if category:
        stmt = stmt.where(Agent.category == category)
    if platform:
        stmt = stmt.where(Agent.platform == platform)
    if is_published is not None:
        stmt = stmt.where(Agent.is_published == is_published)
    if is_active is not None:
        stmt = stmt.where(Agent.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_by_ids(session: AsyncSession, ids: list[int]) -> list[Agent]:
    if not ids:
        return []
    result = await session.execute(select(Agent).where(Agent.id.in_(ids)))
    return list(result.scalars().all())


async def delete(session: AsyncSession, agent_id: int) -> bool:
    result = await session.execute(sa_delete(Agent).where(Agent.id == agent_id))
    return result.rowcount > 0


# ─── AgentCategory ──────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[AgentCategory]:
    result = await session.execute(
        select(AgentCategory).order_by(AgentCategory.sort_order, AgentCategory.id)
    )
    return list(result.scalars().all())


async def find_category_by_id(session: AsyncSession, category_id: int) -> AgentCategory | None:
    result = await session.execute(select(AgentCategory).where(AgentCategory.id == category_id))
    return result.scalar_one_or_none()


async def find_category_by_name(session: AsyncSession, name: str) -> AgentCategory | None:
    result = await session.execute(select(AgentCategory).where(AgentCategory.name == name))
    return result.scalar_one_or_none()


async def create_category(session: AsyncSession, category: AgentCategory) -> AgentCategory:
    session.add(category)
    await session.flush()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    result = await session.execute(
        sa_delete(AgentCategory).where(AgentCategory.id == category_id)
    )
    return result.rowcount > 0


# ─── AgentPlatform ──────────────────────────────────────────────────────────


async def list_platforms(session: AsyncSession) -> list[AgentPlatform]:
    result = await session.execute(
        select(AgentPlatform).order_by(AgentPlatform.sort_order, AgentPlatform.id)
    )
    return list(result.scalars().all())


async def find_platform_by_id(session: AsyncSession, platform_id: int) -> AgentPlatform | None:
    result = await session.execute(select(AgentPlatform).where(AgentPlatform.id == platform_id))
    return result.scalar_one_or_none()


async def find_platform_by_name(session: AsyncSession, name: str) -> AgentPlatform | None:
    result = await session.execute(select(AgentPlatform).where(AgentPlatform.name == name))
    return result.scalar_one_or_none()


async def create_platform(session: AsyncSession, platform: AgentPlatform) -> AgentPlatform:
    session.add(platform)
    await session.flush()
    await session.refresh(platform)
    return platform


async def delete_platform(session: AsyncSession, platform_id: int) -> bool:
    result = await session.execute(
        sa_delete(AgentPlatform).where(AgentPlatform.id == platform_id)
    )
    return result.rowcount > 0


# ─── AgentUsageLog ──────────────────────────────────────────────────────────


async def create_usage_log(session: AsyncSession, log: AgentUsageLog) -> AgentUsageLog:
    session.add(log)
    await session.flush()
    return log


async def has_user_used(session: AsyncSession, agent_id: int, user_id: int) -> bool:
    result = await session.execute(
        select(func.count(AgentUsageLog.id)).where(
            AgentUsageLog.agent_id == agent_id,
            AgentUsageLog.user_id == user_id,
        )
    )
    return (result.scalar_one() or 0) > 0


async def find_usage_logs(
    session: AsyncSession,
    agent_id: int,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[AgentUsageLog]:
    stmt = select(AgentUsageLog).where(AgentUsageLog.agent_id == agent_id).order_by(
        AgentUsageLog.created_at.desc()
    )
    if user_id is not None:
        stmt = stmt.where(AgentUsageLog.user_id == user_id)
    if start_time:
        stmt = stmt.where(AgentUsageLog.created_at >= start_time)
    if end_time:
        stmt = stmt.where(AgentUsageLog.created_at <= end_time)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_usage_logs(
    session: AsyncSession,
    agent_id: int,
    user_id: int | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> int:
    stmt = select(func.count(AgentUsageLog.id)).where(AgentUsageLog.agent_id == agent_id)
    if user_id is not None:
        stmt = stmt.where(AgentUsageLog.user_id == user_id)
    if start_time:
        stmt = stmt.where(AgentUsageLog.created_at >= start_time)
    if end_time:
        stmt = stmt.where(AgentUsageLog.created_at <= end_time)
    result = await session.execute(stmt)
    return result.scalar_one()


async def increment_call_count(session: AsyncSession, agent_id: int) -> None:
    agent = await find_by_id(session, agent_id)
    if agent:
        agent.call_count = (agent.call_count or 0) + 1


async def increment_user_count(session: AsyncSession, agent_id: int) -> None:
    agent = await find_by_id(session, agent_id)
    if agent:
        agent.user_count = (agent.user_count or 0) + 1
