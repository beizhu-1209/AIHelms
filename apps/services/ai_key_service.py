import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError, ValidationError
from models.db import AiKey
from repositories import ai_key_repo
from repositories import ai_key_model_limit_repo
from repositories import user_repo
from repositories import department_repo
from repositories import project_repo
from repositories import model_repo
from services import litellm_client

logger = logging.getLogger(__name__)

KEY_TYPE_PERSONAL_MAIN = "personal_main"
KEY_TYPE_PERSONAL_SCENE = "personal_scene"
KEY_TYPE_DEPT_SHARED = "dept_shared"
KEY_TYPE_PROJECT_SHARED = "project_shared"

VALID_KEY_TYPES = {KEY_TYPE_PERSONAL_MAIN, KEY_TYPE_PERSONAL_SCENE, KEY_TYPE_DEPT_SHARED, KEY_TYPE_PROJECT_SHARED}
VALID_OWNER_TYPES = {"user", "department", "project"}


async def list_keys(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    owner_type: str | None = None,
    owner_id: int | None = None,
    key_type: str | None = None,
) -> dict:
    total = await ai_key_repo.count_all(session, owner_type, owner_id, key_type)
    items = await ai_key_repo.find_all(session, page, page_size, owner_type, owner_id, key_type)
    return {
        "items": [_serialize_key(k) for k in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_key_by_id(session: AsyncSession, key_id: int) -> dict:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)
    return _serialize_key(key)


async def create_key(
    session: AsyncSession,
    name: str,
    key_type: str,
    owner_type: str,
    owner_id: int,
    created_by: int,
    description: str = "",
    tags: list[str] | None = None,
    models: list[str] | None = None,
    budget_limit: Decimal | None = None,
    budget_hard_limit: bool = True,
    duration: str | None = None,
) -> dict:
    if key_type not in VALID_KEY_TYPES:
        raise ConflictError(f"无效的 key 类型: {key_type}")
    if owner_type not in VALID_OWNER_TYPES:
        raise ConflictError(f"无效的 owner 类型: {owner_type}")

    # Validate owner exists
    team_id = await _resolve_owner(session, owner_type, owner_id)
    litellm_user_id = await _resolve_litellm_user(session, owner_type, owner_id)

    # Check personal_main uniqueness
    if key_type == KEY_TYPE_PERSONAL_MAIN:
        existing = await ai_key_repo.find_personal_main(session, owner_id)
        if existing:
            raise ConflictError("该用户已有主 Key")

    # Build key alias
    key_alias = _build_key_alias(key_type, owner_type, owner_id, name)

    ai_key = AiKey(
        name=name,
        description=description,
        key_type=key_type,
        owner_type=owner_type,
        owner_id=owner_id,
        tags=tags or [],
        models=models or [],
        budget_limit=budget_limit,
        budget_hard_limit=budget_hard_limit,
        is_active=False,
        created_by=created_by,
    )
    ai_key = await ai_key_repo.create(session, ai_key)

    # Sync to LiteLLM
    max_budget = float(budget_limit) if budget_limit and budget_hard_limit else None
    try:
        result = await litellm_client.create_key(
            key_alias=key_alias,
            user_id=litellm_user_id,
            team_id=team_id,
            models=models or [],
            max_budget=max_budget,
            metadata={"aihelms_key_id": ai_key.id, "key_type": key_type},
            duration=duration,
        )
        ai_key.litellm_key_id = result.get("key")
        ai_key.litellm_key_alias = key_alias
    except litellm_client.LiteLLMError:
        logger.warning("litellm create key failed for ai_key %s", ai_key.id)

    await session.commit()
    await session.refresh(ai_key)

    data = _serialize_key(ai_key)
    # Return full key value only on creation
    data["key_value"] = result.get("key") if ai_key.litellm_key_id else None
    return data


async def update_key(
    session: AsyncSession,
    key_id: int,
    name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    models: list[str] | None = None,
    budget_limit: Decimal | None = None,
    budget_hard_limit: bool | None = None,
) -> dict:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    if name is not None:
        key.name = name
    if description is not None:
        key.description = description
    if tags is not None:
        key.tags = tags
    if models is not None:
        key.models = models
    if budget_limit is not None:
        key.budget_limit = budget_limit
    if budget_hard_limit is not None:
        key.budget_hard_limit = budget_hard_limit

    # Sync model/budget changes to LiteLLM
    if key.litellm_key_id and (models is not None or budget_limit is not None or budget_hard_limit is not None):
        effective_hard = key.budget_hard_limit
        effective_budget = float(key.budget_limit) if key.budget_limit and effective_hard else None
        try:
            await litellm_client.update_key(
                key_id=key.litellm_key_id,
                models=key.models if models is not None else None,
                max_budget=effective_budget,
            )
        except litellm_client.LiteLLMError:
            logger.warning("litellm update key failed for ai_key %s", key_id)

    await session.commit()
    await session.refresh(key)
    return _serialize_key(key)


async def toggle_key(session: AsyncSession, key_id: int) -> dict:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    key.is_active = not key.is_active

    # Sync budget: active + hard_limit → set budget; inactive → set budget to 0 to block
    if key.litellm_key_id:
        if key.is_active:
            max_budget = float(key.budget_limit) if key.budget_limit and key.budget_hard_limit else None
        else:
            max_budget = 0.0
        try:
            await litellm_client.update_key_budget(key.litellm_key_id, max_budget)
        except litellm_client.LiteLLMError:
            logger.warning("litellm toggle key failed for ai_key %s", key_id)

    await session.commit()
    await session.refresh(key)
    return _serialize_key(key)


async def delete_key(session: AsyncSession, key_id: int) -> None:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    if key.litellm_key_id:
        try:
            await litellm_client.delete_key(key.litellm_key_id)
        except litellm_client.LiteLLMError:
            logger.warning("litellm delete key failed for ai_key %s", key_id)

    await session.delete(key)
    await session.commit()


async def get_my_keys(session: AsyncSession, user_id: int) -> dict:
    """Get all keys accessible to a user: personal + dept shared + project shared."""
    personal_keys = await ai_key_repo.find_by_user(session, user_id)

    # Find user's departments
    user_depts = await user_repo.find_user_departments(session, user_id)
    dept_keys: list[AiKey] = []
    for ud in user_depts:
        keys = await ai_key_repo.find_by_owner(session, "department", ud.department_id)
        dept_keys.extend(keys)

    # Find user's projects
    user_projects = await user_repo.find_user_projects(session, user_id)
    project_keys: list[AiKey] = []
    for up in user_projects:
        keys = await ai_key_repo.find_by_owner(session, "project", up.project_id)
        project_keys.extend(keys)

    return {
        "personal": [_serialize_key(k) for k in personal_keys],
        "department": [_serialize_key(k) for k in dept_keys],
        "project": [_serialize_key(k) for k in project_keys],
    }


async def create_personal_main_key(session: AsyncSession, user_id: int, username: str) -> AiKey | None:
    """Auto-create a personal main key for a new user (disabled by default)."""
    existing = await ai_key_repo.find_personal_main(session, user_id)
    if existing:
        return existing

    key_alias = f"user:{username}/main"
    ai_key = AiKey(
        name="主 Key",
        description="个人主 Key，审批通过后启用",
        key_type=KEY_TYPE_PERSONAL_MAIN,
        owner_type="user",
        owner_id=user_id,
        tags=[],
        models=[],
        is_active=False,
        created_by=user_id,
    )
    ai_key = await ai_key_repo.create(session, ai_key)

    # Get user's litellm_user_id
    user = await user_repo.find_user_by_id(session, user_id)
    litellm_user_id = user.litellm_user_id if user else None

    try:
        result = await litellm_client.create_key(
            key_alias=key_alias,
            user_id=litellm_user_id,
            max_budget=0.0,  # disabled by default
            metadata={"aihelms_key_id": ai_key.id, "key_type": KEY_TYPE_PERSONAL_MAIN},
        )
        ai_key.litellm_key_id = result.get("key")
        ai_key.litellm_key_alias = key_alias
    except litellm_client.LiteLLMError:
        logger.warning("litellm create main key failed for user %s", user_id)

    return ai_key


# --- Identity list ---


async def list_identity(
    session: AsyncSession,
    tab: str,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> dict:
    if tab == "user":
        return await _list_identity_users(session, page, page_size, keyword)
    elif tab == "department":
        return await _list_identity_departments(session, page, page_size, keyword)
    elif tab == "project":
        return await _list_identity_projects(session, page, page_size, keyword)
    raise ValidationError(f"无效的 tab 参数: {tab}")


async def _list_identity_users(
    session: AsyncSession, page: int, page_size: int, keyword: str | None
) -> dict:
    users, total = await user_repo.find_users_paginated(session, page, page_size, keyword)
    items = []
    for user in users:
        user_keys = await ai_key_repo.find_by_user(session, user.id)
        main_key = next((k for k in user_keys if k.key_type == KEY_TYPE_PERSONAL_MAIN), None)
        scene_keys = [k for k in user_keys if k.key_type == KEY_TYPE_PERSONAL_SCENE]

        dept_name = ""
        if user.departments:
            dept_name = user.departments[0].department.name if user.departments[0].department else ""

        items.append({
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "department_name": dept_name,
            },
            "main_key": _serialize_key_with_models(main_key, session) if main_key else None,
            "scene_keys": [_serialize_key_with_models(k, session) for k in scene_keys],
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _list_identity_departments(
    session: AsyncSession, page: int, page_size: int, keyword: str | None
) -> dict:
    depts, total = await department_repo.find_paginated(session, page, page_size, keyword)
    items = []
    for dept in depts:
        dept_keys = await ai_key_repo.find_by_owner(session, "department", dept.id)
        items.append({
            "department": {"id": dept.id, "name": dept.name},
            "keys": [_serialize_key_with_models(k, session) for k in dept_keys],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _list_identity_projects(
    session: AsyncSession, page: int, page_size: int, keyword: str | None
) -> dict:
    projects, total = await project_repo.find_paginated(session, page, page_size, keyword)
    items = []
    for proj in projects:
        proj_keys = await ai_key_repo.find_by_owner(session, "project", proj.id)
        items.append({
            "project": {"id": proj.id, "name": proj.name},
            "keys": [_serialize_key_with_models(k, session) for k in proj_keys],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# --- Model limits ---


async def get_model_limits(session: AsyncSession, key_id: int) -> list[dict]:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    limits = await ai_key_model_limit_repo.find_by_key_id(session, key_id)
    result = []
    for limit in limits:
        model = await model_repo.find_by_id(session, limit.model_id)
        if not model:
            continue
        result.append({
            "model_id": model.id,
            "model_name": model.name,
            "model_model_id": model.model_id,
            "tpm": limit.tpm,
            "rpm": limit.rpm,
            "max_tokens": limit.max_tokens,
            "max_calls": limit.max_calls,
        })
    return result


async def set_model_limits(
    session: AsyncSession,
    key_id: int,
    limits: list[dict],
) -> list[dict]:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    # Validate and upsert
    incoming_model_ids = set()
    for item in limits:
        mid = item["model_id"]
        incoming_model_ids.add(mid)
        model = await model_repo.find_by_id(session, mid)
        if not model:
            raise NotFoundError("model", mid)

        await ai_key_model_limit_repo.upsert(
            session,
            ai_key_id=key_id,
            model_id=mid,
            tpm=item.get("tpm"),
            rpm=item.get("rpm"),
            max_tokens=item.get("max_tokens"),
            max_calls=item.get("max_calls"),
        )

    # Delete limits for models not in the incoming list
    existing_limits = await ai_key_model_limit_repo.find_by_key_id(session, key_id)
    for existing in existing_limits:
        if existing.model_id not in incoming_model_ids:
            await ai_key_model_limit_repo.delete_by_key_and_model(
                session, key_id, existing.model_id
            )

    await session.commit()
    return await get_model_limits(session, key_id)


async def delete_model_limit(session: AsyncSession, key_id: int, model_id: int) -> None:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    deleted = await ai_key_model_limit_repo.delete_by_key_and_model(session, key_id, model_id)
    if not deleted:
        raise NotFoundError("model_limit", f"{key_id}/{model_id}")
    await session.commit()


# --- Private helpers ---


def _serialize_key_with_models(key: AiKey, session) -> dict:
    data = _serialize_key(key)
    return data


async def _resolve_owner(session: AsyncSession, owner_type: str, owner_id: int) -> str | None:
    """Resolve the LiteLLM team_id for the owner. Returns None for personal keys."""
    if owner_type == "user":
        user = await user_repo.find_user_by_id(session, owner_id)
        if not user:
            raise NotFoundError("user", owner_id)
        return None
    elif owner_type == "department":
        dept = await department_repo.find_by_id(session, owner_id)
        if not dept or not dept.is_active:
            raise NotFoundError("department", owner_id)
        return dept.litellm_team_id
    elif owner_type == "project":
        project = await project_repo.find_by_id(session, owner_id)
        if not project or not project.is_active:
            raise NotFoundError("project", owner_id)
        return project.litellm_team_id
    return None


async def _resolve_litellm_user(session: AsyncSession, owner_type: str, owner_id: int) -> str | None:
    """Resolve the LiteLLM user_id. Only for personal keys."""
    if owner_type == "user":
        user = await user_repo.find_user_by_id(session, owner_id)
        return user.litellm_user_id if user else None
    return None


def _build_key_alias(key_type: str, owner_type: str, owner_id: int, name: str) -> str:
    if key_type == KEY_TYPE_PERSONAL_MAIN:
        return f"user:{owner_id}/main"
    elif key_type == KEY_TYPE_PERSONAL_SCENE:
        return f"user:{owner_id}/{name}"
    elif key_type == KEY_TYPE_DEPT_SHARED:
        return f"dept:{owner_id}/{name}"
    elif key_type == KEY_TYPE_PROJECT_SHARED:
        return f"proj:{owner_id}/{name}"
    return f"{owner_type}:{owner_id}/{name}"


def _serialize_key(key: AiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "description": key.description,
        "key_type": key.key_type,
        "owner_type": key.owner_type,
        "owner_id": key.owner_id,
        "tags": key.tags,
        "litellm_key_id": key.litellm_key_id,
        "litellm_key_alias": key.litellm_key_alias,
        "models": key.models,
        "budget_limit": str(key.budget_limit) if key.budget_limit else None,
        "budget_hard_limit": key.budget_hard_limit,
        "is_active": key.is_active,
        "created_by": key.created_by,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "updated_at": key.updated_at.isoformat() if key.updated_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
    }
