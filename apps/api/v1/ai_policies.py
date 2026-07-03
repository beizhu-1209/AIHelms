from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ValidationError
from services import ai_policies_service

router = APIRouter(prefix="/ai-policies", tags=["ai-policies"])


class UpdateAiPoliciesSettingsRequest(BaseModel):
    llm_review_enabled: bool = False
    llm_review_model_id: int | None = Field(None)


@router.get("/audits", summary="查询 AI Policies 审查任务")
async def list_audits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    audit_type: str | None = Query("skill"),
    skill_id: int | None = None,
    status: str | None = None,
    decision: str | None = None,
    q: str | None = None,
    finished_from: datetime | None = None,
    finished_to: datetime | None = None,
    unfinished: bool | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ai_policies:read")),
):
    data = await ai_policies_service.list_audits(
        session,
        page,
        page_size,
        audit_type,
        skill_id,
        status,
        decision,
        q,
        finished_from,
        finished_to,
        unfinished,
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/settings", summary="查询 AI Policies 配置")
async def get_settings(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ai_policies:read")),
):
    data = await ai_policies_service.get_settings(session)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/catalog", summary="查询 AI Policies 风险分类目录")
async def list_catalog(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ai_policies:read")),
):
    data = await ai_policies_service.list_catalog(session)
    return {"code": 200, "message": "ok", "data": data}


@router.put("/settings", summary="更新 LLM 审查引擎配置")
async def update_settings(
    req: UpdateAiPoliciesSettingsRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("ai_policies:config")),
):
    try:
        data = await ai_policies_service.update_settings(
            session,
            req.llm_review_enabled,
            req.llm_review_model_id,
            current_user,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "LLM 审查引擎配置已更新", "data": data}


@router.get("/audits/{audit_id}", summary="查询 AI Policies 审查报告")
async def get_audit(
    audit_id: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ai_policies:read")),
):
    try:
        data = await ai_policies_service.get_audit(session, audit_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="审查任务不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.get("/audits/{audit_id}/download", summary="下载 AI Policies 审查报告")
async def download_audit(
    audit_id: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("ai_policies:read")),
):
    try:
        content, filename, media_type = await ai_policies_service.get_audit_export(
            session, audit_id
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="审查任务不存在")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type=media_type, headers=headers)
