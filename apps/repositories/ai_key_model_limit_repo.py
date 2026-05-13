from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKeyModelLimit


async def find_by_key_id(session: AsyncSession, ai_key_id: int) -> list[AiKeyModelLimit]:
    result = await session.execute(
        select(AiKeyModelLimit)
        .where(AiKeyModelLimit.ai_key_id == ai_key_id)
        .order_by(AiKeyModelLimit.model_id)
    )
    return list(result.scalars().all())


async def find_by_key_and_model(
    session: AsyncSession, ai_key_id: int, model_id: int
) -> AiKeyModelLimit | None:
    result = await session.execute(
        select(AiKeyModelLimit).where(
            AiKeyModelLimit.ai_key_id == ai_key_id,
            AiKeyModelLimit.model_id == model_id,
        )
    )
    return result.scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    ai_key_id: int,
    model_id: int,
    tpm: int | None = None,
    rpm: int | None = None,
    max_tokens: int | None = None,
    max_calls: int | None = None,
) -> AiKeyModelLimit:
    existing = await find_by_key_and_model(session, ai_key_id, model_id)
    if existing:
        existing.tpm = tpm
        existing.rpm = rpm
        existing.max_tokens = max_tokens
        existing.max_calls = max_calls
        await session.flush()
        await session.refresh(existing)
        return existing

    limit = AiKeyModelLimit(
        ai_key_id=ai_key_id,
        model_id=model_id,
        tpm=tpm,
        rpm=rpm,
        max_tokens=max_tokens,
        max_calls=max_calls,
    )
    session.add(limit)
    await session.flush()
    await session.refresh(limit)
    return limit


async def delete_by_key_and_model(
    session: AsyncSession, ai_key_id: int, model_id: int
) -> bool:
    result = await session.execute(
        delete(AiKeyModelLimit).where(
            AiKeyModelLimit.ai_key_id == ai_key_id,
            AiKeyModelLimit.model_id == model_id,
        )
    )
    return result.rowcount > 0


async def delete_all_by_key(session: AsyncSession, ai_key_id: int) -> int:
    result = await session.execute(
        delete(AiKeyModelLimit).where(AiKeyModelLimit.ai_key_id == ai_key_id)
    )
    return result.rowcount
