from fastapi import APIRouter, Depends, HTTPException, Query

from core.deps import require_permission
from exceptions import NotFoundError, ConflictError
from models.organization import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    UpdateOrgManagersRequest,
)
from services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("")
async def list_organizations(
    type: str | None = Query(None, pattern="^(department|group)$"),
    is_active: bool | None = None,
    _: dict = Depends(require_permission("organization:read")),
):
    result = await organization_service.list_organizations(type, is_active)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/tree")
async def get_organization_tree(
    _: dict = Depends(require_permission("organization:read")),
):
    tree = await organization_service.get_organization_tree()
    return {"code": 200, "message": "ok", "data": tree}


@router.post("")
async def create_organization(
    req: CreateOrganizationRequest,
    _: dict = Depends(require_permission("organization:create")),
):
    try:
        org = await organization_service.create_organization(
            req.name, req.type, req.parent_id, req.description, req.sort_order
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": org}


@router.put("/{org_id}")
async def update_organization(
    org_id: int,
    req: UpdateOrganizationRequest,
    _: dict = Depends(require_permission("organization:update")),
):
    try:
        org = await organization_service.update_organization(
            org_id, req.name, req.description, req.sort_order, req.is_active
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="组织不存在")
    return {"code": 200, "message": "ok", "data": org}


@router.put("/{org_id}/managers")
async def update_org_managers(
    org_id: int,
    req: UpdateOrgManagersRequest,
    _: dict = Depends(require_permission("organization:update")),
):
    try:
        org = await organization_service.update_org_managers(org_id, req.manager_user_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="组织不存在")
    return {"code": 200, "message": "ok", "data": org}


@router.delete("/{org_id}")
async def delete_organization(
    org_id: int,
    _: dict = Depends(require_permission("organization:delete")),
):
    try:
        await organization_service.delete_organization(org_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="组织不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.get("/{org_id}/members")
async def get_organization_members(
    org_id: int,
    _: dict = Depends(require_permission("organization:read")),
):
    try:
        members = await organization_service.get_organization_members(org_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="组织不存在")
    return {"code": 200, "message": "ok", "data": members}
