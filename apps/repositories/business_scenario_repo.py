from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import BusinessScenario


async def create(session: AsyncSession, scenario: BusinessScenario) -> BusinessScenario:
    session.add(scenario)
    await session.flush()
    await session.refresh(scenario)
    return scenario


async def find_by_id(session: AsyncSession, scenario_id: int) -> BusinessScenario | None:
    result = await session.execute(
        select(BusinessScenario).where(BusinessScenario.id == scenario_id)
    )
    return result.scalar_one_or_none()


async def find_by_code(session: AsyncSession, code: str) -> BusinessScenario | None:
    result = await session.execute(
        select(BusinessScenario).where(BusinessScenario.code == code)
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    keyword: str | None = None,
    include_inactive: bool = False,
) -> list[BusinessScenario]:
    stmt = select(BusinessScenario).order_by(BusinessScenario.sort_order, BusinessScenario.id)
    if not include_inactive:
        stmt = stmt.where(BusinessScenario.is_active == True)
    if keyword:
        stmt = stmt.where(
            BusinessScenario.name.ilike(f"%{keyword}%") | BusinessScenario.code.ilike(f"%{keyword}%")
        )
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    keyword: str | None = None,
    include_inactive: bool = False,
) -> int:
    stmt = select(func.count(BusinessScenario.id))
    if not include_inactive:
        stmt = stmt.where(BusinessScenario.is_active == True)
    if keyword:
        stmt = stmt.where(
            BusinessScenario.name.ilike(f"%{keyword}%") | BusinessScenario.code.ilike(f"%{keyword}%")
        )
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(session: AsyncSession) -> list[BusinessScenario]:
    result = await session.execute(
        select(BusinessScenario)
        .where(BusinessScenario.is_active == True)
        .order_by(BusinessScenario.sort_order, BusinessScenario.id)
    )
    return list(result.scalars().all())
