from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from models.department import (
    CreateDepartmentRequest,
    UpdateDepartmentRequest,
    UpdateDepartmentManagersRequest,
    DepartmentMemberRequest,
)
from services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/tree")
async def get_department_tree(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:read")),
):
    tree = await department_service.get_department_tree(session)
    return {"code": 200, "message": "ok", "data": tree}


@router.get("/{dept_id}")
async def get_department(
    dept_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:read")),
):
    try:
        dept = await department_service.get_department_by_id(session, dept_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部门不存在")
    return {"code": 200, "message": "ok", "data": dept}


@router.post("")
async def create_department(
    req: CreateDepartmentRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:create")),
):
    try:
        dept = await department_service.create_department(
            session, name=req.name, parent_id=req.parent_id, description=req.description
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="父部门不存在")
    return {"code": 200, "message": "ok", "data": dept}


@router.put("/{dept_id}")
async def update_department(
    dept_id: int,
    req: UpdateDepartmentRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:update")),
):
    try:
        dept = await department_service.update_department(
            session, dept_id, name=req.name, description=req.description, sort_order=req.sort_order
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部门不存在")
    return {"code": 200, "message": "ok", "data": dept}


@router.delete("/{dept_id}")
async def delete_department(
    dept_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:delete")),
):
    try:
        await department_service.delete_department(session, dept_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部门不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.get("/{dept_id}/members")
async def get_department_members(
    dept_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:read")),
):
    try:
        members = await department_service.get_department_members(session, dept_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部门不存在")
    return {"code": 200, "message": "ok", "data": members}


@router.post("/{dept_id}/members")
async def add_department_member(
    dept_id: int,
    req: DepartmentMemberRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:update")),
):
    try:
        await department_service.add_department_member(session, dept_id, req.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.delete("/{dept_id}/members/{user_id}")
async def remove_department_member(
    dept_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:update")),
):
    try:
        await department_service.remove_department_member(session, dept_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}


@router.put("/{dept_id}/managers")
async def update_department_managers(
    dept_id: int,
    req: UpdateDepartmentManagersRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("department:update")),
):
    try:
        await department_service.update_department_managers(session, dept_id, req.manager_user_ids)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="部门不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "ok", "data": None}
