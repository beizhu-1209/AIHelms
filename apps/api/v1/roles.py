from fastapi import APIRouter, Depends, HTTPException

from core.deps import require_permission
from exceptions import NotFoundError, ConflictError
from models.role import CreateRoleRequest, UpdateRoleRequest, UpdateRolePermissionsRequest
from services import role_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("")
async def list_roles(
    _: dict = Depends(require_permission("role:read")),
):
    roles = await role_service.list_roles()
    return {"code": 200, "message": "ok", "data": roles}


@router.post("")
async def create_role(
    req: CreateRoleRequest,
    _: dict = Depends(require_permission("role:create")),
):
    try:
        role = await role_service.create_role(req.name, req.display_name, req.description)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": role}


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    req: UpdateRoleRequest,
    _: dict = Depends(require_permission("role:update")),
):
    try:
        role = await role_service.update_role(role_id, req.display_name, req.description)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="角色不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": role}


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    _: dict = Depends(require_permission("role:delete")),
):
    try:
        await role_service.delete_role(role_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="角色不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.put("/{role_id}/permissions")
async def update_role_permissions(
    role_id: int,
    req: UpdateRolePermissionsRequest,
    _: dict = Depends(require_permission("role:update")),
):
    try:
        role = await role_service.update_role_permissions(role_id, req.permission_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="角色不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": role}


@router.get("/permissions")
async def list_permissions(
    _: dict = Depends(require_permission("permission:read")),
):
    permissions = await role_service.list_permissions()
    return {"code": 200, "message": "ok", "data": permissions}
