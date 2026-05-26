import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError
from models.db import Agent, AgentCategory, AgentPlatform, AgentUsageLog, AiKey
from repositories import agent_repo

logger = logging.getLogger(__name__)


# ─── Agent CRUD ──────────────────────────────────────────────────────────────


async def list_agents(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    platform: str | None = None,
    is_published: bool | None = None,
) -> dict:
    total = await agent_repo.count_all(session, category, platform, is_published)
    items = await agent_repo.find_all(session, page, page_size, category, platform, is_published)
    return {
        "items": [_serialize(a) for a in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_agent(session: AsyncSession, agent_id: int) -> dict:
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)
    return _serialize(agent)


async def create_agent(
    session: AsyncSession,
    name: str,
    platform: str,
    icon: str = "",
    description: str = "",
    category: str = "general",
    chat_url: str = "",
    external_id: str = "",
    tags: list | None = None,
    is_published: bool = False,
    requires_approval: bool = False,
    status: str = "online",
    department_id: int | None = None,
    project_id: int | None = None,
    cost_attribution: str = "owner",
    created_by: int | None = None,
) -> dict:
    aid = str(uuid.uuid4())
    agent = Agent(
        agent_id=aid,
        name=name,
        icon=icon,
        description=description,
        platform=platform,
        category=category,
        chat_url=chat_url,
        external_id=external_id,
        tags=tags or [],
        is_published=is_published,
        requires_approval=requires_approval,
        status=status,
        department_id=department_id,
        project_id=project_id,
        cost_attribution=cost_attribution,
        created_by=created_by,
    )
    agent = await agent_repo.create(session, agent)

    # 发布且不需要审批时，自动同步到所有主 Key
    if is_published and not requires_approval:
        from services import ai_key_service
        await ai_key_service.sync_public_resource_to_all_keys(session, "agents", agent.id)

    await session.commit()
    await session.refresh(agent)
    return _serialize(agent)


async def update_agent(session: AsyncSession, agent_id: int, **kwargs) -> dict:
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)
    for key, value in kwargs.items():
        if hasattr(agent, key) and value is not None:
            setattr(agent, key, value)

    # 发布且不需要审批时，自动同步到所有主 Key
    if agent.is_published and not agent.requires_approval:
        from services import ai_key_service
        await ai_key_service.sync_public_resource_to_all_keys(session, "agents", agent.id)

    await session.commit()
    await session.refresh(agent)
    return _serialize(agent)


async def delete_agent(session: AsyncSession, agent_id: int) -> None:
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)
    await agent_repo.delete(session, agent_id)
    await session.commit()


# ─── Usage Logs ─────────────────────────────────────────────────────────────


async def record_usage(
    session: AsyncSession, agent_id: int, user_id: int, session_id: str = ""
) -> dict:
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)

    is_first = not await agent_repo.has_user_used(session, agent_id, user_id)

    log = AgentUsageLog(agent_id=agent_id, user_id=user_id, session_id=session_id)
    await agent_repo.create_usage_log(session, log)

    agent.call_count = (agent.call_count or 0) + 1
    if is_first:
        agent.user_count = (agent.user_count or 0) + 1

    await session.commit()
    return {"call_count": agent.call_count, "user_count": agent.user_count, "is_first": is_first}


