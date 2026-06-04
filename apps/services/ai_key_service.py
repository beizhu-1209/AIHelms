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
from repositories import mcp_repo
from services import litellm_client
from services.model_service import ANTHROPIC_MODEL_SUFFIX

logger = logging.getLogger(__name__)

KEY_TYPE_PERSONAL_MAIN = "personal_main"
KEY_TYPE_PERSONAL_SCENE = "personal_scene"
KEY_TYPE_DEPT_MAIN = "dept_main"
KEY_TYPE_DEPT_SCENE = "dept_scene"
KEY_TYPE_PROJECT_MAIN = "project_main"
KEY_TYPE_PROJECT_SCENE = "project_scene"

VALID_KEY_TYPES = {
    KEY_TYPE_PERSONAL_MAIN, KEY_TYPE_PERSONAL_SCENE,
    KEY_TYPE_DEPT_MAIN, KEY_TYPE_DEPT_SCENE,
    KEY_TYPE_PROJECT_MAIN, KEY_TYPE_PROJECT_SCENE,
}
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
    mcps: list[int] | None = None,
    skills: list[int] | None = None,
    agents: list[int] | None = None,
    budget_limit: Decimal | None = None,
    budget_hard_limit: bool = False,
    budget_duration: str | None = "30d",
    budget_scope: str = "unified",
    budget_models_total: Decimal | None = None,
    budget_mcps_total: Decimal | None = None,
    budget_models_per: str = "unified",
    budget_mcps_per: str = "unified",
    model_budgets: dict[str, float] | None = None,
    mcp_budgets: dict[str, float] | None = None,
    scenario_id: int | None = None,
    duration: str | None = None,
    rate_limits: list[dict] | None = None,
) -> dict:
    if key_type not in VALID_KEY_TYPES:
        raise ConflictError(f"无效的 key 类型: {key_type}")
    if owner_type not in VALID_OWNER_TYPES:
        raise ConflictError(f"无效的 owner 类型: {owner_type}")

    # Validate owner exists
    team_id = await _resolve_owner(session, owner_type, owner_id)
    litellm_user_id = await _resolve_litellm_user(session, owner_type, owner_id)

    # Check main key uniqueness (only one main key per owner)
    main_types = {KEY_TYPE_PERSONAL_MAIN, KEY_TYPE_DEPT_MAIN, KEY_TYPE_PROJECT_MAIN}
    if key_type in main_types:
        existing = await ai_key_repo.find_main_key(session, owner_type, owner_id, key_type)
        if existing:
            raise ConflictError("该归属已有主 Key")

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
        mcps=mcps or [],
        skills=skills or [],
        agents=agents or [],
        budget_limit=budget_limit,
        budget_hard_limit=budget_hard_limit,
        budget_duration=budget_duration,
        budget_scope=budget_scope,
        budget_models_total=budget_models_total,
        budget_mcps_total=budget_mcps_total,
        budget_models_per=budget_models_per,
        budget_mcps_per=budget_mcps_per,
        model_budgets=model_budgets or {},
        mcp_budgets=mcp_budgets or {},
        scenario_id=scenario_id,
        is_active=False,
        created_by=created_by,
    )
    ai_key = await ai_key_repo.create(session, ai_key)

    # Sync to LiteLLM
    max_budget = float(budget_limit) if budget_limit and budget_hard_limit else None
    litellm_duration = budget_duration if budget_duration and budget_limit else duration
    litellm_models, litellm_model_budgets = await _expand_models_with_anthropic(
        session, models or [], model_budgets
    )
    mcp_server_names = await _resolve_mcp_server_names(session, mcps or [])
    result = await litellm_client.create_key(
        key_alias=key_alias,
        user_id=litellm_user_id,
        team_id=team_id,
        models=litellm_models,
        max_budget=max_budget,
        metadata={"aihelms_key_id": ai_key.id, "key_type": key_type},
        duration=litellm_duration,
        allowed_mcp_servers=mcp_server_names if mcp_server_names else None,
    )
    ai_key.litellm_key_id = result.get("key")
    ai_key.litellm_key_alias = key_alias

    # Sync model_max_budget if set
    if litellm_model_budgets and ai_key.litellm_key_id:
        await litellm_client.update_key(
            key_id=ai_key.litellm_key_id,
            model_max_budget=litellm_model_budgets,
        )

    await session.commit()
    await session.refresh(ai_key)

    # Save rate limits if provided
    if rate_limits:
        await _save_rate_limits(session, ai_key.id, rate_limits)

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
    mcps: list[int] | None = None,
    skills: list[int] | None = None,
    agents: list[int] | None = None,
    budget_limit: Decimal | None = None,
    budget_hard_limit: bool | None = None,
    budget_duration: str | None = None,
    budget_scope: str | None = None,
    budget_models_total: Decimal | None = None,
    budget_mcps_total: Decimal | None = None,
    budget_models_per: str | None = None,
    budget_mcps_per: str | None = None,
    model_budgets: dict[str, float] | None = None,
    mcp_budgets: dict[str, float] | None = None,
    scenario_id: int | None = None,
    rate_limits: list[dict] | None = None,
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
    if mcps is not None:
        key.mcps = mcps
    if skills is not None:
        key.skills = skills
    if agents is not None:
        key.agents = agents
    if budget_limit is not None:
        key.budget_limit = budget_limit
    if budget_hard_limit is not None:
        key.budget_hard_limit = budget_hard_limit
    if budget_duration is not None:
        key.budget_duration = budget_duration
    if budget_scope is not None:
        key.budget_scope = budget_scope
    if budget_models_total is not None:
        key.budget_models_total = budget_models_total
    if budget_mcps_total is not None:
        key.budget_mcps_total = budget_mcps_total
    if budget_models_per is not None:
        key.budget_models_per = budget_models_per
    if budget_mcps_per is not None:
        key.budget_mcps_per = budget_mcps_per
    if model_budgets is not None:
        key.model_budgets = model_budgets
    if mcp_budgets is not None:
        key.mcp_budgets = mcp_budgets
    if scenario_id is not None:
        key.scenario_id = scenario_id

    await _sync_key_to_litellm(
        key,
        models_changed=models is not None,
        mcps_changed=mcps is not None,
        budget_changed=(budget_limit is not None or budget_hard_limit is not None or budget_duration is not None),
        model_budgets_changed=model_budgets is not None,
        session=session,
    )

    await session.commit()
    await session.refresh(key)

    if rate_limits is not None:
        await _save_rate_limits(session, key_id, rate_limits)

    return _serialize_key(key)


