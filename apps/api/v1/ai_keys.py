from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, get_current_user, require_permission
from exceptions import NotFoundError, ConflictError, ValidationError
from services import ai_key_service
from services import litellm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-keys", tags=["ai-keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    key_type: str = Field(..., pattern=r"^(personal_main|personal_scene|dept_shared|project_shared)$")
    owner_type: str = Field(..., pattern=r"^(user|department|project)$")
    owner_id: int
    description: str = Field("", max_length=500)
    tags: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    budget_limit: Decimal | None = None
    budget_hard_limit: bool = True
    duration: str | None = None


class UpdateKeyRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    models: list[str] | None = None
    budget_limit: Decimal | None = None
    budget_hard_limit: bool | None = None
    budget_type: str | None = Field(None, pattern=r"^(money|count)$")


class BatchUpdateRequest(BaseModel):
    key_ids: list[int] = Field(..., min_length=1)
    models: list[str] | None = None
    budget_limit: Decimal | None = None
    budget_hard_limit: bool | None = None
    budget_type: str | None = Field(None, pattern=r"^(money|count)$")


class ModelLimitItem(BaseModel):
    model_id: int
    tpm: int | None = Field(None, ge=1)
    rpm: int | None = Field(None, ge=1)
    max_tokens: int | None = Field(None, ge=1)
    max_calls: int | None = Field(None, ge=1)


class SetModelLimitsRequest(BaseModel):
    limits: list[ModelLimitItem]


@router.get("")
async def list_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_type: str | None = Query(None),
    owner_id: int | None = Query(None),
    key_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await ai_key_service.list_keys(session, page, page_size, owner_type, owner_id, key_type)
    return {"code": 200, "message": "ok", "data": result}


@router.post("")
async def create_key(
    req: CreateKeyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.create_key(
            session,
            name=req.name,
            key_type=req.key_type,
            owner_type=req.owner_type,
            owner_id=req.owner_id,
            created_by=current_user["id"],
            description=req.description,
            tags=req.tags,
            models=req.models,
            budget_limit=req.budget_limit,
            budget_hard_limit=req.budget_hard_limit,
            duration=req.duration,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "message": "ok", "data": key}


@router.get("/my")
async def get_my_keys(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await ai_key_service.get_my_keys(session, current_user["id"])
    return {"code": 200, "message": "ok", "data": result}


@router.get("/identity")
async def list_identity(
    tab: str = Query(..., pattern=r"^(user|department|project)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        result = await ai_key_service.list_identity(session, tab, page, page_size, keyword)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "ok", "data": result}


@router.get("/{key_id}/model-limits")
async def get_model_limits(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        limits = await ai_key_service.get_model_limits(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": limits}


@router.put("/{key_id}/model-limits")
async def set_model_limits(
    key_id: int,
    req: SetModelLimitsRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        limits = await ai_key_service.set_model_limits(
            session, key_id, [item.model_dump() for item in req.limits]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "ok", "data": limits}


@router.delete("/{key_id}/model-limits/{model_id}")
async def delete_model_limit(
    key_id: int,
    model_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await ai_key_service.delete_model_limit(session, key_id, model_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="限制记录不存在")
    return {"code": 200, "message": "ok", "data": None}


@router.get("/{key_id}")
async def get_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        key = await ai_key_service.get_key_by_id(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": key}


@router.put("/{key_id}")
async def update_key(
    key_id: int,
    req: UpdateKeyRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.update_key(
            session, key_id,
            name=req.name,
            description=req.description,
            tags=req.tags,
            models=req.models,
            budget_limit=req.budget_limit,
            budget_hard_limit=req.budget_hard_limit,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": key}


@router.put("/{key_id}/toggle")
async def toggle_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.toggle_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": key}


@router.delete("/{key_id}")
async def delete_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await ai_key_service.delete_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": None}


@router.get("/available-models")
async def get_available_models(
    _: dict = Depends(require_permission("user:read")),
):
    try:
        models = await litellm_client.list_models()
        model_names = [m.get("model_name", m.get("model_info", {}).get("id", "")) for m in models if m]
        model_names = sorted(set(n for n in model_names if n))
    except litellm_client.LiteLLMError:
        logger.warning("failed to fetch models from litellm")
        model_names = []
    return {"code": 200, "message": "ok", "data": model_names}


@router.put("/batch")
async def batch_update_keys(
    req: BatchUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    results = []
    for key_id in req.key_ids:
        try:
            key = await ai_key_service.update_key(
                session, key_id,
                models=req.models,
                budget_limit=req.budget_limit,
                budget_hard_limit=req.budget_hard_limit,
            )
            results.append(key)
        except NotFoundError:
            pass
    return {"code": 200, "message": "ok", "data": {"updated": len(results)}}
