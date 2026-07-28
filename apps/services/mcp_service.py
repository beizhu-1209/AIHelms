import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import ConflictError, NotFoundError, ValidationError
from models.db import McpServer, McpTool
from repositories import mcp_repo
from services import litellm_client
from services.icon_url import normalize_hosted_icon_path, resolve_icon_url
from services.litellm_client import LiteLLMError

logger = logging.getLogger(__name__)


# ─── MCP Server CRUD ─────────────────────────────────────────────────────────


async def list_servers(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    is_active: bool | None = None,
    is_published: bool | None = None,
    status: str | None = None,
) -> dict:
    total = await mcp_repo.count_servers(
        session, category, is_active, is_published, status
    )
    items = await mcp_repo.find_all_servers(
        session, page, page_size, category, is_active, is_published, status
    )
    return {
        "items": [_serialize_server(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_server(session: AsyncSession, server_id: int) -> dict:
    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)
    data = _serialize_server(server)
    tools = await mcp_repo.find_tools_by_server(session, server_id)
    data["tools"] = [_serialize_tool(t) for t in tools]
    return data


async def create_server(
    session: AsyncSession,
    name: str,
    server_name: str,
    url: str,
    transport: str = "sse",
    auth_type: str = "none",
    credentials: dict | None = None,
    description: str = "",
    instructions: str = "",
    mcp_info: dict | None = None,
    extra_headers: list[str] | None = None,
    allowed_tools: list | None = None,
    authorization_url: str | None = None,
    token_url: str | None = None,
    registration_url: str | None = None,
    category: str = "general",
    tags: list | None = None,
    author: str = "",
    icon_url: str = "",
    documentation_url: str = "",
    source_url: str = "",
    billing_type: str = "per_call",
    internal_cost_per_call: float = 0,
    external_cost_per_call: float = 0,
    is_published: bool = False,
    visibility_type: str = "all",
    requires_approval: bool = False,
    created_by: int | None = None,
) -> dict:
    if transport not in ("sse", "http", "streamable_http", "streamableHttp"):
        raise ValidationError("transport 只支持 sse 或 streamableHttp")

    if "-" in server_name:
        raise ValidationError(
            "server_name 不能包含 '-'（LiteLLM 限制），请使用 '_' 替代"
        )

    existing = await mcp_repo.find_server_by_name(session, server_name)
    if existing:
        raise ConflictError(f"MCP Server 名称 '{server_name}' 已存在")

    sid = str(uuid.uuid4())
    server = McpServer(
        server_id=sid,
        name=name,
        server_name=server_name,
        url=url,
        transport=transport,
        auth_type=auth_type,
        credentials=credentials or {},
        description=description,
        instructions=instructions,
        mcp_info=mcp_info or {},
        extra_headers=extra_headers or [],
        allowed_tools=allowed_tools or [],
        authorization_url=authorization_url,
        token_url=token_url,
        registration_url=registration_url,
        category=category,
        tags=tags or [],
        author=author,
        icon_url=normalize_hosted_icon_path(icon_url) or "",
        documentation_url=documentation_url,
        source_url=source_url,
        billing_type=billing_type,
        internal_cost_per_call=internal_cost_per_call,
        external_cost_per_call=external_cost_per_call,
        is_published=is_published,
        visibility_type=visibility_type,
        requires_approval=requires_approval,
        created_by=created_by,
    )
    server = await mcp_repo.create_server(session, server)
    await session.flush()

    try:
        await _sync_server_to_litellm(server)
    except LiteLLMError as e:
        await session.rollback()
        logger.error("sync mcp server to litellm failed: %s", str(e))
        raise ValidationError("保存失败，服务器内部错误")

    await session.commit()
    await session.refresh(server)

    # 创建后自动同步工具列表
    try:
        await refresh_tools(session, server.id)
    except (ValidationError, LiteLLMError):
        pass  # 工具同步失败不影响创建

    return _serialize_server(server)


async def update_server(
    session: AsyncSession,
    server_id: int,
    **kwargs,
) -> dict:
    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)

    if "transport" in kwargs and kwargs["transport"] not in (
        "sse",
        "http",
        "streamable_http",
        "streamableHttp",
    ):
        raise ValidationError("transport 只支持 sse 或 streamableHttp")

    if "server_name" in kwargs and kwargs["server_name"] != server.server_name:
        if "-" in kwargs["server_name"]:
            raise ValidationError(
                "server_name 不能包含 '-'（LiteLLM 限制），请使用 '_' 替代"
            )
        existing = await mcp_repo.find_server_by_name(session, kwargs["server_name"])
        if existing:
            raise ConflictError(f"MCP Server 名称 '{kwargs['server_name']}' 已存在")

    if "icon_url" in kwargs:
        kwargs["icon_url"] = normalize_hosted_icon_path(kwargs["icon_url"]) or ""

    for key, value in kwargs.items():
        if hasattr(server, key) and value is not None:
            setattr(server, key, value)

    # 发布且不需要审批时，自动同步到所有主 Key
    if server.is_published and not server.requires_approval:
        from services import ai_key_service

        await ai_key_service.sync_public_resource_to_all_keys(
            session, "mcps", server.id
        )

    await session.flush()

    try:
        await _sync_server_to_litellm(server)
    except LiteLLMError as e:
        await session.rollback()
        logger.error("sync mcp server to litellm failed: %s", str(e))
        raise ValidationError("保存失败，服务器内部错误")

    await session.commit()
    await session.refresh(server)

    return _serialize_server(server)


async def delete_server(session: AsyncSession, server_id: int) -> None:
    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)

    litellm_server_id = server.server_id
    await mcp_repo.delete_server(session, server_id)
    await session.commit()

    # 在 LiteLLM 侧禁用而非删除
    if litellm_server_id:
        try:
            await litellm_client.update_mcp_server(
                server_id=litellm_server_id,
                allow_all_keys=False,
            )
        except LiteLLMError:
            pass  # LiteLLM 禁用失败不影响平台删除