async def update_key_resources(
    session: AsyncSession,
    key_id: int,
    models: list[str] | None = None,
    mcps: list[int] | None = None,
    skills: list[int] | None = None,
    agents: list[int] | None = None,
) -> None:
    """审批通过后给主 Key 追加资源。仅做资源同步，不动其他字段。"""
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        return
    if models is not None:
        key.models = models
    if mcps is not None:
        key.mcps = mcps
    if skills is not None:
        key.skills = skills
    if agents is not None:
        key.agents = agents
    await _sync_key_to_litellm(key, models is not None, mcps is not None, False, False, session=session)


async def _resolve_mcp_server_names(
    session: AsyncSession, mcp_ids: list[int]
) -> list[str]:
    """Convert MCP server IDs to server_name list for LiteLLM."""
    if not mcp_ids:
        return []
    names = []
    for mcp_id in mcp_ids:
        server = await mcp_repo.find_server_by_id(session, mcp_id)
        if server:
            names.append(server.server_name)
    return names


async def _expand_models_with_anthropic(
    session: AsyncSession,
    model_ids: list[str],
    model_budgets: dict[str, float] | None,
) -> tuple[list[str], dict[str, float] | None]:
    """Expand model list with (Anthropic) variants for models that have anthropic deployments."""
    if not model_ids:
        return model_ids, model_budgets
    anthropic_models = await model_repo.find_model_ids_with_anthropic_deployments(session, model_ids)
    if not anthropic_models:
        return model_ids, model_budgets

    expanded_models = list(model_ids)
    for mid in model_ids:
        if mid in anthropic_models:
            variant = f"{mid}{ANTHROPIC_MODEL_SUFFIX}"
            if variant not in expanded_models:
                expanded_models.append(variant)

    expanded_budgets = model_budgets
    if model_budgets:
        expanded_budgets = dict(model_budgets)
        for mid in list(model_budgets.keys()):
            if mid in anthropic_models:
                variant = f"{mid}{ANTHROPIC_MODEL_SUFFIX}"
                if variant not in expanded_budgets:
                    expanded_budgets[variant] = model_budgets[mid]

    return expanded_models, expanded_budgets


