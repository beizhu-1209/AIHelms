from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.db import (
    Credential,
    Model,
    ModelAccessGroup,
    ModelDepartmentVisibility,
    ModelDeployment,
    ModelUserVisibility,
    RouterSettings,
)


async def create(session: AsyncSession, model: Model) -> Model:
    session.add(model)
    await session.flush()
    await session.refresh(model)
    return model


async def find_by_id(session: AsyncSession, model_id: int) -> Model | None:
    result = await session.execute(select(Model).where(Model.id == model_id))
    return result.scalar_one_or_none()


async def find_by_ids(session: AsyncSession, ids: list[int]) -> list[Model]:
    if not ids:
        return []
    result = await session.execute(select(Model).where(Model.id.in_(ids)))
    return list(result.scalars().all())


async def find_by_model_id(session: AsyncSession, model_id_str: str) -> Model | None:
    result = await session.execute(select(Model).where(Model.model_id == model_id_str))
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    is_active: bool | None = None,
) -> list[Model]:
    stmt = select(Model).order_by(Model.id)
    if category:
        stmt = stmt.where(Model.category == category)
    if is_active is not None:
        stmt = stmt.where(Model.is_active == is_active)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    category: str | None = None,
    is_active: bool | None = None,
) -> int:
    stmt = select(func.count(Model.id))
    if category:
        stmt = stmt.where(Model.category == category)
    if is_active is not None:
        stmt = stmt.where(Model.is_active == is_active)
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_all_active(session: AsyncSession, published_only: bool = False) -> list[Model]:
    stmt = select(Model).where(Model.is_active == True)
    if published_only:
        stmt = stmt.where(Model.is_published == True)
    result = await session.execute(stmt.order_by(Model.name))
    return list(result.scalars().all())


# --- Deployments ---


async def create_deployment(session: AsyncSession, deployment: ModelDeployment) -> ModelDeployment:
    session.add(deployment)
    await session.flush()
    await session.refresh(deployment)
    return deployment


async def find_deployment_by_id(session: AsyncSession, deployment_id: int) -> ModelDeployment | None:
    result = await session.execute(
        select(ModelDeployment).where(ModelDeployment.id == deployment_id)
    )
    return result.scalar_one_or_none()


async def find_deployments_by_model(session: AsyncSession, model_id: int) -> list[ModelDeployment]:
    result = await session.execute(
        select(ModelDeployment)
        .where(ModelDeployment.model_id == model_id)
        .options(selectinload(ModelDeployment.credential))
        .order_by(ModelDeployment.id)
    )
    return list(result.scalars().all())


async def find_all_active_deployments(session: AsyncSession) -> list[ModelDeployment]:
    result = await session.execute(
        select(ModelDeployment)
        .where(ModelDeployment.is_active == True)
        .options(selectinload(ModelDeployment.model), selectinload(ModelDeployment.credential))
        .order_by(ModelDeployment.model_id, ModelDeployment.id)
    )
    return list(result.scalars().all())


async def find_model_ids_by_credential_ids(
    session: AsyncSession, credential_ids: list[int]
) -> list[str]:
    """Return distinct model_id strings for models that have deployments using given credentials."""
    result = await session.execute(
        select(Model.model_id)
        .join(ModelDeployment, ModelDeployment.model_id == Model.id)
        .where(ModelDeployment.credential_id.in_(credential_ids))
        .distinct()
    )
    return [row[0] for row in result.all()]


async def find_model_ids_with_anthropic_deployments(
    session: AsyncSession, model_id_strs: list[str]
) -> set[str]:
    """Return the subset of model_id strings that have active anthropic-format deployments."""
    if not model_id_strs:
        return set()
    result = await session.execute(
        select(Model.model_id)
        .join(ModelDeployment, ModelDeployment.model_id == Model.id)
        .join(Credential, Credential.id == ModelDeployment.credential_id)
        .where(
            Model.model_id.in_(model_id_strs),
            ModelDeployment.is_active == True,
            Credential.credential_info["format"].astext == "anthropic",
        )
        .distinct()
    )
    return {row[0] for row in result.all()}


