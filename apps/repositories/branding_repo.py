from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Branding


async def get(session: AsyncSession) -> Branding:
    row = await session.get(Branding, 1)
    if row is None:
        row = Branding(id=1, platform_name="AIHelms")
        session.add(row)
        await session.flush()
    return row


async def update(session: AsyncSession, **fields: object) -> Branding:
    row = await get(session)
    for key, value in fields.items():
        setattr(row, key, value)
    await session.flush()
    return row
