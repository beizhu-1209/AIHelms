from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Credential


async def create(session: AsyncSession, credential: Credential) -> Credential:
    session.add(credential)
    await session.flush()
    await session.refresh(credential)
    return credential


async def find_by_id(session: AsyncSession, credential_id: int) -> Credential | None:
    result = await session.execute(select(Credential).where(Credential.id == credential_id))
    return result.scalar_one_or_none()


async def find_by_name(session: AsyncSession, credential_name: str) -> Credential | None:
    result = await session.execute(
        select(Credential).where(Credential.credential_name == credential_name)
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    provider_id: int | None = None,
    is_active: bool | None = None,
) -> list[Credential]:
    stmt = select(Credential).order_by(Credential.id)
    if provider_id is not None:
        stmt = stmt.where(Credential.provider_id == provider_id)
    if is_active is not None:
        stmt = stmt.where(Credential.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    provider_id: int | None = None,
    is_active: bool | None = None,
) -> int:
    stmt = select(func.count(Credential.id))
    if provider_id is not None:
        stmt = stmt.where(Credential.provider_id == provider_id)
    if is_active is not None:
        stmt = stmt.where(Credential.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(session: AsyncSession) -> list[Credential]:
    result = await session.execute(
        select(Credential).where(Credential.is_active == True).order_by(Credential.id)
    )
    return list(result.scalars().all())


async def find_by_provider(session: AsyncSession, provider_id: int) -> list[Credential]:
    result = await session.execute(
        select(Credential).where(Credential.provider_id == provider_id).order_by(Credential.id)
    )
    return list(result.scalars().all())
