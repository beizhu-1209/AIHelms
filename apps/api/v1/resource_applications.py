from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db, require_permission
from exceptions import ConflictError, NotFoundError, ValidationError
from services import resource_application_service

router = APIRouter(prefix="/resource-applications", tags=["resource-applications"])


class CreateApplicationRequest(BaseModel):
    resource_type: str = Field(..., pattern=r"^(model|mcp|skill|agent)$")
    resource_id: int
    reason: str = Field("", max_length=500)
    request_config: dict | None = None


class ApproveApplicationRequest(BaseModel):
    approval_config: dict | None = None
    review_notes: str = Field("", max_length=500)


class RejectApplicationRequest(BaseModel):
    review_notes: str = Field("", max_length=500)


class BatchApproveRequest(BaseModel):
    app_ids: list[int] = Field(..., min_length=1, max_length=200)
    approval_config: dict | None = None
    review_notes: str = Field("", max_length=500)


class BatchRejectRequest(BaseModel):
    app_ids: list[int] = Field(..., min_length=1, max_length=200)
    review_notes: str = Field("", max_length=500)


@router.get("")
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: int | None = None,
    resource_type: str | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("resource_application:read")),
):
    data = await resource_application_service.list_applications(
        session, page, page_size, user_id, resource_type, status
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/my")
async def list_my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    resource_type: str | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List current user's own resource applications."""
    data = await resource_application_service.list_applications(
        session, page, page_size, current_user["id"], resource_type, status
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/{app_id}")
async def get_application(
    app_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("resource_application:read")),
):
    try:
        data = await resource_application_service.get_application(session, app_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="申请不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.post("", summary="提交资源申请")
async def create_application(
    req: CreateApplicationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        data = await resource_application_service.create_application(
            session,
            user_id=current_user["id"],
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            reason=req.reason,
            request_config=req.request_config,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "申请提交成功", "data": data}


@router.put("/{app_id}/approve", summary="审批通过资源申请")
async def approve_application(
    app_id: int,
    req: ApproveApplicationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("resource_application:approve")),
):
    try:
        data = await resource_application_service.approve_application(
            session,
            app_id=app_id,
            reviewer_id=current_user["id"],
            approval_config=req.approval_config,
            review_notes=req.review_notes,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="申请不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "申请已批准", "data": data}


@router.put("/{app_id}/reject", summary="驳回资源申请")
async def reject_application(
    app_id: int,
    req: RejectApplicationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("resource_application:approve")),
):
    try:
        data = await resource_application_service.reject_application(
            session,
            app_id=app_id,
            reviewer_id=current_user["id"],
            review_notes=req.review_notes,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="申请不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "申请已拒绝", "data": data}


@router.put("/batch-approve", summary="批量审批资源申请")
async def batch_approve_applications(
    req: BatchApproveRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("resource_application:approve")),
):
    data = await resource_application_service.batch_approve_applications(
        session,
        app_ids=req.app_ids,
        reviewer_id=current_user["id"],
        approval_config=req.approval_config,
        review_notes=req.review_notes,
    )
    return {"code": 200, "message": "批量审批完成", "data": data}


@router.put("/batch-reject", summary="批量驳回资源申请")
async def batch_reject_applications(
    req: BatchRejectRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("resource_application:approve")),
):
    data = await resource_application_service.batch_reject_applications(
        session,
        app_ids=req.app_ids,
        reviewer_id=current_user["id"],
        review_notes=req.review_notes,
    )
    return {"code": 200, "message": "批量驳回完成", "data": data}
