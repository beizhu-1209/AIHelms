from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import McpServer, McpTool, McpCallLog, McpCategory


# ─── McpServer ───────────────────────────────────────────────────────────────


async def create_server(session: AsyncSession, server: McpServer) -> McpServer:
    session.add(server)
    await session.flush()
    await session.refresh(server)
    return server


async def find_server_by_id(session: AsyncSession, server_id: int) -> McpServer | None:
    result = await session.execute(select(McpServer).where(McpServer.id == server_id))
    return result.scalar_one_or_none()


async def find_server_by_server_id(session: AsyncSession, server_id: str) -> McpServer | None:
    result = await session.execute(select(McpServer).where(McpServer.server_id == server_id))
    return result.scalar_one_or_none()


async def find_server_by_name(session: AsyncSession, server_name: str) -> McpServer | None:
    result = await session.execute(select(McpServer).where(McpServer.server_name == server_name))
    return result.scalar_one_or_none()


async def find_servers_by_ids(session: AsyncSession, ids: list[int]) -> list[McpServer]:
    if not ids:
        return []
    result = await session.execute(select(McpServer).where(McpServer.id.in_(ids)))
    return list(result.scalars().all())


async def find_all_servers(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    is_active: bool | None = None,
    is_published: bool | None = None,
    status: str | None = None,
) -> list[McpServer]:
    stmt = select(McpServer).order_by(McpServer.id)
    if category:
        stmt = stmt.where(McpServer.category == category)
    if is_active is not None:
        stmt = stmt.where(McpServer.is_active == is_active)
    if is_published is not None:
        stmt = stmt.where(McpServer.is_published == is_published)
    if status:
        stmt = stmt.where(McpServer.status == status)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_servers(
    session: AsyncSession,
    category: str | None = None,
    is_active: bool | None = None,
    is_published: bool | None = None,
    status: str | None = None,
) -> int:
    stmt = select(func.count(McpServer.id))
    if category:
        stmt = stmt.where(McpServer.category == category)
    if is_active is not None:
        stmt = stmt.where(McpServer.is_active == is_active)
    if is_published is not None:
        stmt = stmt.where(McpServer.is_published == is_published)
    if status:
        stmt = stmt.where(McpServer.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()


async def delete_server(session: AsyncSession, server_id: int) -> bool:
    result = await session.execute(
        sa_delete(McpServer).where(McpServer.id == server_id)
    )
    return result.rowcount > 0


# ─── McpTool ─────────────────────────────────────────────────────────────────


async def create_tool(session: AsyncSession, tool: McpTool) -> McpTool:
    session.add(tool)
    await session.flush()
    await session.refresh(tool)
    return tool


async def bulk_create_tools(session: AsyncSession, tools: list[McpTool]) -> list[McpTool]:
    session.add_all(tools)
    await session.flush()
    for tool in tools:
        await session.refresh(tool)
    return tools


async def find_tools_by_server(session: AsyncSession, server_id: int) -> list[McpTool]:
    result = await session.execute(
        select(McpTool).where(McpTool.server_id == server_id).order_by(McpTool.tool_name)
    )
    return list(result.scalars().all())


async def find_tool_by_id(session: AsyncSession, tool_id: int) -> McpTool | None:
    result = await session.execute(select(McpTool).where(McpTool.id == tool_id))
    return result.scalar_one_or_none()


async def delete_tools_by_server(session: AsyncSession, server_id: int) -> int:
    result = await session.execute(
        sa_delete(McpTool).where(McpTool.server_id == server_id)
    )
    return result.rowcount


# ─── McpCallLog ──────────────────────────────────────────────────────────────


async def create_call_log(session: AsyncSession, log: McpCallLog) -> McpCallLog:
    session.add(log)
    await session.flush()
    return log


async def find_call_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    server_id: int | None = None,
) -> list[McpCallLog]:
    stmt = select(McpCallLog).order_by(McpCallLog.called_at.desc())
    if user_id is not None:
        stmt = stmt.where(McpCallLog.user_id == user_id)
    if server_id is not None:
        stmt = stmt.where(McpCallLog.server_id == server_id)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_call_logs(
    session: AsyncSession,
    user_id: int | None = None,
    server_id: int | None = None,
) -> int:
    stmt = select(func.count(McpCallLog.id))
    if user_id is not None:
        stmt = stmt.where(McpCallLog.user_id == user_id)
    if server_id is not None:
        stmt = stmt.where(McpCallLog.server_id == server_id)
    result = await session.execute(stmt)
    return result.scalar_one()


# ─── McpCategory ─────────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[McpCategory]:
    result = await session.execute(
        select(McpCategory).order_by(McpCategory.sort_order, McpCategory.id)
    )
    return list(result.scalars().all())


async def find_category_by_id(session: AsyncSession, category_id: int) -> McpCategory | None:
    result = await session.execute(
        select(McpCategory).where(McpCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def find_category_by_name(session: AsyncSession, name: str) -> McpCategory | None:
    result = await session.execute(
        select(McpCategory).where(McpCategory.name == name)
    )
    return result.scalar_one_or_none()


async def create_category(session: AsyncSession, category: McpCategory) -> McpCategory:
    session.add(category)
    await session.flush()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    result = await session.execute(
        sa_delete(McpCategory).where(McpCategory.id == category_id)
    )
    return result.rowcount > 0
