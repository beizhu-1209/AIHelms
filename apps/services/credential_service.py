import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import NotFoundError, ConflictError
from models.db import Credential
from repositories import credential_repo
from services import litellm_client
from services.litellm_credential_payload import build_litellm_credential_values

logger = logging.getLogger(__name__)


async def list_credentials(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    provider_id: int | None = None,
) -> dict:
    total = await credential_repo.count_all(session, provider_id=provider_id)
    items = await credential_repo.find_all(session, page, page_size, provider_id=provider_id)
    return {
        "items": [_serialize(c) for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_credential_by_id(session: AsyncSession, credential_id: int) -> dict:
    credential = await credential_repo.find_by_id(session, credential_id)
    if not credential:
        raise NotFoundError("credential", credential_id)
    return _serialize(credential)


async def create_credential(
    session: AsyncSession,
    credential_name: str,
    credential_values: dict,
    provider_id: int,
    credential_info: dict | None = None,
) -> dict:
    existing = await credential_repo.find_by_name(session, credential_name, provider_id=provider_id)
    if existing:
        raise ConflictError(f"该供应商下凭证名 '{credential_name}' 已存在")

    credential = Credential(
        credential_name=credential_name,
        provider_id=provider_id,
        credential_values=credential_values,
        credential_info=credential_info or {},
    )
    credential = await credential_repo.create(session, credential)

    # Sync to LiteLLM. Some compatible providers need LiteLLM-only auth headers;
    # do not persist those generated values back to platform credential_values.
    litellm_credential_values = await build_litellm_credential_values(
        session=session,
        credential_values=credential_values,
        credential_info=credential_info or {},
        provider_id=provider_id,
    )
    await litellm_client.create_credential(
        credential_name=credential_name,
        credential_values=litellm_credential_values,
        credential_info=credential_info or {},
    )
    credential.litellm_synced = True

    await session.commit()
    credential = await credential_repo.find_by_id(session, credential.id)
    return _serialize(credential)


async def update_credential(
    session: AsyncSession,
    credential_id: int,
    credential_values: dict | None = None,
    provider_id: int | None = None,
    credential_info: dict | None = None,
    is_active: bool | None = None,
) -> dict:
    credential = await credential_repo.find_by_id(session, credential_id)
    if not credential:
        raise NotFoundError("credential", credential_id)

    values_changed = credential_values is not None
    info_changed = credential_info is not None
    provider_changed = provider_id is not None and provider_id != credential.provider_id
    if values_changed:
        merged_values = dict(credential.credential_values or {})
        merged_values.update(credential_values or {})
        credential.credential_values = merged_values
    if provider_id is not None:
        credential.provider_id = provider_id
    if info_changed:
        credential.credential_info = credential_info
    active_changed = False
    if is_active is not None and is_active != credential.is_active:
        credential.is_active = is_active
        active_changed = True

    credential_payload_changed = values_changed or info_changed or provider_changed

    # Sync the full effective credential payload to LiteLLM. LiteLLM PATCH does
    # not behave as a partial update for credentials.
    if credential_payload_changed:
        litellm_credential_values = await build_litellm_credential_values(
            session=session,
            credential_values=credential.credential_values or {},
            credential_info=credential.credential_info or {},
            provider_id=credential.provider_id,
        )
        await litellm_client.update_credential(
            credential_name=credential.credential_name,
            credential_values=litellm_credential_values,
            credential_info=credential.credential_info or {},
        )
        credential.litellm_synced = True

    # 凭证内容或启用状态变化时，同步关联 deployments 在 LiteLLM 侧的路由参数。
    if credential_payload_changed or active_changed:
        from services import model_service
        result = await model_service.sync_credential_routing(session, credential)
        if result.get("deployment_errors"):
            logger.error(
                "credential deployment sync finished with errors: credential=%s errors=%s",
                credential.id,
                result["deployment_errors"],
            )

    await session.commit()
    credential = await credential_repo.find_by_id(session, credential.id)
    return _serialize(credential)


async def delete_credential(session: AsyncSession, credential_id: int) -> None:
    credential = await credential_repo.find_by_id(session, credential_id)
    if not credential:
        raise NotFoundError("credential", credential_id)

    if credential.deployments:
        raise ConflictError("该凭证被部署引用，请先解除关联")

    # Delete from LiteLLM
    if credential.litellm_synced:
        await litellm_client.delete_credential(credential.credential_name)

    await session.delete(credential)
    await session.commit()


def _serialize(credential: Credential) -> dict:
    return {
        "id": credential.id,
        "credential_name": credential.credential_name,
        "provider_id": credential.provider_id,
        "provider_name": credential.provider.name if credential.provider else None,
        "provider_type": credential.provider.provider_type if credential.provider else None,
        "credential_values": credential.credential_values,
        "credential_info": credential.credential_info,
        "litellm_synced": credential.litellm_synced,
        "is_active": credential.is_active,
        "deployment_count": len(credential.deployments) if credential.deployments else 0,
        "created_at": fmt_local_time(credential.created_at),
        "updated_at": fmt_local_time(credential.updated_at),
    }

