from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError
from services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=2000)
    expires_at: datetime | None = Field(default=None)


class UpdateApiKeyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)


@router.post("", summary="创建 API Key")
async def create_api_key(
    req: CreateApiKeyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("api_key:create")),
):
    api_key, _raw_key = await api_key_service.create_api_key(
        session,
        name=req.name,
        description=req.description,
        expires_at=req.expires_at,
        created_by=current_user["id"],
    )
    return {
        "code": 200,
        "message": "API Key 创建成功",
        "data": api_key,
    }


@router.get("")
async def list_api_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=128),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("api_key:read")),
):
    result = await api_key_service.list_api_keys(session, page, page_size, keyword)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/{key_id}")
async def get_api_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("api_key:read")),
):
    try:
        api_key = await api_key_service.get_api_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return {"code": 200, "message": "ok", "data": api_key}


@router.put("/{key_id}", summary="更新 API Key")
async def update_api_key(
    key_id: int,
    req: UpdateApiKeyRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("api_key:update")),
):
    try:
        api_key = await api_key_service.update_api_key(
            session,
            key_id,
            name=req.name,
            description=req.description,
            is_active=req.is_active,
            expires_at=req.expires_at,
            expires_at_provided="expires_at" in req.model_fields_set,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return {"code": 200, "message": "API Key 更新成功", "data": api_key}


@router.delete("/{key_id}", summary="删除 API Key")
async def delete_api_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("api_key:delete")),
):
    try:
        await api_key_service.delete_api_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return {"code": 200, "message": "API Key 删除成功", "data": None}