# ─── MCP Tools ───────────────────────────────────────────────────────────────


async def refresh_tools(session: AsyncSession, server_id: int) -> list[dict]:
    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)

    creds = server.credentials if server.credentials else None
    litellm_transport = (
        "http"
        if server.transport in ("streamableHttp", "streamable_http")
        else server.transport
    )
    try:
        remote_tools = await litellm_client.list_mcp_tools_from_server(
            url=server.url,
            transport=litellm_transport,
            auth_type=server.auth_type if server.auth_type != "none" else None,
            credentials=creds,
        )
    except LiteLLMError as e:
        logger.error("failed to fetch tools from mcp server: %s", str(e))
        raise ValidationError(f"无法从 MCP Server 获取工具列表: {e}")

    # 保留已有 tool 的计费信息
    existing_tools = await mcp_repo.find_tools_by_server(session, server_id)
    billing_map = {
        t.tool_name: {
            "billing_type": t.billing_type,
            "internal_cost_per_call": t.internal_cost_per_call,
            "external_cost_per_call": t.external_cost_per_call,
        }
        for t in existing_tools
        if t.billing_type or t.internal_cost_per_call or t.external_cost_per_call
    }

    await mcp_repo.delete_tools_by_server(session, server_id)

    new_tools = []
    for tool_data in remote_tools:
        tool_name = tool_data.get("name", "")
        namespaced = f"{server.server_name}_{tool_name}"
        billing = billing_map.get(tool_name, {})
        tool = McpTool(
            server_id=server_id,
            tool_name=tool_name,
            namespaced_name=namespaced,
            display_name=tool_data.get("display_name", tool_name),
            description=tool_data.get("description", ""),
            input_schema=tool_data.get(
                "inputSchema", tool_data.get("input_schema", {})
            ),
            billing_type=billing.get("billing_type"),
            internal_cost_per_call=billing.get("internal_cost_per_call"),
            external_cost_per_call=billing.get("external_cost_per_call"),
        )
        new_tools.append(tool)

    if new_tools:
        await mcp_repo.bulk_create_tools(session, new_tools)
    await session.commit()

    return [_serialize_tool(t) for t in new_tools]


