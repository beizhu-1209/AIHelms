import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import NotFoundError, ConflictError
from models.db import Role, Permission, RolePermission

logger = logging.getLogger(__name__)


async def list_roles(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()
    return [_serialize_role(r) for r in roles]


async def create_role(session: AsyncSession, name: str, display_name: str, description: str) -> dict:
    result = await session.execute(select(Role).where(Role.name == name))
    if result.scalar_one_or_none():
        raise ConflictError("角色名已存在")

    role = Role(name=name, display_name=display_name, description=description)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return _serialize_role(role)


async def update_role(session: AsyncSession, role_id: int, display_name: str | None, description: str | None) -> dict:
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("role", role_id)
    if role.is_system:
        raise ConflictError("系统角色不可编辑")

    if display_name is not None:
        role.display_name = display_name
    if description is not None:
        role.description = description

    await session.commit()
    await session.refresh(role)
    return _serialize_role(role)


async def delete_role(session: AsyncSession, role_id: int) -> None:
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("role", role_id)
    if role.is_system:
        raise ConflictError("系统角色不可删除")
    await session.delete(role)
    await session.commit()


async def update_role_permissions(session: AsyncSession, role_id: int, permission_ids: list[int]) -> dict:
    result = await session.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("role", role_id)
    if role.is_system:
        raise ConflictError("系统角色权限不可修改")

    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    for perm_id in permission_ids:
        session.add(RolePermission(role_id=role_id, permission_id=perm_id))
    await session.commit()
    await session.refresh(role)
    return _serialize_role(role)


async def list_permissions(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(Permission).order_by(Permission.resource, Permission.action))
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "resource": p.resource,
            "action": p.action,
            "description": p.description,
        }
        for p in result.scalars().all()
    ]


def _serialize_role(role: Role) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "is_system": role.is_system,
        "created_at": fmt_local_time(role.created_at),
        "permissions": [
            {"id": rp.permission.id, "code": rp.permission.code, "name": rp.permission.name, "resource": rp.permission.resource, "action": rp.permission.action}
            for rp in role.permissions
        ],
    }
