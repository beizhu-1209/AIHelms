from sqlalchemy.ext.asyncio import AsyncSession

from models.db import License


async def get(session: AsyncSession) -> License | None:
    return await session.get(License, 1)


async def upsert(session: AsyncSession, **fields: object) -> License:
    row = await get(session)
    if row is None:
        row = License(id=1, **fields)
        session.add(row)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    await session.flush()
    return row
