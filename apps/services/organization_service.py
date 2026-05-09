import logging

from core.database import get_pool
from exceptions import NotFoundError, ConflictError

logger = logging.getLogger(__name__)


async def list_organizations(
    org_type: str | None = None, is_active: bool | None = None
) -> list[dict]:
    pool = await get_pool()
    where_parts = []
    params: list = []
    param_idx = 1

    if org_type:
        where_parts.append(f"type = ${param_idx}")
        params.append(org_type)
        param_idx += 1

    if is_active is not None:
        where_parts.append(f"is_active = ${param_idx}")
        params.append(is_active)
        param_idx += 1

    where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    rows = await pool.fetch(
        f"SELECT id, name, type, parent_id, description, sort_order, is_active, "
        f"created_at, updated_at FROM aihelms.organizations {where_clause} "
        f"ORDER BY sort_order ASC, id ASC",
        *params,
    )
    result = []
    for row in rows:
        org = _format_org(row)
        org["managers"] = await _get_org_managers(pool, org["id"])
        result.append(org)
    return result


async def get_organization_tree() -> list[dict]:
    orgs = await list_organizations(org_type="department", is_active=True)
    return _build_tree(orgs, parent_id=None)


async def create_organization(
    name: str,
    org_type: str,
    parent_id: int | None,
    description: str,
    sort_order: int,
) -> dict:
    pool = await get_pool()
    if parent_id is not None:
        parent = await pool.fetchrow(
            "SELECT id, type FROM aihelms.organizations WHERE id = $1", parent_id
        )
        if not parent:
            raise NotFoundError("organization", parent_id)
        if parent["type"] != "department":
            raise ConflictError("只能在部门下创建子部门")

    row = await pool.fetchrow(
        "INSERT INTO aihelms.organizations (name, type, parent_id, description, sort_order) "
        "VALUES ($1, $2, $3, $4, $5) "
        "RETURNING id, name, type, parent_id, description, sort_order, is_active, created_at, updated_at",
        name,
        org_type,
        parent_id,
        description,
        sort_order,
    )
    org = _format_org(row)
    org["managers"] = []
    return org


async def update_organization(
    org_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM aihelms.organizations WHERE id = $1", org_id
    )
    if not row:
        raise NotFoundError("organization", org_id)

    updates = []
    params: list = []
    param_idx = 1

    if name is not None:
        updates.append(f"name = ${param_idx}")
        params.append(name)
        param_idx += 1
    if description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(description)
        param_idx += 1
    if sort_order is not None:
        updates.append(f"sort_order = ${param_idx}")
        params.append(sort_order)
        param_idx += 1
    if is_active is not None:
        updates.append(f"is_active = ${param_idx}")
        params.append(is_active)
        param_idx += 1

    if updates:
        updates.append("updated_at = NOW()")
        params.append(org_id)
        await pool.execute(
            f"UPDATE aihelms.organizations SET {', '.join(updates)} WHERE id = ${param_idx}",
            *params,
        )

    return await get_organization_by_id(org_id)


async def update_org_managers(org_id: int, manager_user_ids: list[int]) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM aihelms.organizations WHERE id = $1", org_id
    )
    if not row:
        raise NotFoundError("organization", org_id)

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE aihelms.user_organizations SET is_manager = false "
                "WHERE organization_id = $1",
                org_id,
            )
            for user_id in manager_user_ids:
                existing = await conn.fetchrow(
                    "SELECT id FROM aihelms.user_organizations "
                    "WHERE user_id = $1 AND organization_id = $2",
                    user_id,
                    org_id,
                )
                if existing:
                    await conn.execute(
                        "UPDATE aihelms.user_organizations SET is_manager = true "
                        "WHERE user_id = $1 AND organization_id = $2",
                        user_id,
                        org_id,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO aihelms.user_organizations (user_id, organization_id, is_manager) "
                        "VALUES ($1, $2, true)",
                        user_id,
                        org_id,
                    )

    return await get_organization_by_id(org_id)


async def get_organization_by_id(org_id: int) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, name, type, parent_id, description, sort_order, is_active, "
        "created_at, updated_at FROM aihelms.organizations WHERE id = $1",
        org_id,
    )
    if not row:
        raise NotFoundError("organization", org_id)
    org = _format_org(row)
    org["managers"] = await _get_org_managers(pool, org_id)
    return org


async def delete_organization(org_id: int) -> None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM aihelms.organizations WHERE id = $1", org_id
    )
    if not row:
        raise NotFoundError("organization", org_id)
    children = await pool.fetchval(
        "SELECT COUNT(*) FROM aihelms.organizations WHERE parent_id = $1", org_id
    )
    if children > 0:
        raise ConflictError("该组织下有子组织，不能删除")
    await pool.execute(
        "UPDATE aihelms.organizations SET is_active = false, updated_at = NOW() WHERE id = $1",
        org_id,
    )


async def get_organization_members(org_id: int) -> list[dict]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id FROM aihelms.organizations WHERE id = $1", org_id
    )
    if not row:
        raise NotFoundError("organization", org_id)
    rows = await pool.fetch(
        "SELECT u.id, u.username, u.email, u.is_active, uo.is_manager, uo.joined_at "
        "FROM aihelms.users u "
        "JOIN aihelms.user_organizations uo ON uo.user_id = u.id "
        "WHERE uo.organization_id = $1 ORDER BY uo.is_manager DESC, uo.joined_at ASC",
        org_id,
    )
    return [
        {
            "id": r["id"],
            "username": r["username"],
            "email": r["email"],
            "is_active": r["is_active"],
            "is_manager": r["is_manager"],
            "joined_at": r["joined_at"].isoformat(),
        }
        for r in rows
    ]


async def _get_org_managers(pool, org_id: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT u.id, u.username FROM aihelms.users u "
        "JOIN aihelms.user_organizations uo ON uo.user_id = u.id "
        "WHERE uo.organization_id = $1 AND uo.is_manager = true",
        org_id,
    )
    return [{"id": r["id"], "username": r["username"]} for r in rows]


def _format_org(row) -> dict:
    org = dict(row)
    org["created_at"] = org["created_at"].isoformat()
    org["updated_at"] = org["updated_at"].isoformat() if org["updated_at"] else None
    return org


def _build_tree(orgs: list[dict], parent_id: int | None) -> list[dict]:
    nodes = []
    for org in orgs:
        if org["parent_id"] == parent_id:
            node = {**org, "children": _build_tree(orgs, org["id"])}
            nodes.append(node)
    return nodes
