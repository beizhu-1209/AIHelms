import logging

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError
from models.db import Project
from repositories import project_repo
from repositories import user_repo
from services import litellm_client

logger = logging.getLogger(__name__)


async def list_projects(session: AsyncSession, page: int = 1, page_size: int = 20, keyword: str = "") -> dict:
    total = await project_repo.count_projects(session, keyword)
    projects = await project_repo.find_projects(session, page, page_size, keyword)
    items = [_serialize_project(p) for p in projects]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_project_by_id(session: AsyncSession, project_id: int) -> dict:
    project = await project_repo.find_by_id(session, project_id)
    if not project:
        raise NotFoundError("project", project_id)
    return _serialize_project(project)


async def create_project(session: AsyncSession, name: str, description: str = "") -> dict:
    project = Project(name=name, description=description)
    project = await project_repo.create(session, project)

    try:
        result = await litellm_client.create_team(
            team_alias=f"project_{project.id}_{name}",
            metadata={"type": "project", "project_id": project.id},
        )
        project.litellm_team_id = result.get("team_id")
    except litellm_client.LiteLLMError:
        logger.warning("litellm sync failed for project %s", project.id)

    await session.commit()
    return _serialize_project(project)


async def update_project(session: AsyncSession, project_id: int, name: str | None = None, description: str | None = None) -> dict:
    project = await project_repo.find_by_id(session, project_id)
    if not project:
        raise NotFoundError("project", project_id)

    if name is not None:
        project.name = name
    if description is not None:
        project.description = description

    await session.commit()
    return _serialize_project(project)


async def delete_project(session: AsyncSession, project_id: int) -> None:
    project = await project_repo.find_by_id(session, project_id)
    if not project:
        raise NotFoundError("project", project_id)

    members = await project_repo.count_members(session, project_id)
    if members > 0:
        raise ConflictError("该项目下有成员，请先移除成员")

    project.is_active = False
    await session.commit()

    if project.litellm_team_id:
        try:
            await litellm_client.block_team(project.litellm_team_id)
        except litellm_client.LiteLLMError:
            logger.warning("litellm block team failed for project %s", project_id)


async def get_project_members(session: AsyncSession, project_id: int) -> list[dict]:
    project = await project_repo.find_by_id(session, project_id)
    if not project:
        raise NotFoundError("project", project_id)

    rows = await project_repo.find_members(session, project_id)
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "display_name": user.display_name,
            "position": user.position,
            "is_active": user.is_active,
            "joined_at": up.joined_at.isoformat() if up.joined_at else None,
        }
        for user, up in rows
    ]


async def add_project_member(session: AsyncSession, project_id: int, user_id: int) -> None:
    project = await project_repo.find_by_id(session, project_id)
    if not project or not project.is_active:
        raise NotFoundError("project", project_id)

    user = await user_repo.find_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("user", user_id)

    existing = await project_repo.find_membership(session, user_id, project_id)
    if existing:
        raise ConflictError("用户已在该项目中")

    await project_repo.add_member(session, user_id, project_id)

    if project.litellm_team_id and user.litellm_user_id:
        try:
            await litellm_client.add_team_member(project.litellm_team_id, user.litellm_user_id)
        except litellm_client.LiteLLMError:
            logger.warning("litellm add member failed: project=%s user=%s", project_id, user_id)

    await session.commit()


async def remove_project_member(session: AsyncSession, project_id: int, user_id: int) -> None:
    project = await project_repo.find_by_id(session, project_id)
    if not project:
        raise NotFoundError("project", project_id)

    user = await user_repo.find_user_by_id(session, user_id)
    if not user:
        raise NotFoundError("user", user_id)

    await project_repo.remove_member(session, user_id, project_id)

    if project.litellm_team_id and user.litellm_user_id:
        try:
            await litellm_client.remove_team_member(project.litellm_team_id, user.litellm_user_id)
        except litellm_client.LiteLLMError:
            logger.warning("litellm remove member failed: project=%s user=%s", project_id, user_id)

    await session.commit()


def _serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "is_active": project.is_active,
        "litellm_team_id": project.litellm_team_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }
