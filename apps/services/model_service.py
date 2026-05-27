import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from exceptions import NotFoundError, ConflictError
from models.db import Model, ModelDeployment, ModelAccessGroup, RouterSettings, ModelDepartmentVisibility, ModelUserVisibility, ProviderPrefixMap
from repositories import model_repo, credential_repo, ai_key_repo
from services import litellm_client

logger = logging.getLogger(__name__)


# --- Models ---


async def list_models(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
) -> dict:
    total = await model_repo.count_all(session, category, is_active=True)
    items = await model_repo.find_all(session, page, page_size, category, is_active=True)
    return {
        "items": [_serialize_model(m) for m in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_model_by_id(session: AsyncSession, model_id: int) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)
    data = _serialize_model(model)
    deployments = await model_repo.find_deployments_by_model(session, model_id)
    data["deployments"] = [_serialize_deployment(d) for d in deployments]
    return data


async def get_all_active_models(session: AsyncSession) -> list[dict]:
    models = await model_repo.find_all_active(session, published_only=True)
    model_ids = [m.model_id for m in models]
    anthropic_set = await model_repo.find_model_ids_with_anthropic_deployments(session, model_ids)
    return [
        {
            "id": m.id,
            "name": m.name,
            "model_id": m.model_id,
            "category": m.category,
            "capabilities": m.capabilities,
            "description": m.description,
            "is_active": m.is_active,
            "is_published": m.is_published,
            "requires_approval": m.requires_approval,
            "has_anthropic_deployment": m.model_id in anthropic_set,
        }
        for m in models
    ]


async def get_model_ids_by_credential_ids(
    session: AsyncSession, credential_ids: list[int]
) -> list[str]:
    """Return model_id strings for models deployed with given credentials."""
    if not credential_ids:
        return []
    return await model_repo.find_model_ids_by_credential_ids(session, credential_ids)


async def create_model(
    session: AsyncSession,
    name: str,
    model_id: str = "",
    category: str = "chat",
    capabilities: list[str] | None = None,
    description: str = "",
) -> dict:
    effective_model_id = model_id.strip() or None
    if effective_model_id:
        existing = await model_repo.find_by_model_id(session, effective_model_id)
        if existing:
            raise ConflictError(f"模型 ID '{effective_model_id}' 已存在")

    model = Model(
        name=name,
        model_id=effective_model_id,
        category=category,
        capabilities=capabilities or [],
        description=description,
    )
    model = await model_repo.create(session, model)
    await session.commit()
    await session.refresh(model)
    return _serialize_model(model)


async def update_model(
    session: AsyncSession,
    model_id: int,
    name: str | None = None,
    model_id_str: str | None = None,
    category: str | None = None,
    capabilities: list[str] | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    if model_id_str is not None and model_id_str != model.model_id:
        if model_id_str:
            existing = await model_repo.find_by_model_id(session, model_id_str)
            if existing and existing.id != model.id:
                raise ConflictError(f"模型 ID '{model_id_str}' 已被其他模型使用")
        model.model_id = model_id_str
    if name is not None:
        model.name = name
    if category is not None:
        model.category = category
    if capabilities is not None:
        model.capabilities = capabilities
    if description is not None:
        model.description = description
    if is_active is not None:
        model.is_active = is_active

    await session.commit()
    await session.refresh(model)
    return _serialize_model(model)


async def delete_model(session: AsyncSession, model_id: int) -> None:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    deployments = await model_repo.find_deployments_by_model(session, model_id)
    for d in deployments:
        if d.litellm_model_id:
            litellm_model_name = _get_litellm_model_name(model, d.credential)
            await litellm_client.update_model(
                litellm_model_id=d.litellm_model_id,
                model_name=litellm_model_name,
                litellm_params=_convert_cost_for_litellm(d.litellm_params),
                model_info={**(d.model_info or {}), "active": False},
            )
        d.is_active = False

    model.is_active = False
    await session.commit()


# --- Deployment helpers ---


def _merge_external_cost_to_model_info(model_info: dict, litellm_params: dict) -> dict:
    """把 litellm_params 中的外部定价复制到 model_info，供平台成本计算使用。"""
    result = dict(model_info)
    cost_fields = {
        "input_cost_per_token": "input_cost",
        "output_cost_per_token": "output_cost",
        "cache_read_input_token_cost": "cache_read_cost",
        "cache_creation_input_token_cost": "cache_creation_cost",
    }
    for param_key, info_key in cost_fields.items():
        if param_key in litellm_params:
            result[info_key] = litellm_params[param_key]
        elif info_key in result and param_key not in litellm_params:
            del result[info_key]
    return result


def _convert_cost_for_litellm(litellm_params: dict) -> dict:
    """将 litellm_params 中的定价从 ¥/百万token 转换为 USD/token（LiteLLM 原生单位）。"""
    result = dict(litellm_params)
    rate = settings.usd_to_cny_rate
    million = 1_000_000
    cost_keys = [
        "input_cost_per_token",
        "output_cost_per_token",
        "cache_read_input_token_cost",
        "cache_creation_input_token_cost",
    ]
    for key in cost_keys:
        if key in result and result[key]:
            result[key] = float(result[key]) / rate / million
    return result


# --- Deployments ---


async def create_deployment(
    session: AsyncSession,
    model_id: int,
    litellm_params: dict,
    credential_id: int | None = None,
    deploy_name: str = "",
    billing_type: str = "token",
    cost_per_call: float | None = None,
    monthly_call_quota: int | None = None,
    model_info: dict | None = None,
    model_id_str: str | None = None,
) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    # 设置或更新模型的 model_id
    if model_id_str:
        if model.model_id != model_id_str:
            existing = await model_repo.find_by_model_id(session, model_id_str)
            if existing and existing.id != model.id:
                raise ConflictError(f"模型 ID '{model_id_str}' 已被其他模型使用")
            model.model_id = model_id_str

    if not model.model_id:
        raise ConflictError("请先设置模型 ID（在部署表单中填写）")

    credential = None
    if credential_id:
        credential = await credential_repo.find_by_id(session, credential_id)
        if not credential:
            raise NotFoundError("credential", credential_id)

    deployment = ModelDeployment(
        model_id=model_id,
        credential_id=credential_id,
        litellm_params=litellm_params,
        model_info=_merge_external_cost_to_model_info(model_info or {}, litellm_params),
        deploy_name=deploy_name,
        billing_type=billing_type,
        cost_per_call=cost_per_call,
        monthly_call_quota=monthly_call_quota,
    )
    deployment = await model_repo.create_deployment(session, deployment)

    # Sync to LiteLLM
    await _sync_deployment_to_litellm(deployment, model, credential, session)

    await session.commit()
    await session.refresh(deployment)
    return _serialize_deployment(deployment)


async def update_deployment(
    session: AsyncSession,
    deployment_id: int,
    litellm_params: dict | None = None,
    credential_id: int | None = None,
    deploy_name: str | None = None,
    billing_type: str | None = None,
    cost_per_call: float | None = None,
    monthly_call_quota: int | None = None,
    model_info: dict | None = None,
    is_active: bool | None = None,
    model_id_str: str | None = None,
) -> dict:
    deployment = await model_repo.find_deployment_by_id(session, deployment_id)
    if not deployment:
        raise NotFoundError("deployment", deployment_id)

    # 更新模型的 model_id
    if model_id_str:
        model = await model_repo.find_by_id(session, deployment.model_id)
        if model and model.model_id != model_id_str:
            existing = await model_repo.find_by_model_id(session, model_id_str)
            if existing and existing.id != model.id:
                raise ConflictError(f"模型 ID '{model_id_str}' 已被其他模型使用")
            model.model_id = model_id_str

    if litellm_params is not None:
        deployment.litellm_params = litellm_params
    if credential_id is not None:
        deployment.credential_id = credential_id
    if deploy_name is not None:
        deployment.deploy_name = deploy_name
    if billing_type is not None:
        deployment.billing_type = billing_type
    if cost_per_call is not None:
        deployment.cost_per_call = cost_per_call
    if monthly_call_quota is not None:
        deployment.monthly_call_quota = monthly_call_quota
    if model_info is not None:
        deployment.model_info = _merge_external_cost_to_model_info(
            model_info, deployment.litellm_params
        )
    elif litellm_params is not None:
        deployment.model_info = _merge_external_cost_to_model_info(
            deployment.model_info or {}, litellm_params
        )
    if is_active is not None:
        deployment.is_active = is_active

    # Re-sync to LiteLLM
    model = await model_repo.find_by_id(session, deployment.model_id)
    credential = None
    if deployment.credential_id:
        credential = await credential_repo.find_by_id(session, deployment.credential_id)

    if model and deployment.litellm_model_id:
        sync_params = dict(deployment.litellm_params)
        if credential and "litellm_credential_name" not in sync_params and "api_key" not in sync_params:
            sync_params["litellm_credential_name"] = credential.credential_name
        if credential and "api_base" not in sync_params:
            cred_api_base = (credential.credential_values or {}).get("api_base") or (credential.credential_info or {}).get("api_base")
            if cred_api_base:
                sync_params["api_base"] = cred_api_base
        sync_params = _convert_cost_for_litellm(sync_params)
        sync_model_info = dict(deployment.model_info or {})
        sync_model_info["active"] = deployment.is_active
        litellm_model_name = _get_litellm_model_name(model, credential)
        await litellm_client.update_model(
            litellm_model_id=deployment.litellm_model_id,
            model_name=litellm_model_name,
            litellm_params=sync_params,
            model_info=sync_model_info,
        )
    elif model and not deployment.litellm_model_id and deployment.is_active:
        await _sync_deployment_to_litellm(deployment, model, credential, session)

    await session.commit()
    await session.refresh(deployment)
    return _serialize_deployment(deployment)


async def delete_deployment(session: AsyncSession, deployment_id: int) -> None:
    deployment = await model_repo.find_deployment_by_id(session, deployment_id)
    if not deployment:
        raise NotFoundError("deployment", deployment_id)

    if deployment.litellm_model_id:
        model = await model_repo.find_by_id(session, deployment.model_id)
        credential = None
        if deployment.credential_id:
            credential = await credential_repo.find_by_id(session, deployment.credential_id)
        litellm_model_name = _get_litellm_model_name(model, credential) if model else ""
        try:
            await litellm_client.update_model(
                litellm_model_id=deployment.litellm_model_id,
                model_name=litellm_model_name,
                litellm_params=_convert_cost_for_litellm(deployment.litellm_params),
                model_info={**(deployment.model_info or {}), "active": False},
            )
        except litellm_client.LiteLLMError as e:
            logger.error("litellm disable model failed for deployment %s: %s", deployment_id, e)
            raise ConflictError("LiteLLM 侧禁用失败，请稍后重试")

    await session.delete(deployment)
    await session.commit()


# --- Access Groups ---


async def list_access_groups(session: AsyncSession) -> list[dict]:
    groups = await model_repo.find_all_access_groups(session)
    return [_serialize_access_group(g) for g in groups]


async def create_access_group(
    session: AsyncSession,
    group_name: str,
    description: str = "",
    model_ids: list[str] | None = None,
) -> dict:
    existing = await model_repo.find_access_group_by_name(session, group_name)
    if existing:
        raise ConflictError(f"访问组 '{group_name}' 已存在")

    group = ModelAccessGroup(
        group_name=group_name,
        description=description,
        model_ids=model_ids or [],
    )
    group = await model_repo.create_access_group(session, group)
    await session.commit()
    await session.refresh(group)
    return _serialize_access_group(group)


async def update_access_group(
    session: AsyncSession,
    group_id: int,
    group_name: str | None = None,
    description: str | None = None,
    model_ids: list[str] | None = None,
    is_active: bool | None = None,
) -> dict:
    group = await model_repo.find_access_group_by_id(session, group_id)
    if not group:
        raise NotFoundError("access_group", group_id)

    if group_name is not None:
        group.group_name = group_name
    if description is not None:
        group.description = description
    if model_ids is not None:
        group.model_ids = model_ids
    if is_active is not None:
        group.is_active = is_active

    await session.commit()
    await session.refresh(group)
    return _serialize_access_group(group)


async def delete_access_group(session: AsyncSession, group_id: int) -> None:
    group = await model_repo.find_access_group_by_id(session, group_id)
    if not group:
        raise NotFoundError("access_group", group_id)
    await session.delete(group)
    await session.commit()


# --- Router Settings ---


async def get_router_settings(session: AsyncSession) -> dict:
    settings = await model_repo.get_router_settings(session)
    if not settings:
        return {
            "routing_strategy": "simple-shuffle",
            "fallbacks": [],
            "allowed_fails": 3,
            "cooldown_time": 60,
            "num_retries": 2,
            "timeout": 30,
            "config": {},
        }
    return _serialize_router_settings(settings)


async def update_router_settings(
    session: AsyncSession,
    routing_strategy: str | None = None,
    fallbacks: list | None = None,
    allowed_fails: int | None = None,
    cooldown_time: int | None = None,
    num_retries: int | None = None,
    timeout: int | None = None,
    config: dict | None = None,
) -> dict:
    settings = await model_repo.get_router_settings(session)
    if not settings:
        settings = RouterSettings()

    if routing_strategy is not None:
        settings.routing_strategy = routing_strategy
    if fallbacks is not None:
        settings.fallbacks = fallbacks
    if allowed_fails is not None:
        settings.allowed_fails = allowed_fails
    if cooldown_time is not None:
        settings.cooldown_time = cooldown_time
    if num_retries is not None:
        settings.num_retries = num_retries
    if timeout is not None:
        settings.timeout = timeout
    if config is not None:
        settings.config = config

    settings = await model_repo.upsert_router_settings(session, settings)

    # Sync to LiteLLM
    litellm_settings = {
        "routing_strategy": settings.routing_strategy,
        "allowed_fails": settings.allowed_fails,
        "cooldown_time": settings.cooldown_time,
        "num_retries": settings.num_retries,
        "timeout": settings.timeout,
    }
    if settings.fallbacks:
        litellm_settings["fallbacks"] = settings.fallbacks
    if settings.config:
        litellm_settings.update(settings.config)
    await litellm_client.update_router_settings(litellm_settings)

    await session.commit()
    await session.refresh(settings)
    return _serialize_router_settings(settings)


# --- Model Publish / Visibility ---


async def get_model_visibility(session: AsyncSession, model_id: int) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    dept_records = await model_repo.find_visibility_by_model(session, model_id)
    user_records = await model_repo.find_user_visibility_by_model(session, model_id)

    return {
        "is_published": model.is_published,
        "visibility_type": model.visibility_type,
        "requires_approval": model.requires_approval,
        "department_ids": [r.department_id for r in dept_records],
        "departments": [
            {"id": r.department_id, "name": r.department.name if r.department else ""}
            for r in dept_records
        ],
        "user_ids": [r.user_id for r in user_records],
        "user_count": len(user_records),
    }


async def update_model_publish(
    session: AsyncSession,
    model_id: int,
    is_published: bool | None = None,
    visibility_type: str | None = None,
    department_ids: list[int] | None = None,
    requires_approval: bool | None = None,
) -> dict:
    from repositories import department_repo

    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    if is_published is not None:
        model.is_published = is_published
    if visibility_type is not None:
        model.visibility_type = visibility_type
    if requires_approval is not None:
        model.requires_approval = requires_approval

    if department_ids is not None:
        await model_repo.set_visibility_departments(session, model_id, department_ids)
        # Resolve department members to user-level visibility
        user_ids: set[int] = set()
        for dept_id in department_ids:
            members = await department_repo.find_members(session, dept_id)
            for user, _ in members:
                user_ids.add(user.id)
        await model_repo.set_visibility_users(session, model_id, list(user_ids))

    # 发布且不需要审批时，自动同步到所有主 Key
    if model.is_published and not model.requires_approval:
        from services import ai_key_service
        await ai_key_service.sync_public_resource_to_all_keys(session, "models", model.model_id)

    await session.commit()
    await session.refresh(model)
    return await get_model_visibility(session, model_id)


# --- Private helpers ---


def _get_credential_format(credential) -> str:
    """Return the credential format ('openai' or 'anthropic')."""
    if not credential:
        return "openai"
    return (credential.credential_info or {}).get("format") or "openai"


ANTHROPIC_MODEL_SUFFIX = "(Anthropic)"


def _get_litellm_model_name(model: Model, credential=None) -> str:
    """Determine the LiteLLM model_name based on credential format.

    Anthropic-format credentials get an '(Anthropic)' suffix to form an independent model group.
    """
    cred_format = _get_credential_format(credential)
    if cred_format == "anthropic":
        return f"{model.model_id}{ANTHROPIC_MODEL_SUFFIX}"
    return model.model_id


async def _sync_deployment_to_litellm(
    deployment: ModelDeployment,
    model: Model,
    credential=None,
    session=None,
) -> None:
    litellm_params = dict(deployment.litellm_params)

    # Inject credential reference and api_base if not already specified
    if credential and "litellm_credential_name" not in litellm_params and "api_key" not in litellm_params:
        # Ensure credential exists in LiteLLM before referencing it
        if not credential.litellm_synced:
            try:
                await litellm_client.create_credential(
                    credential_name=credential.credential_name,
                    credential_values=credential.credential_values,
                    credential_info=credential.credential_info or {},
                )
                credential.litellm_synced = True
            except litellm_client.LiteLLMError as e:
                logger.error("credential sync failed before deployment: %s", e)
                raise ConflictError("凭证同步失败，请检查凭证配置（API Key、API Base）是否正确")
        litellm_params["litellm_credential_name"] = credential.credential_name

        # Inject api_base from credential if not already in litellm_params
        if "api_base" not in litellm_params:
            cred_api_base = (credential.credential_values or {}).get("api_base") or (credential.credential_info or {}).get("api_base")
            if cred_api_base:
                litellm_params["api_base"] = cred_api_base

    # Auto-resolve prefix and normalize api_base via provider_prefix_map
    if session and credential:
        prefix_info = await _resolve_prefix(session, credential, model.category)
        if prefix_info:
            raw_model = litellm_params.get("model", "")
            model_name_raw = raw_model.split("/")[-1] if "/" in raw_model else raw_model
            if not model_name_raw:
                model_name_raw = model.model_id
            litellm_params["model"] = f"{prefix_info.prefix}/{model_name_raw}"
            if prefix_info.needs_v1 and "api_base" in litellm_params:
                litellm_params["api_base"] = _ensure_v1_suffix(litellm_params["api_base"])

    sync_litellm_params = _convert_cost_for_litellm(litellm_params)
    litellm_model_name = _get_litellm_model_name(model, credential)
    result = await litellm_client.add_model(
        model_name=litellm_model_name,
        litellm_params=sync_litellm_params,
        model_info=deployment.model_info or {},
    )
    litellm_id = result.get("model_info", {}).get("id")
    if litellm_id:
        deployment.litellm_model_id = litellm_id
    # 写回处理后的 litellm_params（含前缀、api_base、credential_name）
    deployment.litellm_params = litellm_params


def _serialize_model(model: Model) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "model_id": model.model_id,
        "category": model.category,
        "capabilities": model.capabilities,
        "description": model.description,
        "is_active": model.is_active,
        "is_published": model.is_published,
        "visibility_type": model.visibility_type,
        "deployment_count": len(model.deployments) if model.deployments else 0,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }


def _serialize_deployment(deployment: ModelDeployment) -> dict:
    credential_name = None
    if deployment.credential:
        credential_name = deployment.credential.credential_name
    return {
        "id": deployment.id,
        "model_id": deployment.model_id,
        "credential_id": deployment.credential_id,
        "credential_name": credential_name,
        "litellm_model_id": deployment.litellm_model_id,
        "litellm_params": deployment.litellm_params,
        "model_info": deployment.model_info,
        "deploy_name": deployment.deploy_name,
        "billing_type": deployment.billing_type,
        "cost_per_call": str(deployment.cost_per_call) if deployment.cost_per_call else None,
        "monthly_call_quota": deployment.monthly_call_quota,
        "monthly_call_used": deployment.monthly_call_used,
        "is_active": deployment.is_active,
        "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
    }


def _serialize_access_group(group: ModelAccessGroup) -> dict:
    return {
        "id": group.id,
        "group_name": group.group_name,
        "description": group.description,
        "model_ids": group.model_ids,
        "is_active": group.is_active,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


def _serialize_router_settings(settings: RouterSettings) -> dict:
    return {
        "id": settings.id,
        "routing_strategy": settings.routing_strategy,
        "fallbacks": settings.fallbacks,
        "allowed_fails": settings.allowed_fails,
        "cooldown_time": settings.cooldown_time,
        "num_retries": settings.num_retries,
        "timeout": settings.timeout,
        "config": settings.config,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


async def _resolve_prefix(
    session: AsyncSession,
    credential,
    category: str,
) -> ProviderPrefixMap | None:
    """Look up the correct LiteLLM prefix from provider_prefix_map table."""
    if not credential or not credential.provider:
        return None
    provider_type = credential.provider.provider_type
    cred_format = (credential.credential_info or {}).get("format") or "openai"
    result = await session.execute(
        select(ProviderPrefixMap).where(
            ProviderPrefixMap.provider_type == provider_type,
            ProviderPrefixMap.format == cred_format,
            ProviderPrefixMap.category == category,
        )
    )
    return result.scalar_one_or_none()


def _ensure_v1_suffix(api_base: str) -> str:
    """Ensure api_base ends with /v1 for providers that need it.

    Skip if the URL already contains /v1 anywhere in the path
    (e.g. .../v1/messages for anthropic endpoints).
    """
    api_base = api_base.rstrip("/")
    if "/v1" in api_base:
        return api_base
    return f"{api_base}/v1"


# --- Resync ---


async def resync_anthropic_deployments(session: AsyncSession) -> dict:
    """重新同步所有 anthropic 格式部署到 LiteLLM，使用 (Anthropic) model_name。

    同时更新所有相关 Key 的 LiteLLM models 列表。
    """
    from services import ai_key_service

    all_deployments = await model_repo.find_all_active_deployments(session)
    synced = 0
    errors = 0

    for deployment in all_deployments:
        credential = deployment.credential
        if not credential:
            continue
        cred_format = _get_credential_format(credential)
        if cred_format != "anthropic":
            continue

        model = deployment.model
        if not model or not deployment.litellm_model_id:
            continue

        litellm_model_name = _get_litellm_model_name(model, credential)
        try:
            sync_params = dict(deployment.litellm_params)
            sync_params = _convert_cost_for_litellm(sync_params)
            sync_model_info = dict(deployment.model_info or {})
            sync_model_info["active"] = deployment.is_active
            await litellm_client.update_model(
                litellm_model_id=deployment.litellm_model_id,
                model_name=litellm_model_name,
                litellm_params=sync_params,
                model_info=sync_model_info,
            )
            synced += 1
        except litellm_client.LiteLLMError:
            logger.warning("resync failed for deployment %s", deployment.id)
            errors += 1

    # Update all main keys to include (Anthropic) variants
    all_main_keys = await ai_key_repo.find_all_main_keys(session)
    keys_updated = 0
    for key in all_main_keys:
        if not key.litellm_key_id or not key.models:
            continue
        litellm_models, litellm_budgets = await ai_key_service._expand_models_with_anthropic(
            session, key.models, key.model_budgets or None
        )
        try:
            await litellm_client.update_key(
                key_id=key.litellm_key_id,
                models=litellm_models,
                model_max_budget=litellm_budgets,
            )
            keys_updated += 1
        except litellm_client.LiteLLMError:
            logger.warning("resync key failed for ai_key %s", key.id)

    await session.commit()
    return {
        "deployments_synced": synced,
        "deployment_errors": errors,
        "keys_updated": keys_updated,
    }