async def list_usage_logs(
    session: AsyncSession,
    agent_id: int,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
) -> dict:
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)
    total = await agent_repo.count_usage_logs(session, agent_id, user_id)
    items = await agent_repo.find_usage_logs(session, agent_id, page, page_size, user_id)
    serialized = []
    for log in items:
        serialized.append({
            "id": log.id,
            "agent_id": log.agent_id,
            "user_id": log.user_id,
            "session_id": log.session_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"items": serialized, "total": total, "page": page, "page_size": page_size}


# ─── Categories ──────────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[dict]:
    cats = await agent_repo.list_categories(session)
    return [
        {"id": c.id, "name": c.name, "description": c.description, "sort_order": c.sort_order}
        for c in cats
    ]


async def create_category(
    session: AsyncSession, name: str, description: str = "", sort_order: int = 0
) -> dict:
    existing = await agent_repo.find_category_by_name(session, name)
    if existing:
        raise ConflictError(f"分类 '{name}' 已存在")
    cat = AgentCategory(name=name, description=description, sort_order=sort_order)
    cat = await agent_repo.create_category(session, cat)
    await session.commit()
    return {"id": cat.id, "name": cat.name, "description": cat.description, "sort_order": cat.sort_order}


async def delete_category(session: AsyncSession, category_id: int) -> None:
    cat = await agent_repo.find_category_by_id(session, category_id)
    if not cat:
        raise NotFoundError("agent_category", category_id)
    await agent_repo.delete_category(session, category_id)
    await session.commit()


# ─── Platforms ───────────────────────────────────────────────────────────────


async def list_platforms(session: AsyncSession) -> list[dict]:
    plats = await agent_repo.list_platforms(session)
    return [
        {"id": p.id, "name": p.name, "label": p.label, "description": p.description, "sort_order": p.sort_order}
        for p in plats
    ]


async def create_platform(
    session: AsyncSession, name: str, label: str = "", description: str = "", sort_order: int = 0
) -> dict:
    existing = await agent_repo.find_platform_by_name(session, name)
    if existing:
        raise ConflictError(f"平台 '{name}' 已存在")
    plat = AgentPlatform(name=name, label=label or name, description=description, sort_order=sort_order)
    plat = await agent_repo.create_platform(session, plat)
    await session.commit()
    return {"id": plat.id, "name": plat.name, "label": plat.label, "description": plat.description, "sort_order": plat.sort_order}


async def delete_platform(session: AsyncSession, platform_id: int) -> None:
    plat = await agent_repo.find_platform_by_id(session, platform_id)
    if not plat:
        raise NotFoundError("agent_platform", platform_id)
    await agent_repo.delete_platform(session, platform_id)
    await session.commit()


async def resolve_key(session: AsyncSession, agent_id: int, user_id: int) -> dict:
    """根据智能体的 cost_attribution 模式返回对应的 Key 信息。"""
    agent = await agent_repo.find_by_id(session, agent_id)
    if not agent:
        raise NotFoundError("agent", agent_id)

    if agent.cost_attribution == "owner":
        # owner 模式：返回智能体绑定的场景 Key
        if not agent.ai_key_id:
            raise NotFoundError("agent_key", agent_id)
        result = await session.execute(
            select(AiKey).where(AiKey.id == agent.ai_key_id)
        )
        key = result.scalar_one_or_none()
        if not key:
            raise NotFoundError("ai_key", agent.ai_key_id)
        return {
            "mode": "owner",
            "key_value": key.key_value,
            "litellm_key_id": key.litellm_key_id,
            "key_name": key.key_name,
            "models": key.models,
            "mcps": key.mcps or [],
        }
    else:
        # user 模式：查找该用户针对此智能体的场景 Key
        result = await session.execute(
            select(AiKey).where(
                AiKey.user_id == user_id,
                AiKey.key_type == "scene",
                AiKey.key_name.contains(f"agent-{agent.id}"),
            )
        )
        key = result.scalar_one_or_none()
        if not key:
            raise NotFoundError("user_agent_key", agent_id)
        return {
            "mode": "user",
            "key_value": key.key_value,
            "litellm_key_id": key.litellm_key_id,
            "key_name": key.key_name,
            "models": key.models,
            "mcps": key.mcps or [],
        }


# ─── Serializer ──────────────────────────────────────────────────────────────


def _serialize(agent: Agent) -> dict:
    return {
        "id": agent.id,
        "agent_id": agent.agent_id,
        "name": agent.name,
        "icon": agent.icon,
        "description": agent.description,
        "platform": agent.platform,
        "category": agent.category,
        "department_id": agent.department_id,
        "project_id": agent.project_id,
        "cost_attribution": agent.cost_attribution,
        "ai_key_id": agent.ai_key_id,
        "chat_url": agent.chat_url,
        "external_id": agent.external_id,
        "tags": agent.tags,
        "is_active": agent.is_active,
        "is_published": agent.is_published,
        "requires_approval": agent.requires_approval,
        "status": agent.status,
        "user_count": agent.user_count,
        "call_count": agent.call_count,
        "created_by": agent.created_by,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
