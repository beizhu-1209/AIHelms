import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
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
SCENE_KEY_TYPES = {
    KEY_TYPE_PERSONAL_SCENE,
    KEY_TYPE_DEPT_SCENE,
    KEY_TYPE_PROJECT_SCENE,
}
VALID_OWNER_TYPES = {"user", "department", "project"}
RATE_LIMIT_MODE_NONE = "none"
RATE_LIMIT_MODE_TOTAL = "total"
RATE_LIMIT_MODE_PER_MODEL = "per_model"
VALID_RATE_LIMIT_MODES = {
    RATE_LIMIT_MODE_NONE,
    RATE_LIMIT_MODE_TOTAL,
    RATE_LIMIT_MODE_PER_MODEL,
}


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
    rate_limit_mode: str = RATE_LIMIT_MODE_NONE,
    tpm_limit: int | None = None,
    rpm_limit: int | None = None,
    max_parallel_requests: int | None = None,
    rate_limits: list[dict] | None = None,
) -> dict:
    if key_type not in VALID_KEY_TYPES:
        raise ConflictError(f"无效的 key 类型: {key_type}")
    if key_type not in SCENE_KEY_TYPES:
        raise ValidationError("只能手动创建场景 Key，主 Key 由平台自动创建")
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
        rate_limit_mode=rate_limit_mode,
        tpm_limit=tpm_limit,
        rpm_limit=rpm_limit,
        max_parallel_requests=max_parallel_requests,
        scenario_id=scenario_id,
        is_active=False,
        created_by=created_by,
    )
    ai_key = await ai_key_repo.create(session, ai_key)
    _assign_key_rate_limits(
        ai_key,
        rate_limit_mode,
        tpm_limit,
        rpm_limit,
        max_parallel_requests,
    )
    await _save_rate_limits(session, ai_key.id, rate_limits or [])

    # Sync to LiteLLM
    litellm_duration = budget_duration if budget_duration and budget_limit else duration
    litellm_models, _ = await _expand_models_with_anthropic(
        session, models or [], None
    )
    mcp_server_names = await _resolve_mcp_server_names(session, mcps or [])
    result = await litellm_client.create_key(
        key_alias=key_alias,
        user_id=litellm_user_id,
        team_id=team_id,
        models=litellm_models,
        metadata=await _build_key_metadata(session, ai_key),
        duration=litellm_duration,
        allowed_mcp_servers=mcp_server_names if mcp_server_names else None,
        tpm_limit=ai_key.tpm_limit,
        rpm_limit=ai_key.rpm_limit,
        max_parallel_requests=ai_key.max_parallel_requests,
    )
    ai_key.litellm_key_id = result.get("key")
    ai_key.litellm_key_alias = key_alias

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
    update_rate_limit: bool = True,
    rate_limit_mode: str | None = None,
    tpm_limit: int | None = None,
    rpm_limit: int | None = None,
    max_parallel_requests: int | None = None,
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

    rate_limit_changed = update_rate_limit and _has_rate_limit_update(
        rate_limit_mode,
        tpm_limit,
        rpm_limit,
        max_parallel_requests,
        rate_limits,
    )
    if rate_limit_changed:
        _assign_key_rate_limits(
            key,
            rate_limit_mode or key.rate_limit_mode or RATE_LIMIT_MODE_NONE,
            tpm_limit,
            rpm_limit,
            max_parallel_requests,
        )
        await _save_rate_limits(session, key_id, rate_limits or [])

    await _sync_key_to_litellm(
        key,
        models_changed=models is not None,
        mcps_changed=mcps is not None,
        budget_changed=(budget_limit is not None or budget_hard_limit is not None or budget_duration is not None),
        model_budgets_changed=model_budgets is not None,
        rate_limits_changed=rate_limit_changed,
        session=session,
    )

    await session.commit()
    await session.refresh(key)

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
    await _sync_key_to_litellm(
        key,
        models is not None,
        mcps is not None,
        False,
        False,
        rate_limits_changed=key.rate_limit_mode == RATE_LIMIT_MODE_PER_MODEL,
        session=session,
    )


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
    rate_limits_changed: bool = False,
    session: AsyncSession | None = None,
) -> None:
    if not key.litellm_key_id:
        return
    if not (models_changed or mcps_changed or budget_changed or rate_limits_changed):
        return

    # Expand models with (Anthropic) variants
    litellm_models = key.models
    if session and models_changed:
        litellm_models, _ = await _expand_models_with_anthropic(
            session, key.models, None
        )

    # Resolve MCP server names from IDs
    mcp_server_names: list[str] | None = None
    if mcps_changed and session:
        mcp_server_names = await _resolve_mcp_server_names(session, key.mcps or [])

    if models_changed or mcps_changed or rate_limits_changed:
        metadata = None
        if session and rate_limits_changed:
            metadata = await _build_key_metadata(session, key)
        await litellm_client.update_key(
            key_id=key.litellm_key_id,
            models=litellm_models if models_changed else None,
            metadata=metadata,
            allowed_mcp_servers=mcp_server_names,
            tpm_limit=key.tpm_limit,
            rpm_limit=key.rpm_limit,
            max_parallel_requests=key.max_parallel_requests,
            sync_rate_limits=rate_limits_changed,
        )

    if budget_changed:
        # Budgets are tracked by AIHelms. LiteLLM max_budget is kept clear
        # except when explicitly disabling a key.
        await litellm_client.update_key_budget(key.litellm_key_id, None)


