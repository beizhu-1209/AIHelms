from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import ApiKey


async def create(session: AsyncSession, api_key: ApiKey) -> ApiKey:
    session.add(api_key)
    await session.flush()
    await session.refresh(api_key)
    return api_key


async def find_by_id(session: AsyncSession, key_id: int) -> ApiKey | None:
    result = await session.execute(select(ApiKey).where(ApiKey.id == key_id))
    return result.scalar_one_or_none()


async def find_by_hash(session: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
) -> list[ApiKey]:
    stmt = select(ApiKey).order_by(ApiKey.id.desc())
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(ApiKey.name.ilike(pattern), ApiKey.description.ilike(pattern))
        )
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(session: AsyncSession, keyword: str = "") -> int:
    stmt = select(func.count(ApiKey.id))
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(ApiKey.name.ilike(pattern), ApiKey.description.ilike(pattern))
        )
    result = await session.execute(stmt)
    return result.scalar_one()


async def delete(session: AsyncSession, key_id: int) -> None:
    api_key = await find_by_id(session, key_id)
    if api_key:
        await session.delete(api_key)
        await session.flush()


async def touch_last_used(session: AsyncSession, key_id: int) -> None:
    await session.execute(
        update(ApiKey)
        .where(ApiKey.id == key_id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await session.commit()
