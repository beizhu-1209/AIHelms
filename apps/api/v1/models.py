from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from services import model_service

router = APIRouter(prefix="/models", tags=["models"])


class CreateModelRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    model_id: str = Field(..., min_length=1, max_length=128)
    category: str = Field("chat", max_length=50)
    capabilities: list[str] = Field(default_factory=list)
    description: str = Field("", max_length=500)


class UpdateModelRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    category: str | None = None
    capabilities: list[str] | None = None
    description: str | None = None
    is_active: bool | None = None


class CreateDeploymentRequest(BaseModel):
    litellm_params: dict = Field(..., description="完整 litellm_params（必须包含 model 字段）")
    credential_id: int | None = None
    deploy_name: str = ""
    billing_type: str = Field("token", pattern=r"^(token|per_call|monthly_quota)$")
    cost_per_call: float | None = None
    monthly_call_quota: int | None = None
    model_info: dict | None = None


class UpdateDeploymentRequest(BaseModel):
    litellm_params: dict | None = None
    credential_id: int | None = None
    deploy_name: str | None = None
    billing_type: str | None = Field(None, pattern=r"^(token|per_call|monthly_quota)$")
    cost_per_call: float | None = None
    monthly_call_quota: int | None = None
    model_info: dict | None = None
    is_active: bool | None = None


class CreateAccessGroupRequest(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    model_ids: list[str] = Field(default_factory=list)


class UpdateAccessGroupRequest(BaseModel):
    group_name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    model_ids: list[str] | None = None
    is_active: bool | None = None


class UpdateRouterSettingsRequest(BaseModel):
    routing_strategy: str | None = None
    fallbacks: list | None = None
    allowed_fails: int | None = Field(None, ge=1)
    cooldown_time: int | None = Field(None, ge=1)
    num_retries: int | None = Field(None, ge=0)
    timeout: int | None = Field(None, ge=1)
    config: dict | None = None


# --- Models ---


@router.get("")
async def list_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    category: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await model_service.list_models(session, page, page_size, category)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/active")
async def get_active_models(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    models = await model_service.get_all_active_models(session)
    return {"code": 200, "message": "ok", "data": models}


@router.post("")
async def create_model(
    req: CreateModelRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        model = await model_service.create_model(
            session,
            name=req.name,
            model_id=req.model_id,
            category=req.category,
            capabilities=req.capabilities,
            description=req.description,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "模型创建成功", "data": model}


@router.get("/{model_id}")
async def get_model(
    model_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        model = await model_service.get_model_by_id(session, model_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"code": 200, "message": "ok", "data": model}


@router.put("/{model_id}")
async def update_model(
    model_id: int,
    req: UpdateModelRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        model = await model_service.update_model(
            session, model_id,
            name=req.name,
            category=req.category,
            capabilities=req.capabilities,
            description=req.description,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"code": 200, "message": "模型更新成功", "data": model}


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await model_service.delete_model(session, model_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"code": 200, "message": "模型删除成功", "data": None}


# --- Deployments ---


@router.post("/{model_id}/deployments")
async def create_deployment(
    model_id: int,
    req: CreateDeploymentRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    if "model" not in req.litellm_params:
        raise HTTPException(status_code=400, detail="litellm_params 必须包含 model 字段")
    try:
        deployment = await model_service.create_deployment(
            session, model_id,
            litellm_params=req.litellm_params,
            credential_id=req.credential_id,
            deploy_name=req.deploy_name,
            billing_type=req.billing_type,
            cost_per_call=req.cost_per_call,
            monthly_call_quota=req.monthly_call_quota,
            model_info=req.model_info,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "message": "渠道创建成功", "data": deployment}


@router.put("/{model_id}/deployments/{deployment_id}")
async def update_deployment(
    model_id: int,
    deployment_id: int,
    req: UpdateDeploymentRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        deployment = await model_service.update_deployment(
            session, deployment_id,
            litellm_params=req.litellm_params,
            credential_id=req.credential_id,
            deploy_name=req.deploy_name,
            billing_type=req.billing_type,
            cost_per_call=req.cost_per_call,
            monthly_call_quota=req.monthly_call_quota,
            model_info=req.model_info,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部署不存在")
    return {"code": 200, "message": "渠道更新成功", "data": deployment}


@router.delete("/{model_id}/deployments/{deployment_id}")
async def delete_deployment(
    model_id: int,
    deployment_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await model_service.delete_deployment(session, deployment_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部署不存在")
    return {"code": 200, "message": "渠道删除成功", "data": None}


# --- Access Groups ---


@router.get("/access-groups/list")
async def list_access_groups(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    groups = await model_service.list_access_groups(session)
    return {"code": 200, "message": "ok", "data": groups}


@router.post("/access-groups")
async def create_access_group(
    req: CreateAccessGroupRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        group = await model_service.create_access_group(
            session,
            group_name=req.group_name,
            description=req.description,
            model_ids=req.model_ids,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "访问组创建成功", "data": group}


@router.put("/access-groups/{group_id}")
async def update_access_group(
    group_id: int,
    req: UpdateAccessGroupRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        group = await model_service.update_access_group(
            session, group_id,
            group_name=req.group_name,
            description=req.description,
            model_ids=req.model_ids,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="访问组不存在")
    return {"code": 200, "message": "访问组更新成功", "data": group}


@router.delete("/access-groups/{group_id}")
async def delete_access_group(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await model_service.delete_access_group(session, group_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="访问组不存在")
    return {"code": 200, "message": "访问组删除成功", "data": None}


# --- Router Settings ---


@router.get("/router-settings/current")
async def get_router_settings(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    settings = await model_service.get_router_settings(session)
    return {"code": 200, "message": "ok", "data": settings}


@router.put("/router-settings/current")
async def update_router_settings(
    req: UpdateRouterSettingsRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    settings = await model_service.update_router_settings(
        session,
        routing_strategy=req.routing_strategy,
        fallbacks=req.fallbacks,
        allowed_fails=req.allowed_fails,
        cooldown_time=req.cooldown_time,
        num_retries=req.num_retries,
        timeout=req.timeout,
        config=req.config,
    )
    return {"code": 200, "message": "路由设置更新成功", "data": settings}
