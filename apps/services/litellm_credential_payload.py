from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Provider


def prepare_litellm_credential_values(
    credential_values: dict | None,
    credential_info: dict | None,
    provider_type: str | None,
) -> dict:
    """Build credential values for LiteLLM without mutating platform DB values."""
    values = dict(credential_values or {})
    info = credential_info or {}
    cred_format = (info.get("format") or "openai").lower()
    provider = (provider_type or "").lower()

    if provider != "vllm" or cred_format != "anthropic":
        return values

    api_key = values.get("api_key")
    if not api_key:
        return values

    existing_headers = values.get("extra_headers")
    headers = dict(existing_headers) if isinstance(existing_headers, dict) else {}
    has_authorization = any(str(name).lower() == "authorization" for name in headers)
    if not has_authorization:
        headers["authorization"] = f"Bearer {api_key}"
    values["extra_headers"] = headers
    return values


async def build_litellm_credential_values(
    session: AsyncSession,
    credential_values: dict | None,
    credential_info: dict | None,
    provider_id: int | None,
) -> dict:
    provider_type = None
    if provider_id:
        provider_type = await session.scalar(
            select(Provider.provider_type).where(Provider.id == provider_id)
        )
    return prepare_litellm_credential_values(
        credential_values=credential_values,
        credential_info=credential_info,
        provider_type=provider_type,
    )


async def build_litellm_credential_values_for_credential(
    session: AsyncSession,
    credential,
) -> dict:
    return await build_litellm_credential_values(
        session=session,
        credential_values=credential.credential_values or {},
        credential_info=credential.credential_info or {},
        provider_id=credential.provider_id,
    )
