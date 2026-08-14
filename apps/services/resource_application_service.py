import logging
from datetime import datetime
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import ConflictError, NotFoundError, ValidationError
from models.db import ResourceApplication
from repositories import (
    agent_repo,
    ai_key_repo,
    mcp_repo,
    model_repo,
    resource_application_repo,
    skill_repo,
)
from services import ai_key_service
from services.icon_url import resolve_icon_url

logger = logging.getLogger(__name__)


class LabeledValue(str, Enum):
    label: str

    def __new__(cls, value: str, label: str):
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    @classmethod
    def label_for(cls, value: str) -> str:
        try:
            return cls(value).label
        except ValueError:
            return value


class ResourceType(LabeledValue):
    MODEL = ("model", "模型")
    MCP = ("mcp", "MCP")
    SKILL = ("skill", "Skill")
    AGENT = ("agent", "智能体")


class ApplicationStatus(LabeledValue):
    PENDING = ("pending", "待审批")
    APPROVED = ("approved", "已批准")
    REJECTED = ("rejected", "已拒绝")


VALID_RESOURCE_TYPES = tuple(item.value for item in ResourceType)
RESOURCE_TYPE_PATTERN = rf"^({'|'.join(VALID_RESOURCE_TYPES)})$"


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
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    reviewed_after: datetime | None = None,
    reviewed_before: datetime | None = None,
) -> dict:
    total = await resource_application_repo.count_all(
        session,
        user_id,
        resource_type,
        None,
        status,
        created_after,
        created_before,
        reviewed_after,
        reviewed_before,
    )
    items = await resource_application_repo.find_all(
        session,
        page,
        page_size,
        user_id,
        resource_type,
        None,
        status,
        created_after,
        created_before,
        reviewed_after,
        reviewed_before,
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
    if app.status != ApplicationStatus.PENDING:
        raise ConflictError("该申请已处理")

    app.status = ApplicationStatus.APPROVED
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
    if app.status != ApplicationStatus.PENDING:
        raise ConflictError("该申请已处理")

    app.status = ApplicationStatus.REJECTED
    app.reviewed_by = reviewer_id
    app.reviewed_at = datetime.utcnow()
    app.review_notes = review_notes

    await session.commit()
    await session.refresh(app)
    return await _serialize(session, app)


async def batch_approve_applications(
    session: AsyncSession,
    app_ids: list[int],
    reviewer_id: int,
    approval_config: dict | None = None,
    review_notes: str = "",
) -> dict:
    success: list[int] = []
    failed: list[dict[str, str | int]] = []
    for app_id in app_ids:
        try:
            await approve_application(
                session, app_id, reviewer_id, approval_config, review_notes
            )
        except Exception as exc:
            await session.rollback()
            _log_batch_failure(app_id, exc)
            failed.append({"id": app_id, "reason": _review_failure_reason(exc)})
        else:
            success.append(app_id)
    return {"success": success, "failed": failed}


async def batch_reject_applications(
    session: AsyncSession,
    app_ids: list[int],
    reviewer_id: int,
    review_notes: str = "",
) -> dict:
    success: list[int] = []
    failed: list[dict[str, str | int]] = []
    for app_id in app_ids:
        try:
            await reject_application(session, app_id, reviewer_id, review_notes)
        except Exception as exc:
            await session.rollback()
            _log_batch_failure(app_id, exc)
            failed.append({"id": app_id, "reason": _review_failure_reason(exc)})
        else:
            success.append(app_id)
    return {"success": success, "failed": failed}


# ─── Internal ────────────────────────────────────────────────────────────────


def _review_failure_reason(exc: Exception) -> str:
    if isinstance(exc, NotFoundError):
        return "申请不存在"
    if isinstance(exc, ConflictError):
        return str(exc)
    return "处理失败"


def _log_batch_failure(app_id: int, exc: Exception) -> None:
    if isinstance(exc, (NotFoundError, ConflictError)):
        return
    logger.exception(
        "batch review resource application failed", extra={"app_id": app_id}
    )


async def _validate_resource_exists(
    session: AsyncSession, resource_type: str, resource_id: int
) -> None:
    if resource_type == ResourceType.MODEL:
        model = await model_repo.find_by_id(session, resource_id)
        if not model:
            raise NotFoundError("model", resource_id)
    elif resource_type == ResourceType.MCP:
        server = await mcp_repo.find_server_by_id(session, resource_id)
        if not server:
            raise NotFoundError("mcp_server", resource_id)
    elif resource_type == ResourceType.SKILL:
        skill = await skill_repo.find_by_id(session, resource_id)
        if not skill:
            raise NotFoundError("skill", resource_id)
    elif resource_type == ResourceType.AGENT:
        agent = await agent_repo.find_by_id(session, resource_id)
        if not agent:
            raise NotFoundError("agent", resource_id)


async def _grant_resource(session: AsyncSession, app: ResourceApplication) -> None:
    """审批通过时把资源授权落到用户主 Key 上。"""
    main_key = await ai_key_repo.find_personal_main(session, app.user_id)
    if not main_key:
        logger.warning("user %s has no personal_main key, skip grant", app.user_id)
        return

    if app.resource_type == ResourceType.MODEL:
        model = await model_repo.find_by_id(session, app.resource_id)
        if model and model.model_id not in (main_key.models or []):
            new_models = list(main_key.models or []) + [model.model_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, models=new_models
            )
    elif app.resource_type == ResourceType.MCP:
        if app.resource_id not in (main_key.mcps or []):
            new_mcps = list(main_key.mcps or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, mcps=new_mcps
            )
    elif app.resource_type == ResourceType.SKILL:
        if app.resource_id not in (main_key.skills or []):
            new_skills = list(main_key.skills or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, skills=new_skills
            )
    elif app.resource_type == ResourceType.AGENT:
        if app.resource_id not in (main_key.agents or []):
            new_agents = list(main_key.agents or []) + [app.resource_id]
            await ai_key_service.update_key_resources(
                session, main_key.id, agents=new_agents
            )


async def _serialize(session: AsyncSession, app: ResourceApplication) -> dict:
    resource_info = await _get_resource_info(
        session, app.resource_type, app.resource_id
    )
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
        "reviewed_at": fmt_local_time(app.reviewed_at),
        "review_notes": app.review_notes,
        "approval_config": app.approval_config,
        "created_at": fmt_local_time(app.created_at),
        "updated_at": fmt_local_time(app.updated_at),
        "user": (
            {
                "id": app.user.id,
                "username": app.user.username,
                "display_name": app.user.display_name,
            }
            if app.user
            else None
        ),
        "reviewer": (
            {
                "id": app.reviewer.id,
                "username": app.reviewer.username,
                "display_name": app.reviewer.display_name,
            }
            if app.reviewer
            else None
        ),
    }


