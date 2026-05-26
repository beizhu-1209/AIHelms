from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import User, UserRole, UserDepartment, UserProject


async def count_users(session: AsyncSession, keyword: str = "") -> int:
    stmt = select(func.count(User.id)).where(User.is_super_admin == False, User.is_active == True)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_users(session: AsyncSession, page: int, page_size: int, keyword: str = "") -> list[User]:
    offset = (page - 1) * page_size
    stmt = select(User).where(User.is_super_admin == False, User.is_active == True).order_by(User.id)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def find_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def find_user_by_username_or_email(session: AsyncSession, username: str, email: str) -> User | None:
    result = await session.execute(
        select(User).where(or_(User.username == username, User.email == email))
    )
    return result.scalar_one_or_none()


async def find_user_by_email_exclude(session: AsyncSession, email: str, exclude_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email, User.id != exclude_id)
    )
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user: User) -> User:
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def replace_user_roles(session: AsyncSession, user_id: int, role_ids: list[int]) -> None:
    await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for role_id in role_ids:
        session.add(UserRole(user_id=user_id, role_id=role_id))
    await session.flush()


async def find_user_departments(session: AsyncSession, user_id: int) -> list[UserDepartment]:
    result = await session.execute(
        select(UserDepartment).where(UserDepartment.user_id == user_id)
    )
    return list(result.scalars().all())


async def find_user_projects(session: AsyncSession, user_id: int) -> list[UserProject]:
    result = await session.execute(
        select(UserProject).where(UserProject.user_id == user_id)
    )
    return list(result.scalars().all())


async def replace_user_departments(session: AsyncSession, user_id: int, department_ids: list[int]) -> None:
    await session.execute(delete(UserDepartment).where(UserDepartment.user_id == user_id))
    for dept_id in department_ids:
        session.add(UserDepartment(user_id=user_id, department_id=dept_id))
    await session.flush()


async def replace_user_projects(session: AsyncSession, user_id: int, project_ids: list[int]) -> None:
    await session.execute(delete(UserProject).where(UserProject.user_id == user_id))
    for proj_id in project_ids:
        session.add(UserProject(user_id=user_id, project_id=proj_id))
    await session.flush()


async def find_users_paginated(
    session: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[list[User], int]:
    kw = keyword or ""
    total = await count_users(session, kw)
    users = await find_users(session, page, page_size, kw)
    return users, total