async def toggle_key(session: AsyncSession, key_id: int) -> dict:
    key = await ai_key_repo.find_by_id(session, key_id)
    if not key:
        raise NotFoundError("ai_key", key_id)

    key.is_active = not key.is_active

    # Sync budget: active + hard_limit → set budget; inactive → set budget to 0 to block
    if key.litellm_key_id:
        if key.is_active:
            max_budget = None
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
            max_budget = None
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
    rate_limit_mode: str = RATE_LIMIT_MODE_NONE,
    tpm_limit: int | None = None,
    rpm_limit: int | None = None,
    max_parallel_requests: int | None = None,
    rate_limits: list[dict] | None = None,
) -> list[dict]:
    if key_type != KEY_TYPE_PERSONAL_SCENE:
        raise ValidationError("批量创建仅支持个人场景 Key")

    results = []
    for user_id in user_ids:
        user = await user_repo.find_user_by_id(session, user_id)
        if not user:
            results.append({"user_id": user_id, "success": False, "error": "用户不存在"})
            continue

        name = name_template.replace("{username}", user.username or "")
        name = name.replace("{display_name}", user.display_name or user.username or "")

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
                rate_limit_mode=rate_limit_mode,
                tpm_limit=tpm_limit,
                rpm_limit=rpm_limit,
                max_parallel_requests=max_parallel_requests,
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
                    rate_limits_changed=key.rate_limit_mode == RATE_LIMIT_MODE_PER_MODEL,
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
            tpm=_clean_limit_value(item.get("tpm")),
            rpm=_clean_limit_value(item.get("rpm")),
            max_tokens=None,
            max_calls=None,
        )

    # Delete limits for models not in the incoming list
    existing_limits = await ai_key_model_limit_repo.find_by_key_id(session, key_id)
    for existing in existing_limits:
        if existing.model_id not in incoming_model_ids:
            await ai_key_model_limit_repo.delete_by_key_and_model(
                session, key_id, existing.model_id
            )

    await _sync_key_to_litellm(
        key,
        models_changed=False,
        mcps_changed=False,
        budget_changed=False,
        model_budgets_changed=False,
        rate_limits_changed=key.rate_limit_mode == RATE_LIMIT_MODE_PER_MODEL,
        session=session,
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
    await _sync_key_to_litellm(
        key,
        models_changed=False,
        mcps_changed=False,
        budget_changed=False,
        model_budgets_changed=False,
        rate_limits_changed=key.rate_limit_mode == RATE_LIMIT_MODE_PER_MODEL,
        session=session,
    )
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


def _has_rate_limit_update(
    rate_limit_mode: str | None,
    tpm_limit: int | None,
    rpm_limit: int | None,
    max_parallel_requests: int | None,
    rate_limits: list[dict] | None,
) -> bool:
    return any(
        value is not None
        for value in (
            rate_limit_mode,
            tpm_limit,
            rpm_limit,
            max_parallel_requests,
            rate_limits,
        )
    )


def _assign_key_rate_limits(
    key: AiKey,
    rate_limit_mode: str,
    tpm_limit: int | None,
    rpm_limit: int | None,
    max_parallel_requests: int | None,
) -> None:
    if rate_limit_mode not in VALID_RATE_LIMIT_MODES:
        raise ValidationError(f"无效的限流模式: {rate_limit_mode}")

    key.rate_limit_mode = rate_limit_mode
    if rate_limit_mode == RATE_LIMIT_MODE_TOTAL:
        key.tpm_limit = tpm_limit
        key.rpm_limit = rpm_limit
        key.max_parallel_requests = max_parallel_requests
        return

    key.tpm_limit = None
    key.rpm_limit = None
    key.max_parallel_requests = None


def _clean_limit_value(value: object) -> int | None:
    if value in (None, ""):
        return None
    number = int(value)
    return number if number > 0 else None


def _base_key_metadata(key: AiKey) -> dict:
    return {"aihelms_key_id": key.id, "key_type": key.key_type}


async def _build_key_metadata(session: AsyncSession, key: AiKey) -> dict:
    metadata = _base_key_metadata(key)
    if key.rate_limit_mode != RATE_LIMIT_MODE_PER_MODEL:
        return metadata

    model_tpm_limit, model_rpm_limit = await _build_model_rate_limit_maps(session, key)
    if model_tpm_limit:
        metadata["model_tpm_limit"] = model_tpm_limit
    if model_rpm_limit:
        metadata["model_rpm_limit"] = model_rpm_limit
    return metadata


async def _build_model_rate_limit_maps(
    session: AsyncSession,
    key: AiKey,
) -> tuple[dict[str, int], dict[str, int]]:
    limits = await ai_key_model_limit_repo.find_by_key_id(session, key.id)
    allowed_models = set(key.models or [])
    tpm_limits: dict[str, int] = {}
    rpm_limits: dict[str, int] = {}

    for limit in limits:
        model = await model_repo.find_by_id(session, limit.model_id)
        if not model or model.model_id not in allowed_models:
            continue
        if limit.tpm:
            tpm_limits[model.model_id] = limit.tpm
        if limit.rpm:
            rpm_limits[model.model_id] = limit.rpm

    expanded_tpm = await _expand_rate_limit_map(session, tpm_limits)
    expanded_rpm = await _expand_rate_limit_map(session, rpm_limits)
    return expanded_tpm, expanded_rpm


async def _expand_rate_limit_map(
    session: AsyncSession,
    limits: dict[str, int],
) -> dict[str, int]:
    if not limits:
        return {}
    _, expanded = await _expand_models_with_anthropic(
        session,
        list(limits.keys()),
        limits,
    )
    return expanded or limits


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
            tpm=_clean_limit_value(item.get("tpm")),
            rpm=_clean_limit_value(item.get("rpm")),
            max_tokens=None,
            max_calls=None,
        )

    # Remove limits for models not in the incoming list
    existing = await ai_key_model_limit_repo.find_by_key_id(session, key_id)
    for limit in existing:
        if limit.model_id not in incoming_model_ids:
            await ai_key_model_limit_repo.delete_by_key_and_model(session, key_id, limit.model_id)

    await session.flush()


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
        "rate_limit_mode": key.rate_limit_mode or RATE_LIMIT_MODE_NONE,
        "tpm_limit": key.tpm_limit,
        "rpm_limit": key.rpm_limit,
        "max_parallel_requests": key.max_parallel_requests,
        "scenario_id": key.scenario_id,
        "is_active": key.is_active,
        "created_by": key.created_by,
        "created_at": fmt_local_time(key.created_at),
        "updated_at": fmt_local_time(key.updated_at),
        "expires_at": fmt_local_time(key.expires_at),
        "last_used_at": fmt_local_time(key.last_used_at),
    }
