from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from models.user import (
    CreateUserRequest,
    UpdateUserRequest,
    ResetPasswordRequest,
    UpdateUserRolesRequest,
    UpdateUserDepartmentsRequest,
    UpdateUserProjectsRequest,
)
from services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=64),
    is_admin: bool | None = Query(None),
    is_active: bool | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await user_service.list_users(session, page, page_size, keyword, is_admin, is_active)
    return {"code": 200, "message": "ok", "data": result}


@router.post("", summary="创建用户")
async def create_user(
    req: CreateUserRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:create")),
):
    try:
        user = await user_service.create_user(
            session,
            username=req.username,
            email=req.email,
            password=req.password,
            phone=req.phone,
            display_name=req.display_name,
            position=req.position,
            avatar=req.avatar,
            is_active=req.is_active,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "用户创建成功", "data": user}


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        user = await user_service.get_user_by_id(session, user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": user}


@router.put("/{user_id}", summary="更新用户")
async def update_user(
    user_id: int,
    req: UpdateUserRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        user = await user_service.update_user(
            session, user_id,
            email=req.email,
            phone=req.phone,
            display_name=req.display_name,
            position=req.position,
            avatar=req.avatar,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "用户更新成功", "data": user}


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await user_service.delete_user(session, user_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "用户删除成功", "data": None}


@router.put("/{user_id}/password", summary="重置用户密码")
async def reset_user_password(
    user_id: int,
    req: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await user_service.reset_password(session, user_id, req.new_password)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "密码重置成功", "data": None}


@router.put("/{user_id}/roles", summary="更新用户角色")
async def update_user_roles(
    user_id: int,
    req: UpdateUserRolesRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("role:update")),
):
    try:
        await user_service.update_user_roles(session, user_id, req.role_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "角色更新成功", "data": None}


@router.put("/{user_id}/departments", summary="更新用户部门")
async def update_user_departments(
    user_id: int,
    req: UpdateUserDepartmentsRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await user_service.update_user_departments(session, user_id, req.department_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "部门更新成功", "data": None}


@router.put("/{user_id}/projects", summary="更新用户项目")
async def update_user_projects(
    user_id: int,
    req: UpdateUserProjectsRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await user_service.update_user_projects(session, user_id, req.project_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "项目更新成功", "data": None}
