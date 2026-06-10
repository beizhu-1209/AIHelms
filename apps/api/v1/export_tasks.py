from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from services import export_task_service

router = APIRouter(prefix="/export-tasks", tags=["资源审计"])


class CreateExportTaskRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=50)
    export_type: str = Field(..., min_length=1, max_length=80)
    task_name: str = Field(default="", max_length=200)
    params: dict[str, object] = Field(default_factory=dict)


class CleanupExportTaskRequest(BaseModel):
    retention_days: int = Field(default=7, ge=1, le=365)


@router.get("")
async def list_export_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    data = await export_task_service.list_export_tasks(
        session, page=page, page_size=page_size, source=source, status=status
    )
    return {"code": 200, "message": "ok", "data": data}


@router.post("", summary="创建导出任务")
async def create_export_task(
    payload: CreateExportTaskRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("usage_log:read")),
):
    try:
        data = await export_task_service.create_export_task(
            session,
            source=payload.source,
            export_type=payload.export_type,
            params=payload.params,
            current_user=current_user,
            task_name=payload.task_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": 200, "message": "导出任务已创建", "data": data}


@router.post("/cleanup", summary="清理导出任务")
async def cleanup_export_tasks(
    payload: CleanupExportTaskRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    try:
        data = await export_task_service.cleanup_export_tasks(
            session, retention_days=payload.retention_days
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": 200, "message": "导出任务已清理", "data": data}


@router.post("/{task_id}/cancel", summary="取消导出任务")
async def cancel_export_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    try:
        data = await export_task_service.cancel_export_task(session, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": 200, "message": "导出任务已取消", "data": data}


@router.post("/{task_id}/retry", summary="重试导出任务")
async def retry_export_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("usage_log:read")),
):
    try:
        data = await export_task_service.retry_export_task(session, task_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": 200, "message": "导出任务已重新提交", "data": data}


@router.get("/{task_id}/download")
async def download_export_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    task = await export_task_service.get_export_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="导出任务不存在")
    if task.status != "success" or not task.file_path or not task.file_name:
        raise HTTPException(status_code=400, detail="导出文件尚未生成")
    file_path = export_task_service.resolve_export_file_path(task)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在")
    return FileResponse(
        file_path,
        media_type="text/csv; charset=utf-8",
        filename=task.file_name,
    )
