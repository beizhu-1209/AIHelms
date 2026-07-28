import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import NotFoundError, ConflictError
from models.db import Department
from repositories import department_repo
from repositories import user_repo
from services import litellm_client

logger = logging.getLogger(__name__)


async def get_department_tree(session: AsyncSession) -> list[dict]:
    departments = await department_repo.find_all_active(session)
    items = [_serialize_dept(d) for d in departments]
    return _build_tree(items)


async def get_department_by_id(session: AsyncSession, dept_id: int) -> dict:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)
    data = _serialize_dept(dept)
    managers = await department_repo.find_managers(session, dept_id)
    data["managers"] = [{"id": m.id, "username": m.username, "display_name": m.display_name} for m in managers]
    return data


async def create_department(session: AsyncSession, name: str, parent_id: int | None = None, description: str = "") -> dict:
    # 前端以 0 表示顶级部门，归一成 None，避免外键约束违反
    if not parent_id or parent_id <= 0:
        parent_id = None
    else:
        parent = await department_repo.find_by_id(session, parent_id)
        if not parent or not parent.is_active:
            raise NotFoundError("parent department", parent_id)

    dept = Department(name=name, parent_id=parent_id, description=description)
    dept = await department_repo.create(session, dept)
    await session.commit()
    await session.refresh(dept)
    data = _serialize_dept(dept)
    data["managers"] = []
    return data


async def update_department(session: AsyncSession, dept_id: int, name: str | None = None, description: str | None = None, sort_order: int | None = None, is_active: bool | None = None) -> dict:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)

    if name is not None:
        dept.name = name
    if description is not None:
        dept.description = description
    if sort_order is not None:
        dept.sort_order = sort_order
    if is_active is not None and is_active != dept.is_active:
        dept.is_active = is_active
        if dept.litellm_team_id:
            if is_active:
                await litellm_client.unblock_team(dept.litellm_team_id)
            else:
                await litellm_client.block_team(dept.litellm_team_id)

    await session.commit()
    return await get_department_by_id(session, dept_id)


async def delete_department(session: AsyncSession, dept_id: int) -> None:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)

    children = await department_repo.count_children(session, dept_id)
    if children > 0:
        raise ConflictError("该部门下有子部门，不能删除")

    members = await department_repo.count_members(session, dept_id)
    if members > 0:
        raise ConflictError("该部门下有成员，请先移除成员")

    dept.is_active = False
    await session.commit()


async def get_department_members(session: AsyncSession, dept_id: int) -> list[dict]:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)

    rows = await department_repo.find_members(session, dept_id)
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "display_name": user.display_name,
            "position": user.position,
            "is_active": user.is_active,
            "is_manager": ud.is_manager,
            "joined_at": fmt_local_time(ud.joined_at),
        }
        for user, ud in rows
    ]


async def add_department_member(session: AsyncSession, dept_id: int, user_id: int) -> None:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept or not dept.is_active:
        raise NotFoundError("department", dept_id)

    user = await user_repo.find_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("user", user_id)

    existing = await department_repo.find_membership(session, user_id, dept_id)
    if existing:
        raise ConflictError("用户已在该部门中")

    await department_repo.add_member(session, user_id, dept_id)
    await session.commit()


async def remove_department_member(session: AsyncSession, dept_id: int, user_id: int) -> None:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)

    user = await user_repo.find_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("user", user_id)

    await department_repo.remove_member(session, user_id, dept_id)
    await session.commit()


async def update_department_managers(session: AsyncSession, dept_id: int, manager_user_ids: list[int]) -> None:
    dept = await department_repo.find_by_id(session, dept_id)
    if not dept:
        raise NotFoundError("department", dept_id)

    for uid in manager_user_ids:
        membership = await department_repo.find_membership(session, uid, dept_id)
        if not membership:
            raise ConflictError(f"用户 {uid} 不是该部门成员，不能设为主管")

    await department_repo.clear_managers(session, dept_id)
    await department_repo.set_managers(session, dept_id, manager_user_ids)
    await session.commit()


def _serialize_dept(dept: Department) -> dict:
    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "description": dept.description,
        "sort_order": dept.sort_order,
        "is_active": dept.is_active,
        "litellm_team_id": dept.litellm_team_id,
        "created_at": fmt_local_time(dept.created_at),
        "updated_at": fmt_local_time(dept.updated_at),
    }


def _build_tree(items: list[dict]) -> list[dict]:
    node_map = {item["id"]: {**item, "children": []} for item in items}
    tree = []
    for item in items:
        node = node_map[item["id"]]
        parent_id = item.get("parent_id")
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(node)
        else:
            tree.append(node)
    return tree
