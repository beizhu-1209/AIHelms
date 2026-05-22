import logging

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError
from models.db import Model, ModelDeployment, ModelAccessGroup, RouterSettings, ModelDepartmentVisibility, ModelUserVisibility
from repositories import model_repo, credential_repo
from services import litellm_client

logger = logging.getLogger(__name__)


# --- Models ---


async def list_models(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
) -> dict:
    total = await model_repo.count_all(session, category)
    items = await model_repo.find_all(session, page, page_size, category)
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
    model_id: str,
    category: str = "chat",
    capabilities: list[str] | None = None,
    description: str = "",
) -> dict:
    existing = await model_repo.find_by_model_id(session, model_id)
    if existing:
        raise ConflictError(f"模型 ID '{model_id}' 已存在")

    model = Model(
        name=name,
        model_id=model_id,
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
    category: str | None = None,
    capabilities: list[str] | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

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
            try:
                await litellm_client.delete_model(d.litellm_model_id)
            except litellm_client.LiteLLMError:
                logger.warning("litellm delete model failed for deployment %s", d.id)

    model.is_active = False
    await session.commit()


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
) -> dict:
    model = await model_repo.find_by_id(session, model_id)
    if not model:
        raise NotFoundError("model", model_id)

    credential = None
    if credential_id:
        credential = await credential_repo.find_by_id(session, credential_id)
        if not credential:
            raise NotFoundError("credential", credential_id)

    deployment = ModelDeployment(
        model_id=model_id,
        credential_id=credential_id,
        litellm_params=litellm_params,
        model_info=model_info or {},
        deploy_name=deploy_name,
        billing_type=billing_type,
        cost_per_call=cost_per_call,
        monthly_call_quota=monthly_call_quota,
    )
    deployment = await model_repo.create_deployment(session, deployment)

    # Sync to LiteLLM
    await _sync_deployment_to_litellm(deployment, model, credential)

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
) -> dict:
    deployment = await model_repo.find_deployment_by_id(session, deployment_id)
    if not deployment:
        raise NotFoundError("deployment", deployment_id)

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
        deployment.model_info = model_info
    if is_active is not None:
        deployment.is_active = is_active

    # Re-sync to LiteLLM
    model = await model_repo.find_by_id(session, deployment.model_id)
    credential = None
    if deployment.credential_id:
        credential = await credential_repo.find_by_id(session, deployment.credential_id)

    if model and deployment.litellm_model_id:
        try:
            sync_params = dict(deployment.litellm_params)
            if credential and "litellm_credential_name" not in sync_params and "api_key" not in sync_params:
                sync_params["litellm_credential_name"] = credential.credential_name
            await litellm_client.update_model(
                litellm_model_id=deployment.litellm_model_id,
                model_name=model.model_id,
                litellm_params=sync_params,
                model_info=deployment.model_info,
            )
        except litellm_client.LiteLLMError:
            logger.warning("litellm update model failed for deployment %s", deployment_id)

    await session.commit()
    await session.refresh(deployment)
    return _serialize_deployment(deployment)


async def delete_deployment(session: AsyncSession, deployment_id: int) -> None:
    deployment = await model_repo.find_deployment_by_id(session, deployment_id)
    if not deployment:
        raise NotFoundError("deployment", deployment_id)

    if deployment.litellm_model_id:
        try:
            await litellm_client.delete_model(deployment.litellm_model_id)
        except litellm_client.LiteLLMError:
            logger.warning("litellm delete model failed for deployment %s", deployment_id)

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
    try:
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
    except litellm_client.LiteLLMError:
        logger.warning("failed to sync router settings to litellm")

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

    await session.commit()
    await session.refresh(model)
    return await get_model_visibility(session, model_id)


# --- Private helpers ---


async def _sync_deployment_to_litellm(
    deployment: ModelDeployment,
    model: Model,
    credential=None,
) -> None:
    litellm_params = dict(deployment.litellm_params)

    # Inject credential reference if not already specified
    if credential and "litellm_credential_name" not in litellm_params and "api_key" not in litellm_params:
        litellm_params["litellm_credential_name"] = credential.credential_name

    try:
        result = await litellm_client.add_model(
            model_name=model.model_id,
            litellm_params=litellm_params,
            model_info=deployment.model_info or {},
        )
        litellm_id = result.get("model_info", {}).get("id")
        if litellm_id:
            deployment.litellm_model_id = litellm_id
    except litellm_client.LiteLLMError:
        logger.warning("litellm add model failed for deployment %s", deployment.id)


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
