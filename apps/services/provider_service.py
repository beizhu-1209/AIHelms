import logging

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError
from models.db import Provider
from repositories import provider_repo, credential_repo

logger = logging.getLogger(__name__)


async def list_providers(session: AsyncSession, page: int = 1, page_size: int = 50) -> dict:
    total = await provider_repo.count_all(session)
    items = await provider_repo.find_all(session, page, page_size)
    return {
        "items": [_serialize(p) for p in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_provider_by_id(session: AsyncSession, provider_id: int) -> dict:
    provider = await provider_repo.find_by_id(session, provider_id)
    if not provider:
        raise NotFoundError("provider", provider_id)
    return _serialize(provider)


async def create_provider(
    session: AsyncSession,
    name: str,
    provider_type: str,
    billing_type: str = "token",
    monthly_budget: float | None = None,
    description: str = "",
    config: dict | None = None,
) -> dict:
    provider = Provider(
        name=name,
        provider_type=provider_type,
        billing_type=billing_type,
        monthly_budget=monthly_budget,
        description=description,
        config=config or {},
    )
    provider = await provider_repo.create(session, provider)
    await session.commit()
    await session.refresh(provider)
    return _serialize(provider)


async def update_provider(
    session: AsyncSession,
    provider_id: int,
    name: str | None = None,
    provider_type: str | None = None,
    billing_type: str | None = None,
    monthly_budget: float | None = None,
    is_active: bool | None = None,
    description: str | None = None,
    config: dict | None = None,
) -> dict:
    provider = await provider_repo.find_by_id(session, provider_id)
    if not provider:
        raise NotFoundError("provider", provider_id)

    if name is not None:
        provider.name = name
    if provider_type is not None:
        provider.provider_type = provider_type
    if billing_type is not None:
        provider.billing_type = billing_type
    if monthly_budget is not None:
        provider.monthly_budget = monthly_budget
    if is_active is not None:
        provider.is_active = is_active
    if description is not None:
        provider.description = description
    if config is not None:
        provider.config = config

    await session.commit()
    await session.refresh(provider)
    return _serialize(provider)


async def delete_provider(session: AsyncSession, provider_id: int) -> None:
    provider = await provider_repo.find_by_id(session, provider_id)
    if not provider:
        raise NotFoundError("provider", provider_id)

    credentials = await credential_repo.find_by_provider(session, provider_id)
    if credentials:
        raise ConflictError("该供应商下有凭证，请先删除或迁移凭证")

    provider.is_active = False
    await session.commit()


def _serialize(provider: Provider) -> dict:
    return {
        "id": provider.id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "billing_type": provider.billing_type,
        "monthly_budget": str(provider.monthly_budget) if provider.monthly_budget else None,
        "monthly_used": str(provider.monthly_used) if provider.monthly_used else "0",
        "is_active": provider.is_active,
        "description": provider.description,
        "config": provider.config,
        "credential_count": len(provider.credentials) if provider.credentials else 0,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
    }