async def _sync_key_to_litellm(
    key,
    models_changed: bool,
    mcps_changed: bool,
    budget_changed: bool,
    model_budgets_changed: bool,
    session: AsyncSession | None = None,
) -> None:
    if not key.litellm_key_id:
        return
    if not (models_changed or mcps_changed or budget_changed or model_budgets_changed):
        return

    effective_hard = key.budget_hard_limit
    effective_budget = float(key.budget_limit) if key.budget_limit and effective_hard else None

    # Expand models with (Anthropic) variants
    litellm_models = key.models
    litellm_model_budgets = key.model_budgets if model_budgets_changed else None
    if session and (models_changed or model_budgets_changed):
        litellm_models, litellm_model_budgets = await _expand_models_with_anthropic(
            session, key.models, key.model_budgets if model_budgets_changed else None
        )

    # Resolve MCP server names from IDs
    mcp_server_names: list[str] | None = None
    if mcps_changed and session:
        mcp_server_names = await _resolve_mcp_server_names(session, key.mcps or [])

    await litellm_client.update_key(
        key_id=key.litellm_key_id,
        models=litellm_models if models_changed else None,
        max_budget=effective_budget,
        model_max_budget=litellm_model_budgets,
        allowed_mcp_servers=mcp_server_names,
    )


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
        await litellm_client.update_key_budget(key.litellm_key_id, max_budget)

    await session.commit()
    await session.refresh(key)
    return _serialize_key(key)


async def sync_user_keys_active(session: AsyncSession, user_id: int, active: bool) -> int:
    """随用户启用/禁用，同步其名下所有 AI Key 在 LiteLLM 侧的可用性。

    禁用用户 -> 名下 key 预算卡成 0（沿用 toggle_key 的禁用模式）；
    启用用户 -> 恢复各 key 预算（有 hard_limit 则按 budget_limit，否则 None）。
    平台侧同步 key.is_active。不在此提交事务，由调用方统一 commit。
    """
    keys = await ai_key_repo.find_by_user(session, user_id)
    synced = 0
    for key in keys:
        key.is_active = active
        if not key.litellm_key_id:
            continue
        if active:
            max_budget = float(key.budget_limit) if key.budget_limit and key.budget_hard_limit else None
        else:
            max_budget = 0.0
        try:
            await litellm_client.update_key_budget(key.litellm_key_id, max_budget)
            synced += 1
        except litellm_client.LiteLLMError as e:
            logger.error("sync user key %s active=%s failed: %s", key.id, active, e)
    return synced


async def delete_key(session: AsyncSession, key_id: int) -> None:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    if key.litellm_key_id:
        await litellm_client.delete_key(key.litellm_key_id)

    await session.delete(key)
    await session.commit()


