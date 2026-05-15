from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from services import credential_service, model_service
from services import litellm_client

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CreateCredentialRequest(BaseModel):
    credential_name: str = Field(..., min_length=1, max_length=128)
    credential_values: dict = Field(..., description="认证信息（api_key, api_base 等）")
    provider_id: int = Field(..., description="归属供应商 ID")
    credential_info: dict | None = None


class UpdateCredentialRequest(BaseModel):
    credential_values: dict | None = None
    provider_id: int | None = None
    credential_info: dict | None = None
    is_active: bool | None = None


@router.get("")
async def list_credentials(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    provider_id: int | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await credential_service.list_credentials(session, page, page_size, provider_id)
    return {"code": 200, "message": "ok", "data": result}


@router.post("")
async def create_credential(
    req: CreateCredentialRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        credential = await credential_service.create_credential(
            session,
            credential_name=req.credential_name,
            credential_values=req.credential_values,
            provider_id=req.provider_id,
            credential_info=req.credential_info,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "凭证添加成功", "data": credential}


@router.get("/provider-fields")
async def get_provider_fields(
    _: dict = Depends(require_permission("user:read")),
):
    fields = await litellm_client.get_provider_fields()
    return {"code": 200, "message": "ok", "data": fields}


@router.get("/{credential_id}")
async def get_credential(
    credential_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        credential = await credential_service.get_credential_by_id(session, credential_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return {"code": 200, "message": "ok", "data": credential}


@router.put("/{credential_id}")
async def update_credential(
    credential_id: int,
    req: UpdateCredentialRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        credential = await credential_service.update_credential(
            session, credential_id,
            credential_values=req.credential_values,
            provider_id=req.provider_id,
            credential_info=req.credential_info,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="凭证不存在")
    return {"code": 200, "message": "凭证更新成功", "data": credential}


@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await credential_service.delete_credential(session, credential_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="凭证不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "凭证删除成功", "data": None}


@router.get("/{credential_id}/models")
async def get_credential_models(
    credential_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    """获取使用该凭证的模型 ID 列表"""
    model_ids = await model_service.get_model_ids_by_credential_ids(
        session, [credential_id]
    )
    return {"code": 200, "message": "ok", "data": model_ids}


@router.get("/by-provider/{provider_id}/models")
async def get_provider_models(
    provider_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    """获取该供应商所有凭证关联的模型 ID 列表"""
    creds = await credential_service.list_credentials(session, 1, 100, provider_id)
    cred_ids = [item["id"] for item in creds["items"]]
    model_ids = await model_service.get_model_ids_by_credential_ids(session, cred_ids)
    return {"code": 200, "message": "ok", "data": model_ids}
