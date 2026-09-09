import logging
from collections.abc import Awaitable, Callable
from datetime import date
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from services import (
    agent_service,
    ai_key_service,
    auth_service,
    efficiency_service,
    mcp_service,
    model_service,
    resource_application_service,
    skill_service,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _current_month() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today


def _hub_user(user: dict[str, object]) -> dict[str, object]:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "display_name": user["display_name"],
        "avatar": user["avatar"],
        "position": user["position"],
        "is_admin": user["is_admin"],
        "departments": user["departments"],
    }


def _hub_key(key: dict[str, object]) -> dict[str, object]:
    return {
        "id": key["id"],
        "name": key["name"],
        "description": key["description"],
        "key_type": key["key_type"],
        "key_value": key.get("key_value") or key.get("litellm_key_id"),
        "models": key["models"],
        "mcps": key["mcps"],
        "skills": key["skills"],
        "agents": key["agents"],
        "budget_limit": key["budget_limit"],
        "budget_used": key["budget_used"],
        "budget_hard_limit": key["budget_hard_limit"],
        "budget_duration": key["budget_duration"],
        "budget_scope": key["budget_scope"],
        "budget_models_total": key["budget_models_total"],
        "budget_mcps_total": key["budget_mcps_total"],
        "budget_models_per": key["budget_models_per"],
        "budget_mcps_per": key["budget_mcps_per"],
        "model_budgets": key["model_budgets"],
        "mcp_budgets": key["mcp_budgets"],
        "rate_limit_mode": key["rate_limit_mode"],
        "tpm_limit": key["tpm_limit"],
        "rpm_limit": key["rpm_limit"],
        "max_parallel_requests": key["max_parallel_requests"],
        "is_active": key["is_active"],
        "expires_at": key["expires_at"],
    }


async def _main_key(session: AsyncSession, user_id: int) -> dict[str, object] | None:
    keys = await ai_key_service.get_my_keys(session, user_id)
    main_key = next(
        (key for key in keys["personal"] if key["key_type"] == "personal_main"),
        None,
    )
    return _hub_key(main_key) if main_key else None


def _hub_agent(agent: dict[str, object]) -> dict[str, object]:
    return {
        "id": agent["id"],
        "name": agent["name"],
        "icon_url": agent["icon_url"],
        "description": agent["description"],
        "platform": agent["platform"],
        "category": agent["category"],
        "chat_url": agent["chat_url"],
        "tags": agent["tags"],
        "requires_approval": agent["requires_approval"],
        "status": agent["status"],
        "user_count": agent["user_count"],
    }


def _hub_skill(skill: dict[str, object]) -> dict[str, object]:
    return {
        "id": skill["id"],
        "name": skill["name"],
        "icon_url": skill["icon_url"],
        "description": skill["description"],
        "category": skill["category"],
        "tags": skill["tags"],
        "author": skill["author"],
        "requires_approval": skill["requires_approval"],
        "install_count": skill["install_count"],
    }


def _hub_mcp(server: dict[str, object]) -> dict[str, object]:
    return {
        "id": server["id"],
        "name": server["name"],
        "icon_url": server["icon_url"],
        "description": server["description"],
        "category": server["category"],
        "tags": server["tags"],
        "author": server["author"],
        "requires_approval": server["requires_approval"],
        "status": server["status"],
        "call_count": server["call_count"],
    }


def _hub_application(application: dict[str, object]) -> dict[str, object]:
    return {
        "id": application["id"],
        "resource_type": application["resource_type"],
        "resource_id": application["resource_id"],
        "resource_info": application["resource_info"],
        "status": application["status"],
        "created_at": application["created_at"],
    }


def _paged(
    result: dict[str, object],
    serializer: Callable[[dict[str, object]], dict[str, object]],
) -> dict[str, object]:
    items = result["items"]
    if not isinstance(items, list):
        raise TypeError("paged items must be a list")
    return {
        "items": [serializer(item) for item in items],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


def _empty_page(page_size: int) -> dict[str, object]:
    return {"items": [], "total": 0, "page": 1, "page_size": page_size}


async def _optional_block(
    session: AsyncSession,
    name: str,
    loader: Callable[[], Awaitable[T]],
    fallback: T,
) -> T:
    try:
        return await loader()
    except Exception:
        await session.rollback()
        logger.warning("Hub AI identity %s unavailable", name, exc_info=True)
        return fallback


async def _applications(session: AsyncSession, user_id: int) -> dict[str, object]:
    result = await resource_application_service.list_applications(
        session, 1, 10, user_id
    )
    return _paged(result, _hub_application)


async def _mcp(session: AsyncSession) -> dict[str, object]:
    result = await mcp_service.list_servers(session, 1, 200, None, None, True, None)
    return _paged(result, _hub_mcp)


async def _skills(session: AsyncSession) -> dict[str, object]:
    result = await skill_service.list_skills(session, 1, 200, None, True)
    return _paged(result, _hub_skill)


async def get_ai_identity(session: AsyncSession, user_id: int) -> dict[str, object]:
    start_date, end_date = _current_month()
    user = _hub_user(await auth_service.get_current_user_info(session, user_id))
    main_key = await _main_key(session, user_id)

    return {
        "user": user,
        "keys": {"personal": {"main_key": main_key}},
        "overview": await _optional_block(
            session,
            "overview",
            lambda: efficiency_service.get_user_overview(
                session, start_date, end_date, user_id
            ),
            None,
        ),
        "trend": await _optional_block(
            session,
            "trend",
            lambda: efficiency_service.get_trend(
                session, start_date, end_date, "day", user_id
            ),
            [],
        ),
        "applications": await _optional_block(
            session,
            "applications",
            lambda: _applications(session, user_id),
            _empty_page(10),
        ),
        "mcp": await _optional_block(
            session, "MCP list", lambda: _mcp(session), _empty_page(200)
        ),
        "skills": await _optional_block(
            session, "Skill list", lambda: _skills(session), _empty_page(200)
        ),
        "models": await _optional_block(
            session,
            "model list",
            lambda: model_service.get_all_active_models(session),
            [],
        ),
    }


async def get_agent_center(
    session: AsyncSession, user_id: int, page: int, page_size: int
) -> dict[str, object]:
    agents = await agent_service.list_agents(session, page, page_size, None, None, True)
    return {
        "agents": _paged(agents, _hub_agent),
        "keys": {"personal": {"main_key": await _main_key(session, user_id)}},
    }


async def get_market(
    session: AsyncSession, user_id: int, page: int, page_size: int
) -> dict[str, object]:
    skills = await skill_service.list_skills(session, page, page_size, None, True)
    mcp = await mcp_service.list_servers(
        session, page, page_size, None, None, True, None
    )
    return {
        "skills": _paged(skills, _hub_skill),
        "mcp": _paged(mcp, _hub_mcp),
        "keys": {"personal": {"main_key": await _main_key(session, user_id)}},
    }


async def get_model_square(session: AsyncSession, user_id: int) -> dict[str, object]:
    return {
        "models": await model_service.get_all_active_models(session),
        "keys": {"personal": {"main_key": await _main_key(session, user_id)}},
    }