async def batch_create_keys(
    session: AsyncSession,
    user_ids: list[int],
    key_type: str,
    name_template: str,
    created_by: int,
    description: str = "",
    models: list[str] | None = None,
    mcps: list[int] | None = None,
    skills: list[int] | None = None,
    agents: list[int] | None = None,
    budget_limit: Decimal | None = None,
    budget_hard_limit: bool = False,
    budget_duration: str | None = "30d",
    budget_scope: str = "unified",
    budget_models_total: Decimal | None = None,
    budget_mcps_total: Decimal | None = None,
    budget_models_per: str = "unified",
    budget_mcps_per: str = "unified",
    model_budgets: dict[str, float] | None = None,
    mcp_budgets: dict[str, float] | None = None,
    scenario_id: int | None = None,
    rate_limits: list[dict] | None = None,
) -> list[dict]:
    if key_type not in {KEY_TYPE_PERSONAL_MAIN, KEY_TYPE_PERSONAL_SCENE}:
        raise ValidationError("批量创建仅支持个人主 Key 和场景 Key")

    results = []
    for user_id in user_ids:
        user = await user_repo.find_user_by_id(session, user_id)
        if not user:
            results.append({"user_id": user_id, "success": False, "error": "用户不存在"})
            continue

        name = name_template.replace("{username}", user.username or "")
        name = name.replace("{display_name}", user.display_name or user.username or "")

        if key_type == KEY_TYPE_PERSONAL_MAIN:
            existing = await ai_key_repo.find_personal_main(session, user_id)
            if existing:
                results.append({"user_id": user_id, "success": False, "error": "已有主 Key"})
                continue

        try:
            key_data = await create_key(
                session,
                name=name,
                key_type=key_type,
                owner_type="user",
                owner_id=user_id,
                created_by=created_by,
                description=description,
                models=models,
                mcps=mcps,
                skills=skills,
                agents=agents,
                budget_limit=budget_limit,
                budget_hard_limit=budget_hard_limit,
                budget_duration=budget_duration,
                budget_scope=budget_scope,
                budget_models_total=budget_models_total,
                budget_mcps_total=budget_mcps_total,
                budget_models_per=budget_models_per,
                budget_mcps_per=budget_mcps_per,
                model_budgets=model_budgets,
                mcp_budgets=mcp_budgets,
                scenario_id=scenario_id,
                rate_limits=rate_limits,
            )
            results.append({"user_id": user_id, "success": True, "key": key_data})
        except (ConflictError, NotFoundError) as e:
            results.append({"user_id": user_id, "success": False, "error": str(e)})

    return results


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
    """Auto-create a personal main key for a new user (enabled, with public resources)."""
    existing = await ai_key_repo.find_personal_main(session, user_id)
    if existing:
        return existing

    public_resources = await get_public_resources(session)

    key_alias = f"user:{username}/main"
    ai_key = AiKey(
        name="主 Key",
        description="个人主 Key",
        key_type=KEY_TYPE_PERSONAL_MAIN,
        owner_type="user",
        owner_id=user_id,
        tags=[],
        models=public_resources["models"],
        skills=public_resources["skills"],
        mcps=public_resources["mcps"],
        agents=public_resources["agents"],
        is_active=True,
        created_by=user_id,
    )
    ai_key = await ai_key_repo.create(session, ai_key)

    # Get user's litellm_user_id
    user = await user_repo.find_user_by_id(session, user_id)
    litellm_user_id = user.litellm_user_id if user else None

    litellm_models, _ = await _expand_models_with_anthropic(
        session, public_resources["models"], None
    )

    result = await litellm_client.create_key(
        key_alias=key_alias,
        user_id=litellm_user_id,
        models=litellm_models,
        metadata={"aihelms_key_id": ai_key.id, "key_type": KEY_TYPE_PERSONAL_MAIN},
    )
    ai_key.litellm_key_id = result.get("key")
    ai_key.litellm_key_alias = key_alias

    return ai_key


# --- Public resource sync ---


async def get_public_resources(session: AsyncSession) -> dict[str, list]:
    """获取所有已发布且不需要审批的资源 ID。"""
    from models.db import Model, Skill, McpServer, Agent
    from sqlalchemy import select

    models_result = await session.execute(
        select(Model.model_id).where(
            Model.is_published == True, Model.requires_approval == False, Model.is_active == True
        )
    )
    skills_result = await session.execute(
        select(Skill.id).where(
            Skill.is_published == True, Skill.requires_approval == False
        )
    )
    mcps_result = await session.execute(
        select(McpServer.id).where(
            McpServer.is_published == True, McpServer.requires_approval == False
        )
    )
    agents_result = await session.execute(
        select(Agent.id).where(
            Agent.is_published == True, Agent.requires_approval == False, Agent.is_active == True
        )
    )
    return {
        "models": [r[0] for r in models_result.all()],
        "skills": [r[0] for r in skills_result.all()],
        "mcps": [r[0] for r in mcps_result.all()],
        "agents": [r[0] for r in agents_result.all()],
    }