async def list_applications_for_export(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 100000,
    user_id: int | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    reviewed_after: datetime | None = None,
    reviewed_before: datetime | None = None,
) -> list[ResourceApplication]:
    """获取审批记录的 ORM 对象列表用于导出，保留关系数据。"""
    return await resource_application_repo.find_all(
        session,
        page,
        page_size,
        user_id,
        resource_type,
        None,
        status,
        created_after,
        created_before,
        reviewed_after,
        reviewed_before,
    )


async def _get_resource_info(
    session: AsyncSession, resource_type: str, resource_id: int
) -> dict | None:
    if resource_type == ResourceType.MODEL:
        m = await model_repo.find_by_id(session, resource_id)
        if m:
            return {"id": m.id, "name": m.name, "model_id": m.model_id}
    elif resource_type == ResourceType.MCP:
        s = await mcp_repo.find_server_by_id(session, resource_id)
        if s:
            return {"id": s.id, "name": s.name, "server_name": s.server_name}
    elif resource_type == ResourceType.SKILL:
        sk = await skill_repo.find_by_id(session, resource_id)
        if sk:
            return {
                "id": sk.id,
                "name": sk.name,
                "icon": sk.icon,
                "icon_url": resolve_icon_url(sk.icon_url or sk.icon),
            }
    elif resource_type == ResourceType.AGENT:
        ag = await agent_repo.find_by_id(session, resource_id)
        if ag:
            return {
                "id": ag.id,
                "name": ag.name,
                "icon": ag.icon,
                "icon_url": resolve_icon_url(ag.icon_url or ag.icon),
                "platform": ag.platform,
            }
    return None
