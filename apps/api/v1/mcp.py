from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.deps import get_db, get_current_user, require_permission
from exceptions import NotFoundError, ConflictError, ValidationError
from services import mcp_service, ai_key_service

router = APIRouter(prefix="/mcp", tags=["mcp"])


class CreateServerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    server_name: str = Field(..., min_length=1, max_length=128)
    url: str = Field(..., min_length=1)
    transport: str = Field("sse", pattern=r"^(sse|http|streamable_http|streamableHttp)$")
    auth_type: str = Field("none", max_length=30)
    credentials: dict | None = None
    description: str = Field("", max_length=2000)
    instructions: str = Field("", max_length=5000)
    mcp_info: dict | None = None
    extra_headers: list[str] | None = None
    allowed_tools: list | None = None
    authorization_url: str | None = None
    token_url: str | None = None
    registration_url: str | None = None
    category: str = Field("general", max_length=50)
    tags: list[str] | None = None
    icon_url: str = Field("", max_length=500)
    documentation_url: str = Field("", max_length=500)
    source_url: str = Field("", max_length=500)
    billing_type: str = Field("per_call", pattern=r"^(per_call|free)$")
    internal_cost_per_call: float = 0
    external_cost_per_call: float = 0
    is_published: bool = False
    visibility_type: str = Field("all", pattern=r"^(all|selected)$")
    requires_approval: bool = False


class UpdateServerRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    server_name: str | None = Field(None, min_length=1, max_length=128)
    url: str | None = None
    transport: str | None = Field(None, pattern=r"^(sse|http|streamable_http|streamableHttp)$")
    auth_type: str | None = None
    credentials: dict | None = None
    description: str | None = None
    instructions: str | None = None
    mcp_info: dict | None = None
    extra_headers: list[str] | None = None
    allowed_tools: list | None = None
    authorization_url: str | None = None
    token_url: str | None = None
    registration_url: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    icon_url: str | None = None
    documentation_url: str | None = None
    source_url: str | None = None
    billing_type: str | None = Field(None, pattern=r"^(per_call|free)$")
    internal_cost_per_call: float | None = None
    external_cost_per_call: float | None = None
    is_active: bool | None = None
    is_published: bool | None = None
    visibility_type: str | None = Field(None, pattern=r"^(all|selected)$")
    requires_approval: bool | None = None


class UpdateToolBillingRequest(BaseModel):
    billing_type: str | None = Field(None, pattern=r"^(per_call|free)$")
    internal_cost_per_call: float | None = None
    external_cost_per_call: float | None = None


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field("", max_length=200)
    sort_order: int = 0


@router.get("/servers/published")
async def list_published_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """公开接口：已认证用户可查看已发布的 MCP Server 列表。"""
    data = await mcp_service.list_servers(
        session, page, page_size, category, is_active=None, is_published=True, status=None
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/servers")
async def list_servers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    is_active: bool | None = None,
    is_published: bool | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:read")),
):
    data = await mcp_service.list_servers(
        session, page, page_size, category, is_active, is_published, status
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/servers/{server_id}")
async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:read")),
):
    try:
        data = await mcp_service.get_server(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.post("/servers", summary="创建 MCP Server")
async def create_server(
    req: CreateServerRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("mcp:create")),
):
    try:
        data = await mcp_service.create_server(
            session,
            name=req.name,
            server_name=req.server_name,
            url=req.url,
            transport=req.transport,
            auth_type=req.auth_type,
            credentials=req.credentials,
            description=req.description,
            instructions=req.instructions,
            mcp_info=req.mcp_info,
            extra_headers=req.extra_headers,
            allowed_tools=req.allowed_tools,
            authorization_url=req.authorization_url,
            token_url=req.token_url,
            registration_url=req.registration_url,
            category=req.category,
            tags=req.tags,
            icon_url=req.icon_url,
            documentation_url=req.documentation_url,
            source_url=req.source_url,
            billing_type=req.billing_type,
            internal_cost_per_call=req.internal_cost_per_call,
            external_cost_per_call=req.external_cost_per_call,
            is_published=req.is_published,
            visibility_type=req.visibility_type,
            requires_approval=req.requires_approval,
            created_by=current_user["id"],
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "MCP Server 创建成功", "data": data}