async def get_tools(session: AsyncSession, server_id: int) -> list[dict]:
    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)
    tools = await mcp_repo.find_tools_by_server(session, server_id)
    return [_serialize_tool(t) for t in tools]


async def update_tool_billing(
    session: AsyncSession,
    tool_id: int,
    billing_type: str | None = None,
    internal_cost_per_call: float | None = None,
    external_cost_per_call: float | None = None,
) -> dict:
    tool = await mcp_repo.find_tool_by_id(session, tool_id)
    if not tool:
        raise NotFoundError("mcp_tool", tool_id)

    if billing_type is not None:
        tool.billing_type = billing_type
    if internal_cost_per_call is not None:
        tool.internal_cost_per_call = internal_cost_per_call
    if external_cost_per_call is not None:
        tool.external_cost_per_call = external_cost_per_call

    await session.commit()
    await session.refresh(tool)

    # 重新同步 server 的 cost_info 到 LiteLLM
    server = await mcp_repo.find_server_by_id(session, tool.server_id)
    if server and server.litellm_synced:
        # 确保 tools relationship 包含最新数据
        await session.refresh(server, ["tools"])
        try:
            await _sync_server_to_litellm(server)
            await session.commit()
        except LiteLLMError as e:
            logger.error(
                "sync mcp cost to litellm failed after tool billing update: %s", str(e)
            )

    return _serialize_tool(tool)


# ─── Health Check ────────────────────────────────────────────────────────────


async def health_check_server(session: AsyncSession, server_id: int) -> dict:
    from datetime import datetime

    server = await mcp_repo.find_server_by_id(session, server_id)
    if not server:
        raise NotFoundError("mcp_server", server_id)

    litellm_transport = (
        "http"
        if server.transport in ("streamableHttp", "streamable_http")
        else server.transport
    )
    try:
        await litellm_client.test_mcp_connection(
            url=server.url,
            transport=litellm_transport,
            auth_type=server.auth_type if server.auth_type != "none" else None,
            credentials=server.credentials if server.credentials else None,
        )
        server.status = "healthy"
        server.health_check_error = None
    except LiteLLMError as e:
        server.status = "unhealthy"
        server.health_check_error = str(e)

    server.last_health_check = datetime.utcnow()
    await session.commit()
    await session.refresh(server)
    return _serialize_server(server)


# ─── LiteLLM Sync ───────────────────────────────────────────────────────────


async def _sync_server_to_litellm(server: McpServer) -> None:
    mcp_info = _build_mcp_info(server)
    # LiteLLM 只支持 sse/http/stdio，streamableHttp 映射为 http
    litellm_transport = (
        "http"
        if server.transport in ("streamableHttp", "streamable_http")
        else server.transport
    )

    if server.litellm_synced:
        await litellm_client.update_mcp_server(
            server_id=server.server_id,
            server_name=server.server_name,
            url=server.url,
            transport=litellm_transport,
            auth_type=server.auth_type if server.auth_type != "none" else None,
            credentials=server.credentials if server.credentials else None,
            description=server.description,
            instructions=server.instructions,
            mcp_info=mcp_info,
            extra_headers=server.extra_headers if server.extra_headers else None,
            allow_all_keys=True,
        )
    else:
        await litellm_client.create_mcp_server(
            server_id=server.server_id,
            server_name=server.server_name,
            url=server.url,
            transport=litellm_transport,
            auth_type=server.auth_type if server.auth_type != "none" else None,
            credentials=server.credentials if server.credentials else None,
            description=server.description,
            instructions=server.instructions,
            mcp_info=mcp_info,
            extra_headers=server.extra_headers if server.extra_headers else None,
        )
    server.litellm_synced = True
    server.litellm_sync_error = None


