from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import ResourceApplication


async def create(session: AsyncSession, app: ResourceApplication) -> ResourceApplication:
    session.add(app)
    await session.flush()
    await session.refresh(app)
    return app


async def find_by_id(session: AsyncSession, app_id: int) -> ResourceApplication | None:
    result = await session.execute(
        select(ResourceApplication).where(ResourceApplication.id == app_id)
    )
    return result.scalar_one_or_none()


async def find_pending_by_user_resource(
    session: AsyncSession, user_id: int, resource_type: str, resource_id: int
) -> ResourceApplication | None:
    result = await session.execute(
        select(ResourceApplication).where(
            ResourceApplication.user_id == user_id,
            ResourceApplication.resource_type == resource_type,
            ResourceApplication.resource_id == resource_id,
            ResourceApplication.status == "pending",
        )
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    status: str | None = None,
) -> list[ResourceApplication]:
    stmt = select(ResourceApplication).order_by(ResourceApplication.id.desc())
    if user_id is not None:
        stmt = stmt.where(ResourceApplication.user_id == user_id)
    if resource_type:
        stmt = stmt.where(ResourceApplication.resource_type == resource_type)
    if resource_id is not None:
        stmt = stmt.where(ResourceApplication.resource_id == resource_id)
    if status:
        stmt = stmt.where(ResourceApplication.status == status)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    status: str | None = None,
) -> int:
    stmt = select(func.count(ResourceApplication.id))
    if user_id is not None:
        stmt = stmt.where(ResourceApplication.user_id == user_id)
    if resource_type:
        stmt = stmt.where(ResourceApplication.resource_type == resource_type)
    if resource_id is not None:
        stmt = stmt.where(ResourceApplication.resource_id == resource_id)
    if status:
        stmt = stmt.where(ResourceApplication.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()
