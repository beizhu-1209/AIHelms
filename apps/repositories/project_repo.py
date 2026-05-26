from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Project, UserProject, User


async def count_projects(session: AsyncSession, keyword: str = "") -> int:
    stmt = select(func.count(Project.id)).where(Project.is_active == True)
    if keyword:
        stmt = stmt.where(Project.name.ilike(f"%{keyword}%"))
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_projects(session: AsyncSession, page: int, page_size: int, keyword: str = "") -> list[Project]:
    offset = (page - 1) * page_size
    stmt = select(Project).where(Project.is_active == True).order_by(Project.id)
    if keyword:
        stmt = stmt.where(Project.name.ilike(f"%{keyword}%"))
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_by_id(session: AsyncSession, project_id: int) -> Project | None:
    result = await session.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, project: Project) -> Project:
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def count_members(session: AsyncSession, project_id: int) -> int:
    result = await session.execute(
        select(func.count(UserProject.id)).where(UserProject.project_id == project_id)
    )
    return result.scalar_one()


async def find_members(session: AsyncSession, project_id: int) -> list[tuple[User, UserProject]]:
    result = await session.execute(
        select(User, UserProject)
        .join(UserProject, UserProject.user_id == User.id)
        .where(UserProject.project_id == project_id)
        .order_by(User.id)
    )
    return list(result.tuples().all())


async def find_membership(session: AsyncSession, user_id: int, project_id: int) -> UserProject | None:
    result = await session.execute(
        select(UserProject).where(
            UserProject.user_id == user_id, UserProject.project_id == project_id
        )
    )
    return result.scalar_one_or_none()


async def add_member(session: AsyncSession, user_id: int, project_id: int) -> None:
    session.add(UserProject(user_id=user_id, project_id=project_id))
    await session.flush()


async def remove_member(session: AsyncSession, user_id: int, project_id: int) -> None:
    await session.execute(
        delete(UserProject).where(
            UserProject.user_id == user_id, UserProject.project_id == project_id
        )
    )


async def find_paginated(
    session: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[list[Project], int]:
    kw = keyword or ""
    total = await count_projects(session, kw)
    items = await find_projects(session, page, page_size, kw)
    return items, total