async def sync_public_resource_to_all_keys(
    session: AsyncSession,
    resource_type: str,
    resource_id: str | int,
) -> int:
    """将一个公开资源同步到所有主 Key。返回更新的 Key 数量。"""
    all_main_keys = await ai_key_repo.find_all_main_keys(session)
    updated = 0
    for key in all_main_keys:
        field = getattr(key, resource_type, None)
        if field is None:
            continue
        if resource_id not in field:
            field.append(resource_id)
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(key, resource_type)
            updated += 1
            if resource_type == "models":
                await _sync_key_to_litellm(
                    key, models_changed=True, mcps_changed=False,
                    budget_changed=False, model_budgets_changed=False,
                    session=session,
                )
    if updated:
        await session.flush()
    return updated


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
        main_key = next((k for k in dept_keys if k.key_type == KEY_TYPE_DEPT_MAIN), None)
        scene_keys = [k for k in dept_keys if k.key_type == KEY_TYPE_DEPT_SCENE]
        items.append({
            "department": {"id": dept.id, "name": dept.name},
            "main_key": _serialize_key(main_key) if main_key else None,
            "scene_keys": [_serialize_key(k) for k in scene_keys],
            "keys": [_serialize_key(k) for k in dept_keys],
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def _list_identity_projects(
    session: AsyncSession, page: int, page_size: int, keyword: str | None
) -> dict:
    projects, total = await project_repo.find_paginated(session, page, page_size, keyword)
    items = []
    for proj in projects:
        proj_keys = await ai_key_repo.find_by_owner(session, "project", proj.id)
        main_key = next((k for k in proj_keys if k.key_type == KEY_TYPE_PROJECT_MAIN), None)
        scene_keys = [k for k in proj_keys if k.key_type == KEY_TYPE_PROJECT_SCENE]
        items.append({
            "project": {"id": proj.id, "name": proj.name},
            "main_key": _serialize_key(main_key) if main_key else None,
            "scene_keys": [_serialize_key(k) for k in scene_keys],
            "keys": [_serialize_key(k) for k in proj_keys],
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
    elif key_type == KEY_TYPE_DEPT_MAIN:
        return f"dept:{owner_id}/main"
    elif key_type == KEY_TYPE_DEPT_SCENE:
        return f"dept:{owner_id}/{name}"
    elif key_type == KEY_TYPE_PROJECT_MAIN:
        return f"proj:{owner_id}/main"
    elif key_type == KEY_TYPE_PROJECT_SCENE:
        return f"proj:{owner_id}/{name}"
    return f"{owner_type}:{owner_id}/{name}"


async def _save_rate_limits(session: AsyncSession, key_id: int, rate_limits: list[dict]) -> None:
    """Save rate limits (TPM/RPM per model) for a key."""
    incoming_model_ids = set()
    for item in rate_limits:
        mid = item.get("model_id")
        if not mid:
            continue
        incoming_model_ids.add(mid)
        await ai_key_model_limit_repo.upsert(
            session,
            ai_key_id=key_id,
            model_id=mid,
            tpm=item.get("tpm"),
            rpm=item.get("rpm"),
            max_tokens=item.get("max_tokens"),
            max_calls=item.get("max_calls"),
        )

    # Remove limits for models not in the incoming list
    existing = await ai_key_model_limit_repo.find_by_key_id(session, key_id)
    for limit in existing:
        if limit.model_id not in incoming_model_ids:
            await ai_key_model_limit_repo.delete_by_key_and_model(session, key_id, limit.model_id)

    await session.commit()


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
        "mcps": key.mcps or [],
        "skills": key.skills or [],
        "agents": key.agents or [],
        "budget_limit": str(key.budget_limit) if key.budget_limit is not None else None,
        "budget_used": str(key.budget_used) if key.budget_used else "0",
        "budget_hard_limit": key.budget_hard_limit,
        "budget_duration": key.budget_duration,
        "budget_scope": key.budget_scope,
        "budget_models_total": str(key.budget_models_total) if key.budget_models_total is not None else None,
        "budget_mcps_total": str(key.budget_mcps_total) if key.budget_mcps_total is not None else None,
        "budget_models_per": key.budget_models_per,
        "budget_mcps_per": key.budget_mcps_per,
        "model_budgets": key.model_budgets or {},
        "mcp_budgets": key.mcp_budgets or {},
        "scenario_id": key.scenario_id,
        "is_active": key.is_active,
        "created_by": key.created_by,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "updated_at": key.updated_at.isoformat() if key.updated_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
    }
