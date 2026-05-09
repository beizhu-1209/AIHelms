import logging

from core.database import get_pool
from core.security import verify_password, get_password_hash, create_access_token
from exceptions import NotFoundError, UnauthorizedError

logger = logging.getLogger(__name__)


async def authenticate(username: str, password: str) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, email, hashed_password, is_active, is_admin "
        "FROM aihelms.users WHERE username = $1",
        username,
    )
    if not row:
        raise UnauthorizedError("用户名或密码错误")
    if not row["is_active"]:
        raise UnauthorizedError("账户已被禁用")
    if not verify_password(password, row["hashed_password"]):
        raise UnauthorizedError("用户名或密码错误")
    return dict(row)


async def login(username: str, password: str) -> str:
    user = await authenticate(username, password)
    permissions = await get_user_permissions(user["id"])
    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "is_admin": user["is_admin"],
        "permissions": permissions,
    }
    return create_access_token(token_data)


async def get_user_permissions(user_id: int) -> list[str]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT DISTINCT p.code FROM aihelms.permissions p "
        "JOIN aihelms.role_permissions rp ON rp.permission_id = p.id "
        "JOIN aihelms.user_roles ur ON ur.role_id = rp.role_id "
        "WHERE ur.user_id = $1",
        user_id,
    )
    return [row["code"] for row in rows]


async def get_current_user_info(user_id: int) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, username, email, is_active, is_admin, created_at "
        "FROM aihelms.users WHERE id = $1",
        user_id,
    )
    if not row:
        raise NotFoundError("user", user_id)
    user = dict(row)
    user["created_at"] = user["created_at"].isoformat()
    user["permissions"] = await get_user_permissions(user_id)
    roles = await pool.fetch(
        "SELECT r.id, r.name, r.display_name FROM aihelms.roles r "
        "JOIN aihelms.user_roles ur ON ur.role_id = r.id "
        "WHERE ur.user_id = $1",
        user_id,
    )
    user["roles"] = [dict(r) for r in roles]
    return user


async def change_password(user_id: int, old_password: str, new_password: str) -> None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT hashed_password FROM aihelms.users WHERE id = $1",
        user_id,
    )
    if not row:
        raise NotFoundError("user", user_id)
    if not verify_password(old_password, row["hashed_password"]):
        raise UnauthorizedError("原密码错误")
    hashed = get_password_hash(new_password)
    await pool.execute(
        "UPDATE aihelms.users SET hashed_password = $1, updated_at = NOW() WHERE id = $2",
        hashed,
        user_id,
    )


async def ensure_super_admin(password: str) -> None:
    pool = await get_pool()
    admin_role = await pool.fetchrow(
        "SELECT id FROM aihelms.roles WHERE name = 'super_admin'"
    )
    if not admin_role:
        return
    has_super_admin = await pool.fetchrow(
        "SELECT ur.user_id FROM aihelms.user_roles ur WHERE ur.role_id = $1 LIMIT 1",
        admin_role["id"],
    )
    if has_super_admin:
        return
    existing_admin = await pool.fetchrow(
        "SELECT id FROM aihelms.users WHERE is_admin = true LIMIT 1"
    )
    if existing_admin:
        await pool.execute(
            "INSERT INTO aihelms.user_roles (user_id, role_id) VALUES ($1, $2) "
            "ON CONFLICT (user_id, role_id) DO NOTHING",
            existing_admin["id"],
            admin_role["id"],
        )
        logger.info("assigned super_admin role to existing admin user %d", existing_admin["id"])
        return
    hashed = get_password_hash(password)
    user_id = await pool.fetchval(
        "INSERT INTO aihelms.users (username, email, hashed_password, is_active, is_admin) "
        "VALUES ('admin', 'admin@aihelms.local', $1, true, true) "
        "ON CONFLICT (username) DO UPDATE SET hashed_password = $1 "
        "RETURNING id",
        hashed,
    )
    await pool.execute(
        "INSERT INTO aihelms.user_roles (user_id, role_id) VALUES ($1, $2) "
        "ON CONFLICT (user_id, role_id) DO NOTHING",
        user_id,
        admin_role["id"],
    )
    logger.info("created super_admin user 'admin'")