@router.put("/servers/{server_id}", summary="更新 MCP Server")
async def update_server(
    server_id: int,
    req: UpdateServerRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:update")),
):
    kwargs = req.model_dump(exclude_none=True)
    try:
        data = await mcp_service.update_server(session, server_id, **kwargs)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "MCP Server 更新成功", "data": data}


@router.delete("/servers/{server_id}", summary="删除 MCP Server")
async def delete_server(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:delete")),
):
    try:
        await mcp_service.delete_server(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return {"code": 200, "message": "MCP Server 删除成功", "data": None}


@router.get("/servers/{server_id}/connect-config", summary="获取 MCP 接入配置（用户端）")
async def get_connect_config(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """返回当前用户可直接复制到客户端的 MCP 安装配置 JSON。"""
    try:
        server_data = await mcp_service.get_server(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")

    # 获取用户的 personal_main key
    keys_data = await ai_key_service.get_my_keys(session, current_user["id"])
    main_key = next((k for k in keys_data.get("personal", []) if k.get("key_type") == "personal_main"), None)
    user_key = main_key.get("litellm_key_id", "") if main_key else ""

    base_url = settings.litellm_public_url.rstrip("/")
    server_name = server_data["server_name"]

    mcp_url = f"{base_url}/{server_name}/mcp"

    config = {
        "mcpServers": {
            server_name: {
                "url": mcp_url,
                "description": server_data.get("description", ""),
                "isActive": True,
                "name": server_data["name"],
                "headers": {
                    "x-litellm-api-key": f"Bearer {user_key}"
                }
            }
        }
    }

    agent_prompt = (
        f"请帮我安装 {server_data['name']} MCP 服务。\n\n"
    )

    tools = server_data.get("tools") or []
    tools_info = [{"name": t["display_name"] or t["tool_name"], "description": t.get("description", "")} for t in tools]

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "name": server_data["name"],
            "description": server_data.get("description", ""),
            "agent_prompt": agent_prompt,
            "config": config,
            "instructions": server_data.get("instructions", ""),
            "documentation_url": server_data.get("documentation_url", ""),
            "tools": tools_info,
        }
    }


@router.post("/servers/{server_id}/refresh-tools", summary="刷新 MCP 工具列表")
async def refresh_tools(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:update")),
):
    try:
        tools = await mcp_service.refresh_tools(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "工具列表刷新成功", "data": tools}


@router.get("/servers/{server_id}/tools")
async def get_tools(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:read")),
):
    try:
        tools = await mcp_service.get_tools(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return {"code": 200, "message": "ok", "data": tools}


@router.put("/tools/{tool_id}/billing", summary="更新 MCP 工具计费")
async def update_tool_billing(
    tool_id: int,
    req: UpdateToolBillingRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:update")),
):
    try:
        data = await mcp_service.update_tool_billing(
            session,
            tool_id,
            billing_type=req.billing_type,
            internal_cost_per_call=req.internal_cost_per_call,
            external_cost_per_call=req.external_cost_per_call,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Tool 不存在")
    return {"code": 200, "message": "工具计费配置更新成功", "data": data}


@router.post("/servers/{server_id}/health-check", summary="MCP Server 健康检查")
async def health_check(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:update")),
):
    try:
        data = await mcp_service.health_check_server(session, server_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return {"code": 200, "message": "健康检查完成", "data": data}


# ─── Categories ──────────────────────────────────────────────────────────────


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:read")),
):
    data = await mcp_service.list_categories(session)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/categories", summary="创建 MCP 分类")
async def create_category(
    req: CreateCategoryRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:create")),
):
    try:
        data = await mcp_service.create_category(
            session, name=req.name, description=req.description, sort_order=req.sort_order
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "分类创建成功", "data": data}


@router.delete("/categories/{category_id}", summary="删除 MCP 分类")
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("mcp:delete")),
):
    try:
        await mcp_service.delete_category(session, category_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"code": 200, "message": "分类删除成功", "data": None}
