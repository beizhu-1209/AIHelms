from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, get_current_user, require_permission
from exceptions import NotFoundError, ConflictError
from services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    icon: str = ""
    description: str = Field("", max_length=2000)
    platform: str = Field(..., min_length=1, max_length=64)
    category: str = Field("general", max_length=50)
    department_id: int | None = None
    project_id: int | None = None
    cost_attribution: str = Field("owner", pattern=r"^(owner|user)$")
    ai_key_id: int | None = None
    chat_url: str = Field("", max_length=500)
    tags: list[str] = Field(default_factory=list)
    is_published: bool = False
    requires_approval: bool = False
    status: str = Field("online", pattern=r"^(online|offline|loading)$")


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    icon: str | None = None
    description: str | None = None
    platform: str | None = None
    category: str | None = None
    department_id: int | None = None
    project_id: int | None = None
    cost_attribution: str | None = Field(None, pattern=r"^(owner|user)$")
    ai_key_id: int | None = None
    chat_url: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None
    is_published: bool | None = None
    requires_approval: bool | None = None
    status: str | None = Field(None, pattern=r"^(online|offline|loading)$")


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field("", max_length=200)
    sort_order: int = 0


class CreatePlatformRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    label: str = Field("", max_length=64)
    description: str = Field("", max_length=200)
    sort_order: int = 0


class RecordUsageRequest(BaseModel):
    session_id: str = Field("", max_length=100)


# ─── Categories / Platforms ─────────────────────────────────────────────────


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:read")),
):
    data = await agent_service.list_categories(session)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/categories", summary="创建智能体分类")
async def create_category(
    req: CreateCategoryRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:create")),
):
    try:
        data = await agent_service.create_category(
            session, name=req.name, description=req.description, sort_order=req.sort_order
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "分类创建成功", "data": data}


@router.delete("/categories/{category_id}", summary="删除智能体分类")
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:delete")),
):
    try:
        await agent_service.delete_category(session, category_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"code": 200, "message": "分类删除成功", "data": None}


@router.get("/platforms")
async def list_platforms(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:read")),
):
    data = await agent_service.list_platforms(session)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/platforms", summary="创建智能体平台")
async def create_platform(
    req: CreatePlatformRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:create")),
):
    try:
        data = await agent_service.create_platform(
            session, name=req.name, label=req.label, description=req.description, sort_order=req.sort_order
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "平台创建成功", "data": data}


@router.delete("/platforms/{platform_id}", summary="删除智能体平台")
async def delete_platform(
    platform_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:delete")),
):
    try:
        await agent_service.delete_platform(session, platform_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="平台不存在")
    return {"code": 200, "message": "平台删除成功", "data": None}


# ─── Agent CRUD ──────────────────────────────────────────────────────────────


@router.get("")
async def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    platform: str | None = None,
    is_published: bool | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:read")),
):
    data = await agent_service.list_agents(session, page, page_size, category, platform, is_published)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/{agent_id}")
async def get_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:read")),
):
    try:
        data = await agent_service.get_agent(session, agent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.post("", summary="创建智能体")
async def create_agent(
    req: CreateAgentRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("agent:create")),
):
    data = await agent_service.create_agent(
        session,
        name=req.name,
        icon=req.icon,
        description=req.description,
        platform=req.platform,
        category=req.category,
        department_id=req.department_id,
        project_id=req.project_id,
        cost_attribution=req.cost_attribution,
        chat_url=req.chat_url,
        tags=req.tags,
        is_published=req.is_published,
        requires_approval=req.requires_approval,
        status=req.status,
        created_by=current_user["id"],
    )
    return {"code": 200, "message": "智能体创建成功", "data": data}


@router.put("/{agent_id}", summary="更新智能体")
async def update_agent(
    agent_id: int,
    req: UpdateAgentRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:update")),
):
    kwargs = req.model_dump(exclude_none=True)
    try:
        data = await agent_service.update_agent(session, agent_id, **kwargs)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"code": 200, "message": "智能体更新成功", "data": data}


@router.delete("/{agent_id}", summary="删除智能体")
async def delete_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:delete")),
):
    try:
        await agent_service.delete_agent(session, agent_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"code": 200, "message": "智能体删除成功", "data": None}


@router.get("/{agent_id}/resolve-key")
async def resolve_agent_key(
    agent_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取智能体的可用 Key。owner 模式返回绑定的场景 Key，user 模式返回当前用户的场景 Key。"""
    try:
        data = await agent_service.resolve_key(session, agent_id, current_user["id"])
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在或未绑定 Key")
    return {"code": 200, "message": "ok", "data": data}


# ─── Usage Logs ─────────────────────────────────────────────────────────────


@router.post("/{agent_id}/use", summary="记录智能体使用")
async def record_usage(
    agent_id: int,
    req: RecordUsageRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        data = await agent_service.record_usage(
            session, agent_id, current_user["id"], session_id=req.session_id
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"code": 200, "message": "使用记录已保存", "data": data}


@router.get("/{agent_id}/usage-logs")
async def list_usage_logs(
    agent_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: int | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("agent:read")),
):
    try:
        data = await agent_service.list_usage_logs(session, agent_id, page, page_size, user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="智能体不存在")
    return {"code": 200, "message": "ok", "data": data}
