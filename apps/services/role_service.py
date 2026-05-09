import logging

from core.database import get_pool
from exceptions import NotFoundError, ConflictError

logger = logging.getLogger(__name__)


async def list_roles() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, name, display_name, description, is_system, created_at "
        "FROM aihelms.roles ORDER BY id ASC"
    )
    result = []
    for row in rows:
        role = dict(row)
        role["created_at"] = role["created_at"].isoformat()
        role["permissions"] = await _get_role_permissions(pool, role["id"])
        result.append(role)
    return result


async def create_role(name: str, display_name: str, description: str) -> dict:
    pool = await get_pool()
    existing = await pool.fetchrow(
        "SELECT id FROM aihelms.roles WHERE name = $1", name
    )
    if existing:
        raise ConflictError("角色名已存在")
    row = await pool.fetchrow(
        "INSERT INTO aihelms.roles (name, display_name, description) "
        "VALUES ($1, $2, $3) RETURNING id, name, display_name, description, is_system, created_at",
        name,
        display_name,
        description,
    )
    role = dict(row)
    role["created_at"] = role["created_at"].isoformat()
    role["permissions"] = []
    return role


async def update_role(role_id: int, display_name: str | None, description: str | None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, is_system FROM aihelms.roles WHERE id = $1", role_id
    )
    if not row:
        raise NotFoundError("role", role_id)
    if row["is_system"]:
        raise ConflictError("系统角色不可编辑")

    updates = []
    params: list = []
    param_idx = 1

    if display_name is not None:
        updates.append(f"display_name = ${param_idx}")
        params.append(display_name)
        param_idx += 1
    if description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(description)
        param_idx += 1

    if updates:
        updates.append("updated_at = NOW()")
        params.append(role_id)
        await pool.execute(
            f"UPDATE aihelms.roles SET {', '.join(updates)} WHERE id = ${param_idx}",
            *params,
        )

    return await get_role_by_id(role_id)


async def delete_role(role_id: int) -> None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, is_system FROM aihelms.roles WHERE id = $1", role_id
    )
    if not row:
        raise NotFoundError("role", role_id)
    if row["is_system"]:
        raise ConflictError("系统角色不可删除")
    await pool.execute("DELETE FROM aihelms.roles WHERE id = $1", role_id)


async def update_role_permissions(role_id: int, permission_ids: list[int]) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, is_system FROM aihelms.roles WHERE id = $1", role_id
    )
    if not row:
        raise NotFoundError("role", role_id)
    if row["is_system"]:
        raise ConflictError("系统角色权限不可修改")

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM aihelms.role_permissions WHERE role_id = $1", role_id
            )
            for perm_id in permission_ids:
                await conn.execute(
                    "INSERT INTO aihelms.role_permissions (role_id, permission_id) VALUES ($1, $2)",
                    role_id,
                    perm_id,
                )
    return await get_role_by_id(role_id)


async def list_permissions() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, code, name, resource, action, description "
        "FROM aihelms.permissions ORDER BY resource, action"
    )
    return [dict(r) for r in rows]


async def get_role_by_id(role_id: int) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, display_name, description, is_system, created_at "
        "FROM aihelms.roles WHERE id = $1",
        role_id,
    )
    if not row:
        raise NotFoundError("role", role_id)
    role = dict(row)
    role["created_at"] = role["created_at"].isoformat()
    role["permissions"] = await _get_role_permissions(pool, role_id)
    return role


async def _get_role_permissions(pool, role_id: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT p.id, p.code, p.name, p.resource, p.action "
        "FROM aihelms.permissions p "
        "JOIN aihelms.role_permissions rp ON rp.permission_id = p.id "
        "WHERE rp.role_id = $1",
        role_id,
    )
    return [dict(r) for r in rows]
