from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.api_key_utils import generate_api_key
from core.crypto import decrypt, encrypt
from exceptions import NotFoundError
from models.db import ApiKey
from repositories import api_key_repo


async def create_api_key(
    session: AsyncSession,
    name: str,
    description: str,
    expires_at: datetime | None,
    created_by: int,
) -> tuple[dict, str]:
    raw_key, key_prefix, key_hash = generate_api_key()
    api_key = ApiKey(
        name=name,
        description=description,
        key_prefix=key_prefix,
        key_hash=key_hash,
        key_encrypted=encrypt(raw_key),
        is_active=True,
        created_by=created_by,
        expires_at=expires_at,
    )
    api_key = await api_key_repo.create(session, api_key)
    await session.commit()
    return _serialize(api_key, include_raw=True), raw_key


async def list_api_keys(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
) -> dict:
    total = await api_key_repo.count_all(session, keyword)
    keys = await api_key_repo.find_all(session, page, page_size, keyword)
    return {
        "items": [_serialize(k, include_raw=True) for k in keys],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_api_key(session: AsyncSession, key_id: int) -> dict:
    api_key = await api_key_repo.find_by_id(session, key_id)
    if not api_key:
        raise NotFoundError("api_key", key_id)
    return _serialize(api_key, include_raw=True)


async def update_api_key(
    session: AsyncSession,
    key_id: int,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    expires_at: datetime | None = None,
    expires_at_provided: bool = False,
) -> dict:
    api_key = await api_key_repo.find_by_id(session, key_id)
    if not api_key:
        raise NotFoundError("api_key", key_id)
    if name is not None:
        api_key.name = name
    if description is not None:
        api_key.description = description
    if is_active is not None:
        api_key.is_active = is_active
    if expires_at_provided:
        api_key.expires_at = expires_at
    await session.commit()
    await session.refresh(api_key)
    return _serialize(api_key, include_raw=True)


async def delete_api_key(session: AsyncSession, key_id: int) -> None:
    api_key = await api_key_repo.find_by_id(session, key_id)
    if not api_key:
        raise NotFoundError("api_key", key_id)
    await api_key_repo.delete(session, key_id)
    await session.commit()


def _serialize(api_key: ApiKey, include_raw: bool = False) -> dict:
    data = {
        "id": api_key.id,
        "name": api_key.name,
        "description": api_key.description,
        "key_prefix": api_key.key_prefix,
        "is_active": api_key.is_active,
        "created_by": api_key.created_by,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "updated_at": api_key.updated_at.isoformat() if api_key.updated_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "last_used_at": (
            api_key.last_used_at.isoformat() if api_key.last_used_at else None
        ),
    }
    if include_raw:
        data["raw_key"] = (
            decrypt(api_key.key_encrypted) if api_key.key_encrypted else ""
        )
    return data
