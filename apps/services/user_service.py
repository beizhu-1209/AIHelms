import logging

from core.database import get_pool
from core.security import get_password_hash
from exceptions import NotFoundError, ConflictError

logger = logging.getLogger(__name__)


async def list_users(page: int = 1, page_size: int = 20, keyword: str = "") -> dict:
    pool = await get_pool()
    offset = (page - 1) * page_size
    where_clause = "WHERE 1=1"
    params: list = []
    param_idx = 1

    if keyword:
        where_clause += f" AND (username ILIKE ${param_idx} OR email ILIKE ${param_idx})"
        params.append(f"%{keyword}%")
        param_idx += 1

    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM aihelms.users {where_clause}",
        *params,
    )

    params.extend([page_size, offset])
    rows = await pool.fetch(
        f"SELECT id, username, email, is_active, is_admin, created_at "
        f"FROM aihelms.users {where_clause} "
        f"ORDER BY id ASC LIMIT ${param_idx} OFFSET ${param_idx + 1}",
        *params,
    )

    items = []
    for row in rows:
        user = dict(row)
        user["created_at"] = user["created_at"].isoformat()
        user["roles"] = await _get_user_roles(pool, user["id"])
        user["organizations"] = await _get_user_organizations(pool, user["id"])
        items.append(user)

    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_user_by_id(user_id: int) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, email, is_active, is_admin, created_at, updated_at "
        "FROM aihelms.users WHERE id = $1",
        user_id,
    )
    if not row:
        raise NotFoundError("user", user_id)
    user = dict(row)
    user["created_at"] = user["created_at"].isoformat()
    user["updated_at"] = user["updated_at"].isoformat() if user["updated_at"] else None
    user["roles"] = await _get_user_roles(pool, user_id)
    user["organizations"] = await _get_user_organizations(pool, user_id)
    return user


async def create_user(username: str, email: str, password: str, is_active: bool = True) -> dict:
    pool = await get_pool()
    existing = await pool.fetchrow(
        "SELECT id FROM aihelms.users WHERE username = $1 OR email = $2",
        username,
        email,
    )
    if existing:
        raise ConflictError("用户名或邮箱已存在")

    hashed = get_password_hash(password)
    row = await pool.fetchrow(
        "INSERT INTO aihelms.users (username, email, hashed_password, is_active) "
        "VALUES ($1, $2, $3, $4) RETURNING id, username, email, is_active, is_admin, created_at",
        username,
        email,
        hashed,
        is_active,
    )
    user = dict(row)
    user["created_at"] = user["created_at"].isoformat()
    user["roles"] = []
    user["organizations"] = []
    return user


async def update_user(user_id: int, email: str | None = None, is_active: bool | None = None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM aihelms.users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError("user", user_id)

    updates = []
    params = []
    param_idx = 1

    if email is not None:
        dup = await pool.fetchrow(
            "SELECT id FROM aihelms.users WHERE email = $1 AND id != $2",
            email,
            user_id,
        )
        if dup:
            raise ConflictError("邮箱已被使用")
        updates.append(f"email = ${param_idx}")
        params.append(email)
        param_idx += 1

    if is_active is not None:
        updates.append(f"is_active = ${param_idx}")
        params.append(is_active)
        param_idx += 1

    if updates:
        updates.append("updated_at = NOW()")
        params.append(user_id)
        await pool.execute(
            f"UPDATE aihelms.users SET {', '.join(updates)} WHERE id = ${param_idx}",
            *params,
        )

    return await get_user_by_id(user_id)


async def delete_user(user_id: int) -> None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id, is_admin FROM aihelms.users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError("user", user_id)
    if row["is_admin"]:
        raise ConflictError("不能删除管理员账户")
    await pool.execute(
        "UPDATE aihelms.users SET is_active = false, updated_at = NOW() WHERE id = $1",
        user_id,
    )


async def reset_password(user_id: int, new_password: str) -> None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM aihelms.users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError("user", user_id)
    hashed = get_password_hash(new_password)
    await pool.execute(
        "UPDATE aihelms.users SET hashed_password = $1, updated_at = NOW() WHERE id = $2",
        hashed,
        user_id,
    )


async def update_user_roles(user_id: int, role_ids: list[int]) -> None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM aihelms.users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError("user", user_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM aihelms.user_roles WHERE user_id = $1", user_id)
            for role_id in role_ids:
                await conn.execute(
                    "INSERT INTO aihelms.user_roles (user_id, role_id) VALUES ($1, $2)",
                    user_id,
                    role_id,
                )


async def update_user_organizations(user_id: int, organization_ids: list[int]) -> None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id FROM aihelms.users WHERE id = $1", user_id)
    if not row:
        raise NotFoundError("user", user_id)
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM aihelms.user_organizations WHERE user_id = $1 AND is_manager = false",
                user_id,
            )
            for org_id in organization_ids:
                await conn.execute(
                    "INSERT INTO aihelms.user_organizations (user_id, organization_id) "
                    "VALUES ($1, $2) ON CONFLICT (user_id, organization_id) DO NOTHING",
                    user_id,
                    org_id,
                )


async def _get_user_roles(pool, user_id: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT r.id, r.name, r.display_name FROM aihelms.roles r "
        "JOIN aihelms.user_roles ur ON ur.role_id = r.id WHERE ur.user_id = $1",
        user_id,
    )
    return [dict(r) for r in rows]


async def _get_user_organizations(pool, user_id: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT o.id, o.name, o.type, uo.is_manager FROM aihelms.organizations o "
        "JOIN aihelms.user_organizations uo ON uo.organization_id = o.id WHERE uo.user_id = $1",
        user_id,
    )
    return [dict(r) for r in rows]
