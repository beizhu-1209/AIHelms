import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError, ValidationError
from models.db import ResourceApplication
from repositories import resource_application_repo, mcp_repo, ai_key_repo, model_repo, skill_repo, agent_repo
from services import ai_key_service

logger = logging.getLogger(__name__)


VALID_RESOURCE_TYPES = ("model", "mcp", "skill", "agent")


async def create_application(
    session: AsyncSession,
    user_id: int,
    resource_type: str,
    resource_id: int,
    reason: str = "",
    request_config: dict | None = None,
) -> dict:
    if resource_type not in VALID_RESOURCE_TYPES:
        raise ValidationError(f"resource_type 必须为 {VALID_RESOURCE_TYPES} 之一")

    await _validate_resource_exists(session, resource_type, resource_id)

    existing = await resource_application_repo.find_pending_by_user_resource(
        session, user_id, resource_type, resource_id
    )
    if existing:
        raise ConflictError("已存在未处理的申请")

    app = ResourceApplication(
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        request_config=request_config or {},
    )
    app = await resource_application_repo.create(session, app)
    await session.commit()
    await session.refresh(app)
    return await _serialize(session, app)


async def list_applications(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    resource_type: str | None = None,
    status: str | None = None,
) -> dict:
    total = await resource_application_repo.count_all(
        session, user_id, resource_type, None, status
    )
    items = await resource_application_repo.find_all(
        session, page, page_size, user_id, resource_type, None, status
    )
    serialized = [await _serialize(session, a) for a in items]
    return {
        "items": serialized,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_application(session: AsyncSession, app_id: int) -> dict:
    app = await resource_application_repo.find_by_id(session, app_id)
    if not app:
        raise NotFoundError("resource_application", app_id)
    return await _serialize(session, app)


async def approve_application(
    session: AsyncSession,
    app_id: int,
    reviewer_id: int,
    approval_config: dict | None = None,
    review_notes: str = "",
) -> dict:
    app = await resource_application_repo.find_by_id(session, app_id)
    if not app:
        raise NotFoundError("resource_application", app_id)
    if app.status != "pending":
        raise ConflictError("该申请已处理")

    app.status = "approved"
    app.reviewed_by = reviewer_id
    app.reviewed_at = datetime.utcnow()
    app.review_notes = review_notes
    app.approval_config = approval_config or {}

    await _grant_resource(session, app)

    await session.commit()
    await session.refresh(app)
    return await _serialize(session, app)


async def reject_application(
    session: AsyncSession,
    app_id: int,
    reviewer_id: int,
    review_notes: str = "",
) -> dict:
    app = await resource_application_repo.find_by_id(session, app_id)
    if not app:
        raise NotFoundError("resource_application", app_id)
    if app.status != "pending":
        raise ConflictError("该申请已处理")

    app.status = "rejected"
    app.reviewed_by = reviewer_id
    app.reviewed_at = datetime.utcnow()
    app.review_notes = review_notes

    await session.commit()
    await session.refresh(app)
    return await _serialize(session, app)


# ─── Internal ────────────────────────────────────────────────────────────────


async def _validate_resource_exists(
    session: AsyncSession, resource_type: str, resource_id: int
) -> None:
    if resource_type == "model":
        model = await model_repo.find_by_id(session, resource_id)
        if not model:
            raise NotFoundError("model", resource_id)
    elif resource_type == "mcp":
        server = await mcp_repo.find_server_by_id(session, resource_id)
        if not server:
            raise NotFoundError("mcp_server", resource_id)
    elif resource_type == "skill":
        skill = await skill_repo.find_by_id(session, resource_id)
        if not skill:
            raise NotFoundError("skill", resource_id)
    elif resource_type == "agent":
        agent = await agent_repo.find_by_id(session, resource_id)
        if not agent:
            raise NotFoundError("agent", resource_id)


async def _grant_resource(session: AsyncSession, app: ResourceApplication) -> None:
    """审批通过时把资源授权落到用户主 Key 上。"""
    main_key = await ai_key_repo.find_personal_main(session, app.user_id)
    if not main_key:
        logger.warning("user %s has no personal_main key, skip grant", app.user_id)
        return

    if app.resource_type == "model":
        model = await model_repo.find_by_id(session, app.resource_id)
        if model and model.model_id not in (main_key.models or []):
            new_models = list(main_key.models or []) + [model.model_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, models=new_models
            )
    elif app.resource_type == "mcp":
        if app.resource_id not in (main_key.mcps or []):
            new_mcps = list(main_key.mcps or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, mcps=new_mcps
            )
    elif app.resource_type == "skill":
        if app.resource_id not in (main_key.skills or []):
            new_skills = list(main_key.skills or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, skills=new_skills
            )
    elif app.resource_type == "agent":
        if app.resource_id not in (main_key.agents or []):
            new_agents = list(main_key.agents or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, agents=new_agents
            )


async def _serialize(session: AsyncSession, app: ResourceApplication) -> dict:
    resource_info = await _get_resource_info(session, app.resource_type, app.resource_id)
    return {
        "id": app.id,
        "user_id": app.user_id,
        "resource_type": app.resource_type,
        "resource_id": app.resource_id,
        "resource_info": resource_info,
        "reason": app.reason,
        "request_config": app.request_config,
        "status": app.status,
        "reviewed_by": app.reviewed_by,
        "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
        "review_notes": app.review_notes,
        "approval_config": app.approval_config,
        "created_at": app.created_at.isoformat() if app.created_at else None,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
        "user": {
            "id": app.user.id,
            "username": app.user.username,
            "display_name": app.user.display_name,
        } if app.user else None,
        "reviewer": {
            "id": app.reviewer.id,
            "username": app.reviewer.username,
            "display_name": app.reviewer.display_name,
        } if app.reviewer else None,
    }


async def _get_resource_info(session: AsyncSession, resource_type: str, resource_id: int) -> dict | None:
    if resource_type == "model":
        m = await model_repo.find_by_id(session, resource_id)
        if m:
            return {"id": m.id, "name": m.name, "model_id": m.model_id}
    elif resource_type == "mcp":
        s = await mcp_repo.find_server_by_id(session, resource_id)
        if s:
            return {"id": s.id, "name": s.name, "server_name": s.server_name}
    elif resource_type == "skill":
        sk = await skill_repo.find_by_id(session, resource_id)
        if sk:
            return {"id": sk.id, "name": sk.name, "icon": sk.icon}
    elif resource_type == "agent":
        ag = await agent_repo.find_by_id(session, resource_id)
        if ag:
            return {"id": ag.id, "name": ag.name, "icon": ag.icon, "platform": ag.platform}
    return None
