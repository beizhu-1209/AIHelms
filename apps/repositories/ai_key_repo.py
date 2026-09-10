from sqlalchemy import String, bindparam, func, select, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey, User


async def create(session: AsyncSession, ai_key: AiKey) -> AiKey:
    session.add(ai_key)
    await session.flush()
    await session.refresh(ai_key)
    return ai_key


async def find_by_id(session: AsyncSession, key_id: int) -> AiKey | None:
    result = await session.execute(select(AiKey).where(AiKey.id == key_id))
    return result.scalar_one_or_none()


async def find_by_litellm_key_id(session: AsyncSession, token: str) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(AiKey.litellm_key_id == token)
    )
    return result.scalar_one_or_none()


async def find_by_litellm_key_alias(session: AsyncSession, alias: str) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(AiKey.litellm_key_alias == alias)
    )
    return result.scalar_one_or_none()


async def find_by_owner(
    session: AsyncSession,
    owner_type: str,
    owner_id: int,
) -> list[AiKey]:
    result = await session.execute(
        select(AiKey)
        .where(AiKey.owner_type == owner_type, AiKey.owner_id == owner_id)
        .order_by(AiKey.id)
    )
    return list(result.scalars().all())


async def find_by_user(session: AsyncSession, user_id: int) -> list[AiKey]:
    result = await session.execute(
        select(AiKey)
        .where(AiKey.owner_type == "user", AiKey.owner_id == user_id)
        .order_by(AiKey.id)
    )
    return list(result.scalars().all())


async def find_personal_main(session: AsyncSession, user_id: int) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(
            AiKey.owner_type == "user",
            AiKey.owner_id == user_id,
            AiKey.key_type == "personal_main",
        )
    )
    return result.scalar_one_or_none()


async def find_personal_main_keys_for_model_sync(
    session: AsyncSession,
    user_ids: list[int] | None = None,
    include_inactive: bool = False,
) -> list[AiKey]:
    stmt = (
        select(AiKey)
        .join(User, User.id == AiKey.owner_id)
        .where(
            AiKey.key_type == "personal_main",
            AiKey.owner_type == "user",
            User.is_admin.is_(False),
        )
        .order_by(AiKey.id)
    )
    if user_ids is not None:
        stmt = stmt.where(AiKey.owner_id.in_(user_ids))
    if not include_inactive:
        stmt = stmt.where(AiKey.is_active.is_(True), User.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def sync_litellm_model_access(
    session: AsyncSession,
    model_id: str | list[str],
    add_token_hashes: list[str],
    remove_token_hashes: list[str],
    remove_model_ids: list[str] | None = None,
) -> None:
    """Apply a model grant/revocation to LiteLLM keys in bulk.

    LiteLLM treats an empty ``models`` array as unrestricted access.  Keep the
    sentinel value on keys which have no model grants so revocation cannot
    accidentally widen access.
    """
    model_ids = [model_id] if isinstance(model_id, str) else list(model_id)
    revoke_ids = remove_model_ids or model_ids
    token_param = bindparam("tokens", type_=ARRAY(String()))
    if add_token_hashes:
        for current_model_id in model_ids:
            await session.execute(
                text(
                    'UPDATE public."LiteLLM_VerificationToken" '
                    "SET models = array_append("
                    "array_remove(COALESCE(models, ARRAY[]::text[]), 'no-default-models'), "
                    ":model_id) "
                    "WHERE token = ANY(:tokens) "
                    "AND NOT (:model_id = ANY(COALESCE(models, ARRAY[]::text[])))"
                ).bindparams(token_param),
                {"model_id": current_model_id, "tokens": add_token_hashes},
            )
    if remove_token_hashes:
        for current_model_id in revoke_ids:
            await session.execute(
                text(
                    'UPDATE public."LiteLLM_VerificationToken" '
                    "SET models = CASE "
                    "WHEN cardinality(array_remove(array_remove(COALESCE(models, ARRAY[]::text[]), 'no-default-models'), :model_id)) = 0 "
                    "THEN ARRAY['no-default-models']::text[] "
                    "ELSE array_remove(array_remove(COALESCE(models, ARRAY[]::text[]), 'no-default-models'), :model_id) "
                    "END "
                    "WHERE token = ANY(:tokens)"
                ).bindparams(token_param),
                {"model_id": current_model_id, "tokens": remove_token_hashes},
            )


async def get_litellm_model_access(
    session: AsyncSession,
    token_hashes: list[str],
) -> dict[str, set[str]]:
    token_param = bindparam("tokens", type_=ARRAY(String()))
    result = await session.execute(
        text(
            'SELECT token, models FROM public."LiteLLM_VerificationToken" '
            'WHERE token = ANY(:tokens)'
        ).bindparams(token_param),
        {"tokens": token_hashes},
    )
    actual_by_token = {row[0]: set(row[1] or []) for row in result.all()}
    return actual_by_token


async def find_all_main_keys(session: AsyncSession) -> list[AiKey]:
    """查找所有主 Key（personal_main / dept_main / project_main）。"""
    result = await session.execute(
        select(AiKey).where(
            AiKey.key_type.in_(["personal_main", "dept_main", "project_main"]),
            AiKey.is_active == True,
        )
    )
    return list(result.scalars().all())


async def find_keys_referencing_model(session: AsyncSession, model_id_str: str) -> list[AiKey]:
    """查找 models 列表中引用了指定 model_id 字符串的所有 Key（含场景 Key）。"""
    result = await session.execute(
        select(AiKey).where(AiKey.models.contains([model_id_str]))
    )
    return list(result.scalars().all())


async def find_main_key(session: AsyncSession, owner_type: str, owner_id: int, key_type: str) -> AiKey | None:
    result = await session.execute(
        select(AiKey).where(
            AiKey.owner_type == owner_type,
            AiKey.owner_id == owner_id,
            AiKey.key_type == key_type,
        )
    )
    return result.scalar_one_or_none()


async def find_all(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    owner_type: str | None = None,
    owner_id: int | None = None,
    key_type: str | None = None,
) -> list[AiKey]:
    stmt = select(AiKey).order_by(AiKey.id)
    if owner_type:
        stmt = stmt.where(AiKey.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(AiKey.owner_id == owner_id)
    if key_type:
        stmt = stmt.where(AiKey.key_type == key_type)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_all(
    session: AsyncSession,
    owner_type: str | None = None,
    owner_id: int | None = None,
    key_type: str | None = None,
) -> int:
    stmt = select(func.count(AiKey.id))
    if owner_type:
        stmt = stmt.where(AiKey.owner_type == owner_type)
    if owner_id:
        stmt = stmt.where(AiKey.owner_id == owner_id)
    if key_type:
        stmt = stmt.where(AiKey.key_type == key_type)
    result = await session.execute(stmt)
    return result.scalar_one()
