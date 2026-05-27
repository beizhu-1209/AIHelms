from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey


async def create(session: AsyncSession, ai_key: AiKey) -> AiKey:
    session.add(ai_key)
    await session.flush()
    await session.refresh(ai_key)
    return ai_key


async def find_by_id(session: AsyncSession, key_id: int) -> AiKey | None:
    result = await session.execute(select(AiKey).where(AiKey.id == key_id))
    return result.scalar_one_or_none()


async def find_by_litellm_key_id(session: AsyncSession, token: str) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(AiKey.litellm_key_id == token)
    )
    return result.scalar_one_or_none()


async def find_by_owner(
    session: AsyncSession,
    owner_type: str,
    owner_id: int,
) -> list[AiKey]:
    result = await session.execute(
        select(AiKey)
        .where(AiKey.owner_type == owner_type, AiKey.owner_id == owner_id)
        .order_by(AiKey.id)
    )
    return list(result.scalars().all())


async def find_by_user(session: AsyncSession, user_id: int) -> list[AiKey]:
    result = await session.execute(
        select(AiKey)
        .where(AiKey.owner_type == "user", AiKey.owner_id == user_id)
        .order_by(AiKey.id)
    )
    return list(result.scalars().all())


async def find_personal_main(session: AsyncSession, user_id: int) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(
            AiKey.owner_type == "user",
            AiKey.owner_id == user_id,
            AiKey.key_type == "personal_main",
        )
    )
    return result.scalar_one_or_none()


async def find_all_main_keys(session: AsyncSession) -> list[AiKey]:
    """查找所有主 Key（personal_main / dept_main / project_main）。"""
    result = await session.execute(
        select(AiKey).where(
            AiKey.key_type.in_(["personal_main", "dept_main", "project_main"]),
            AiKey.is_active == True,
        )
    )
    return list(result.scalars().all())


async def find_main_key(session: AsyncSession, owner_type: str, owner_id: int, key_type: str) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(
            AiKey.owner_type == owner_type,
            AiKey.owner_id == owner_id,
            AiKey.key_type == key_type,
        )
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    owner_type: str | None = None,
    owner_id: int | None = None,
    key_type: str | None = None,
) -> list[AiKey]:
    stmt = select(AiKey).order_by(AiKey.id)
    if owner_type:
        stmt = stmt.where(AiKey.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(AiKey.owner_id == owner_id)
    if key_type:
        stmt = stmt.where(AiKey.key_type == key_type)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    owner_type: str | None = None,
    owner_id: int | None = None,
    key_type: str | None = None,
) -> int:
    stmt = select(func.count(AiKey.id))
    if owner_type:
        stmt = stmt.where(AiKey.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(AiKey.owner_id == owner_id)
    if key_type:
        stmt = stmt.where(AiKey.key_type == key_type)
    result = await session.execute(stmt)
    return result.scalar_one()