# --- Access Groups ---


async def create_access_group(session: AsyncSession, group: ModelAccessGroup) -> ModelAccessGroup:
    session.add(group)
    await session.flush()
    await session.refresh(group)
    return group


async def find_access_group_by_id(session: AsyncSession, group_id: int) -> ModelAccessGroup | None:
    result = await session.execute(
        select(ModelAccessGroup).where(ModelAccessGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def find_access_group_by_name(session: AsyncSession, group_name: str) -> ModelAccessGroup | None:
    result = await session.execute(
        select(ModelAccessGroup).where(ModelAccessGroup.group_name == group_name)
    )
    return result.scalar_one_or_none()


async def find_all_access_groups(session: AsyncSession) -> list[ModelAccessGroup]:
    result = await session.execute(
        select(ModelAccessGroup).order_by(ModelAccessGroup.id)
    )
    return list(result.scalars().all())


# --- Router Settings ---


async def get_router_settings(session: AsyncSession) -> RouterSettings | None:
    result = await session.execute(select(RouterSettings).limit(1))
    return result.scalar_one_or_none()


async def upsert_router_settings(session: AsyncSession, settings: RouterSettings) -> RouterSettings:
    existing = await get_router_settings(session)
    if existing:
        existing.routing_strategy = settings.routing_strategy
        existing.fallbacks = settings.fallbacks
        existing.allowed_fails = settings.allowed_fails
        existing.cooldown_time = settings.cooldown_time
        existing.num_retries = settings.num_retries
        existing.timeout = settings.timeout
        existing.config = settings.config
        await session.flush()
        await session.refresh(existing)
        return existing
    session.add(settings)
    await session.flush()
    await session.refresh(settings)
    return settings


# --- Model Visibility ---


async def find_visibility_by_model(session: AsyncSession, model_id: int) -> list[ModelDepartmentVisibility]:
    result = await session.execute(
        select(ModelDepartmentVisibility)
        .where(ModelDepartmentVisibility.model_id == model_id)
        .order_by(ModelDepartmentVisibility.id)
    )
    return list(result.scalars().all())


async def set_visibility_departments(
    session: AsyncSession, model_id: int, department_ids: list[int]
) -> None:
    await session.execute(
        sa_delete(ModelDepartmentVisibility)
        .where(ModelDepartmentVisibility.model_id == model_id)
    )
    for dept_id in department_ids:
        session.add(ModelDepartmentVisibility(model_id=model_id, department_id=dept_id))
    await session.flush()


async def find_user_visibility_by_model(session: AsyncSession, model_id: int) -> list[ModelUserVisibility]:
    result = await session.execute(
        select(ModelUserVisibility)
        .where(ModelUserVisibility.model_id == model_id)
        .order_by(ModelUserVisibility.id)
    )
    return list(result.scalars().all())


async def set_visibility_users(
    session: AsyncSession, model_id: int, user_ids: list[int]
) -> None:
    await session.execute(
        sa_delete(ModelUserVisibility)
        .where(ModelUserVisibility.model_id == model_id)
    )
    for user_id in user_ids:
        session.add(ModelUserVisibility(model_id=model_id, user_id=user_id))
    await session.flush()


async def add_visibility_users(
    session: AsyncSession, model_id: int, user_ids: list[int]
) -> None:
    existing = await session.execute(
        select(ModelUserVisibility.user_id)
        .where(ModelUserVisibility.model_id == model_id)
        .where(ModelUserVisibility.user_id.in_(user_ids))
    )
    existing_ids = {row[0] for row in existing.all()}
    for user_id in user_ids:
        if user_id not in existing_ids:
            session.add(ModelUserVisibility(model_id=model_id, user_id=user_id))
    await session.flush()


async def remove_visibility_users(
    session: AsyncSession, model_id: int, user_ids: list[int]
) -> None:
    await session.execute(
        sa_delete(ModelUserVisibility)
        .where(ModelUserVisibility.model_id == model_id)
        .where(ModelUserVisibility.user_id.in_(user_ids))
    )
    await session.flush()