def _build_mcp_info(server: McpServer) -> dict | None:
    """组装 mcp_info，包含 LiteLLM 需要的 mcp_server_cost_info。"""
    from core.config import settings

    mcp_info = dict(server.mcp_info) if server.mcp_info else {}
    rate = settings.usd_to_cny_rate

    # 构建成本信息（平台存人民币，LiteLLM 需要美元）
    tool_costs = {}
    if server.tools:
        for tool in server.tools:
            if tool.external_cost_per_call:
                tool_costs[tool.tool_name] = round(
                    float(tool.external_cost_per_call) / rate, 6
                )

    default_cost = (
        round(float(server.external_cost_per_call) / rate, 6)
        if server.external_cost_per_call
        else None
    )

    if default_cost or tool_costs:
        cost_info: dict = {}
        if default_cost:
            cost_info["default_cost_per_query"] = default_cost
        if tool_costs:
            cost_info["tool_name_to_cost_per_query"] = tool_costs
        mcp_info["mcp_server_cost_info"] = cost_info
    else:
        mcp_info["mcp_server_cost_info"] = None

    # 保留 description 和 server_name 供 LiteLLM 展示
    mcp_info["description"] = server.description or ""
    mcp_info["server_name"] = server.server_name

    return mcp_info if mcp_info else None


# ─── Serializers ─────────────────────────────────────────────────────────────


def _serialize_server(server: McpServer) -> dict:
    return {
        "id": server.id,
        "server_id": server.server_id,
        "name": server.name,
        "server_name": server.server_name,
        "description": server.description,
        "url": server.url,
        "transport": server.transport,
        "auth_type": server.auth_type,
        "credentials": server.credentials,
        "instructions": server.instructions,
        "mcp_info": server.mcp_info,
        "extra_headers": server.extra_headers,
        "allowed_tools": server.allowed_tools,
        "authorization_url": server.authorization_url,
        "token_url": server.token_url,
        "registration_url": server.registration_url,
        "category": server.category,
        "tags": server.tags,
        "author": server.author,
        "icon_url": resolve_icon_url(server.icon_url),
        "documentation_url": server.documentation_url,
        "source_url": server.source_url,
        "billing_type": server.billing_type,
        "internal_cost_per_call": float(server.internal_cost_per_call),
        "external_cost_per_call": float(server.external_cost_per_call),
        "is_active": server.is_active,
        "is_published": server.is_published,
        "visibility_type": server.visibility_type,
        "requires_approval": server.requires_approval,
        "status": server.status,
        "call_count": server.call_count or 0,
        "last_health_check": fmt_local_time(server.last_health_check),
        "health_check_error": server.health_check_error,
        "litellm_synced": server.litellm_synced,
        "litellm_sync_error": server.litellm_sync_error,
        "created_by": server.created_by,
        "created_at": fmt_local_time(server.created_at),
        "updated_at": fmt_local_time(server.updated_at),
    }


def _serialize_tool(tool: McpTool) -> dict:
    return {
        "id": tool.id,
        "server_id": tool.server_id,
        "tool_name": tool.tool_name,
        "namespaced_name": tool.namespaced_name,
        "display_name": tool.display_name,
        "description": tool.description,
        "input_schema": tool.input_schema,
        "billing_type": tool.billing_type,
        "internal_cost_per_call": (
            float(tool.internal_cost_per_call)
            if tool.internal_cost_per_call is not None
            else None
        ),
        "external_cost_per_call": (
            float(tool.external_cost_per_call)
            if tool.external_cost_per_call is not None
            else None
        ),
        "is_active": tool.is_active,
    }


# ─── Categories ─────────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[dict]:
    cats = await mcp_repo.list_categories(session)
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "sort_order": c.sort_order,
        }
        for c in cats
    ]


async def create_category(
    session: AsyncSession, name: str, description: str = "", sort_order: int = 0
) -> dict:
    from models.db import McpCategory

    existing = await mcp_repo.find_category_by_name(session, name)
    if existing:
        raise ConflictError(f"分类 '{name}' 已存在")

    cat = McpCategory(name=name, description=description, sort_order=sort_order)
    cat = await mcp_repo.create_category(session, cat)
    await session.commit()
    return {
        "id": cat.id,
        "name": cat.name,
        "description": cat.description,
        "sort_order": cat.sort_order,
    }


async def delete_category(session: AsyncSession, category_id: int) -> None:
    cat = await mcp_repo.find_category_by_id(session, category_id)
    if not cat:
        raise NotFoundError("mcp_category", category_id)
    await mcp_repo.delete_category(session, category_id)
    await session.commit()
