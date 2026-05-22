import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.security import create_access_token, get_password_hash, verify_password
from exceptions import NotFoundError, UnauthorizedError
from models.db import Permission, Role, RolePermission, User, UserRole

logger = logging.getLogger(__name__)


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("用户名或密码错误")
    if not user.is_active:
        raise UnauthorizedError("账户已被禁用")
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("用户名或密码错误")
    return user


async def login(session: AsyncSession, username: str, password: str) -> tuple[str, User]:
    user = await authenticate(session, username, password)
    permissions = await get_user_permissions(session, user.id)
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "is_admin": user.is_admin,
        "permissions": permissions,
    }
    return create_access_token(token_data), user


async def get_user_permissions(session: AsyncSession, user_id: int) -> list[str]:
    result = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    return list(result.scalars().all())


async def get_current_user_info(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("user", user_id)
    permissions = await get_user_permissions(session, user_id)
    departments = [
        {"id": ud.department.id, "name": ud.department.name}
        for ud in user.departments if ud.department
    ]
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "display_name": user.display_name,
        "avatar": user.avatar,
        "position": user.position,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "permissions": permissions,
        "roles": [{"id": ur.role.id, "name": ur.role.name, "display_name": ur.role.display_name} for ur in user.roles],
        "departments": departments,
    }


async def change_password(session: AsyncSession, user_id: int, old_password: str, new_password: str) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("user", user_id)
    if not verify_password(old_password, user.hashed_password):
        raise UnauthorizedError("原密码错误")
    user.hashed_password = get_password_hash(new_password)
    await session.commit()


async def ensure_super_admin(password: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(Role).where(Role.name == "super_admin"))
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            return

        result = await session.execute(
            select(UserRole).where(UserRole.role_id == admin_role.id).limit(1)
        )
        if result.scalar_one_or_none():
            return

        result = await session.execute(
            select(User).where(User.is_admin == True).limit(1)
        )
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            session.add(UserRole(user_id=existing_admin.id, role_id=admin_role.id))
            await session.commit()
            logger.info("assigned super_admin role to existing admin user %d", existing_admin.id)
            return

        hashed = get_password_hash(password)
        user = User(
            username="admin",
            email="admin@aihelms.local",
            hashed_password=hashed,
            is_active=True,
            is_admin=True,
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=admin_role.id))
        await session.commit()
        logger.info("created super_admin user 'admin'")
