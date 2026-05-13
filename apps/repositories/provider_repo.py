from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Provider


async def create(session: AsyncSession, provider: Provider) -> Provider:
    session.add(provider)
    await session.flush()
    await session.refresh(provider)
    return provider


async def find_by_id(session: AsyncSession, provider_id: int) -> Provider | None:
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    is_active: bool | None = None,
) -> list[Provider]:
    stmt = select(Provider).order_by(Provider.id)
    if is_active is not None:
        stmt = stmt.where(Provider.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(session: AsyncSession, is_active: bool | None = None) -> int:
    stmt = select(func.count(Provider.id))
    if is_active is not None:
        stmt = stmt.where(Provider.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(session: AsyncSession) -> list[Provider]:
    result = await session.execute(
        select(Provider).where(Provider.is_active == True).order_by(Provider.id)
    )
    return list(result.scalars().all())
