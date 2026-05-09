from fastapi import APIRouter, Depends, HTTPException, Query

from core.deps import require_permission
from exceptions import NotFoundError, ConflictError
from models.user import (
    CreateUserRequest,
    UpdateUserRequest,
    ResetPasswordRequest,
    UpdateUserRolesRequest,
    UpdateUserOrganizationsRequest,
)
from services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=64),
    _: dict = Depends(require_permission("user:read")),
):
    result = await user_service.list_users(page, page_size, keyword)
    return {"code": 200, "message": "ok", "data": result}


@router.post("")
async def create_user(
    req: CreateUserRequest,
    _: dict = Depends(require_permission("user:create")),
):
    try:
        user = await user_service.create_user(req.username, req.email, req.password, req.is_active)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": user}


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    _: dict = Depends(require_permission("user:read")),
):
    try:
        user = await user_service.get_user_by_id(user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": user}


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    req: UpdateUserRequest,
    _: dict = Depends(require_permission("user:update")),
):
    try:
        user = await user_service.update_user(user_id, req.email, req.is_active)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": user}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await user_service.delete_user(user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.put("/{user_id}/password")
async def reset_user_password(
    user_id: int,
    req: ResetPasswordRequest,
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await user_service.reset_password(user_id, req.new_password)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": None}


@router.put("/{user_id}/roles")
async def update_user_roles(
    user_id: int,
    req: UpdateUserRolesRequest,
    _: dict = Depends(require_permission("role:update")),
):
    try:
        await user_service.update_user_roles(user_id, req.role_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": None}


@router.put("/{user_id}/organizations")
async def update_user_organizations(
    user_id: int,
    req: UpdateUserOrganizationsRequest,
    _: dict = Depends(require_permission("organization:update")),
):
    try:
        await user_service.update_user_organizations(user_id, req.organization_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": None}
