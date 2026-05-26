from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from models.project import (
    CreateProjectRequest,
    UpdateProjectRequest,
    ProjectMemberRequest,
)
from services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", max_length=64),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:read")),
):
    result = await project_service.list_projects(session, page, page_size, keyword)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:read")),
):
    try:
        project = await project_service.get_project_by_id(session, project_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"code": 200, "message": "ok", "data": project}


@router.post("", summary="创建项目")
async def create_project(
    req: CreateProjectRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:create")),
):
    project = await project_service.create_project(session, name=req.name, description=req.description)
    return {"code": 200, "message": "项目创建成功", "data": project}


@router.put("/{project_id}", summary="更新项目")
async def update_project(
    project_id: int,
    req: UpdateProjectRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:update")),
):
    try:
        project = await project_service.update_project(
            session, project_id, name=req.name, description=req.description, is_active=req.is_active
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"code": 200, "message": "项目更新成功", "data": project}


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:delete")),
):
    try:
        await project_service.delete_project(session, project_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "项目删除成功", "data": None}


@router.get("/{project_id}/members")
async def get_project_members(
    project_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:read")),
):
    try:
        members = await project_service.get_project_members(session, project_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"code": 200, "message": "ok", "data": members}


@router.post("/{project_id}/members", summary="添加项目成员")
async def add_project_member(
    project_id: int,
    req: ProjectMemberRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:update")),
):
    try:
        await project_service.add_project_member(session, project_id, req.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "成员添加成功", "data": None}


@router.delete("/{project_id}/members/{user_id}", summary="移除项目成员")
async def remove_project_member(
    project_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("project:update")),
):
    try:
        await project_service.remove_project_member(session, project_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "message": "成员移除成功", "data": None}
