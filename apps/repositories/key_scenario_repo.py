from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import KeyScenario


async def create(session: AsyncSession, scenario: KeyScenario) -> KeyScenario:
    session.add(scenario)
    await session.flush()
    await session.refresh(scenario)
    return scenario


async def find_by_id(session: AsyncSession, scenario_id: int) -> KeyScenario | None:
    result = await session.execute(
        select(KeyScenario).where(KeyScenario.id == scenario_id)
    )
    return result.scalar_one_or_none()


async def find_by_name(session: AsyncSession, name: str) -> KeyScenario | None:
    result = await session.execute(
        select(KeyScenario).where(KeyScenario.name == name)
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    keyword: str | None = None,
) -> list[KeyScenario]:
    stmt = select(KeyScenario).where(KeyScenario.is_active == True).order_by(KeyScenario.id)
    if keyword:
        stmt = stmt.where(KeyScenario.name.ilike(f"%{keyword}%"))
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(session: AsyncSession, keyword: str | None = None) -> int:
    stmt = select(func.count(KeyScenario.id)).where(KeyScenario.is_active == True)
    if keyword:
        stmt = stmt.where(KeyScenario.name.ilike(f"%{keyword}%"))
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(session: AsyncSession) -> list[KeyScenario]:
    result = await session.execute(
        select(KeyScenario).where(KeyScenario.is_active == True).order_by(KeyScenario.id)
    )
    return list(result.scalars().all())
