import csv
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from celery_app import celery_app
from core.config import settings
from core.time_utils import fmt_local_time
from models.db import ExportTask
from repositories import export_task_repo
from services.export_task_builders import build_export_rows

EXPORT_RETENTION_DAYS = 7
SOURCE_OPTIONS = [
    {"key": "usage_logs", "label": "日志管理"},
    {"key": "efficiency", "label": "AI效能"},
    {"key": "resource_applications", "label": "审批记录"},
]
EXPORT_TYPE_OPTIONS = {
    "usage_logs": {"llm", "mcp", "skill", "agent"},
    "efficiency": {
        "overview_scope",
        "adoption_scope",
        "adoption_agents",
        "adoption_mcp",
        "adoption_skill",
        "adoption_unused_users",
        "cost_model",
        "cost_mcp",
        "cost_date",
        "cost_attribution",
        "cost_department",
        "cost_project",
        "budget_key",
        "budget_user",
        "budget_department",
        "budget_project",
        "health_model",
        "health_docker",
        "health_mcp",
    },
    "resource_applications": {"applications"},
}
EXPORT_RUNNING_TIMEOUT_MINUTES = 30
STATUS_OPTIONS = [
    {"key": "pending", "label": "等待中"},
    {"key": "running", "label": "处理中"},
    {"key": "success", "label": "完成"},
    {"key": "failed", "label": "失败"},
    {"key": "canceled", "label": "已取消"},
]

logger = logging.getLogger(__name__)
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _exports_dir() -> Path:
    configured = Path(settings.exports_storage_dir)
    if configured.is_absolute():
        return configured
    parts = configured.parts
    if parts and parts[0] == "..":
        return _project_root() / Path(*parts[1:])
    return _project_root() / configured


def _validate_export_type(source: str, export_type: str) -> None:
    if source not in EXPORT_TYPE_OPTIONS:
        raise ValueError("不支持的导出来源")
    if export_type not in EXPORT_TYPE_OPTIONS[source]:
        raise ValueError("不支持的导出类型")


def _is_path_under(base: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _stored_export_path(task: ExportTask) -> Path | None:
    exports_dir = _exports_dir()
    candidates: list[Path] = []
    if task.file_name:
        candidates.append(exports_dir / task.file_name)
    if task.file_path:
        raw = Path(task.file_path)
        candidates.append(raw if raw.is_absolute() else _project_root() / raw)
    for candidate in candidates:
        if _is_path_under(exports_dir, candidate) and candidate.exists():
            return candidate
    return None


def resolve_export_file_path(task: ExportTask) -> Path | None:
    return _stored_export_path(task)


def _serialize_task(task: ExportTask) -> dict:
    return {
        "id": task.id,
        "task_name": task.task_name,
        "source": task.source,
        "export_type": task.export_type,
        "status": task.status,
        "created_by": task.created_by_name,
        "created_at": _fmt_time(task.created_at),
        "started_at": _fmt_time(task.started_at),
        "finished_at": _fmt_time(task.finished_at),
        "canceled_at": _fmt_time(task.canceled_at),
        "file_name": task.file_name,
        "file_size": task.file_size,
        "row_count": task.row_count,
        "error_message": task.error_message,
        "retry_of_task_id": task.retry_of_task_id,
        "download_url": f"/api/v1/export-tasks/{task.id}/download" if task.status == "success" and task.file_name else None,
        "can_retry": task.status in {"failed", "canceled"},
        "can_cancel": task.status in {"pending", "running"},
    }


def _fmt_time(value: datetime | None) -> str | None:
    if not value:
        return None
    return fmt_local_time(value)


def _sanitize_csv_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip().startswith(CSV_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(header)
        writer.writerows(
            [[_sanitize_csv_cell(value) for value in row] for row in rows]
        )


async def list_export_tasks(
    session: AsyncSession,
    page: int,
    page_size: int,
    source: str | None = None,
    status: str | None = None,
) -> dict:
    total = await export_task_repo.count_all(session, source, status)
    tasks = await export_task_repo.find_all(session, page, page_size, source, status)
    return {
        "items": [_serialize_task(task) for task in tasks],
        "total": total,
        "page": page,
        "page_size": page_size,
        "sources": SOURCE_OPTIONS,
        "statuses": STATUS_OPTIONS,
        "retention_days": EXPORT_RETENTION_DAYS,
    }


async def create_export_task(
    session: AsyncSession,
    source: str,
    export_type: str,
    params: dict[str, object],
    current_user: dict,
    task_name: str = "",
    retry_of_task_id: int | None = None,
) -> dict:
    _validate_export_type(source, export_type)
    name = task_name or _default_task_name(source, export_type)
    task = ExportTask(
        task_name=name,
        source=source,
        export_type=export_type,
        status="pending",
        params=params,
        created_by_id=int(current_user["id"]),
        created_by_name=str(current_user.get("username", "")),
        retry_of_task_id=retry_of_task_id,
    )
    task = await export_task_repo.create(session, task)
    await session.commit()
    await session.refresh(task)
    celery_task = _enqueue_export_task(task.id)
    task.celery_task_id = celery_task.id
    await session.commit()
    await session.refresh(task)
    return _serialize_task(task)


def _enqueue_export_task(task_id: int):
    from tasks.export_task_tasks import generate_export_file

    return generate_export_file.delay(task_id)


async def process_export_task(session: AsyncSession, task_id: int) -> None:
    task = await export_task_repo.find_by_id(session, task_id)
    if not task or task.status not in {"pending", "running"}:
        return
    if task.cancel_requested:
        task.status = "canceled"
        task.canceled_at = _now()
        task.finished_at = _now()
        await session.commit()
        return
    task.status = "running"
    task.started_at = _now()
    task.error_message = ""
    await session.commit()

    file_path: Path | None = None
    try:
        header, rows = await build_export_rows(session, task.source, task.export_type, task.params or {})
        await session.refresh(task)
        if task.cancel_requested or task.status == "canceled":
            task.status = "canceled"
            task.canceled_at = _now()
            task.finished_at = _now()
            await session.commit()
            return
        safe_name = f"{task.source}-{task.export_type}-{task.id}-{uuid4().hex[:8]}.csv"
        file_path = _exports_dir() / safe_name
        _write_csv(file_path, header, rows)
        await session.refresh(task)
        if task.cancel_requested or task.status == "canceled":
            if file_path.exists():
                file_path.unlink()
            task.status = "canceled"
            task.canceled_at = _now()
            task.finished_at = _now()
            await session.commit()
            return
        task.status = "success"
        task.file_name = safe_name
        task.file_path = str(file_path)
        task.file_size = file_path.stat().st_size
        task.row_count = len(rows)
        task.finished_at = _now()
    except Exception:
        logger.exception(
            "export task failed: task_id=%s source=%s export_type=%s",
            task.id,
            task.source,
            task.export_type,
        )
        if file_path and file_path.exists():
            file_path.unlink()
        task.status = "failed"
        task.error_message = "导出失败，请检查筛选条件或联系管理员"
        task.finished_at = _now()
    await session.commit()


async def retry_export_task(
    session: AsyncSession, task_id: int, current_user: dict
) -> dict:
    task = await export_task_repo.find_by_id(session, task_id)
    if not task:
        raise ValueError("导出任务不存在")
    if task.status not in {"failed", "canceled"}:
        raise ValueError("只有失败或已取消的任务可以重试")
    return await create_export_task(
        session,
        task.source,
        task.export_type,
        task.params or {},
        current_user,
        task.task_name,
        retry_of_task_id=task.id,
    )


async def cancel_export_task(session: AsyncSession, task_id: int) -> dict:
    task = await export_task_repo.find_by_id(session, task_id)
    if not task:
        raise ValueError("导出任务不存在")
    if task.status not in {"pending", "running"}:
        raise ValueError("当前任务状态不可取消")
    task.cancel_requested = True
    task.status = "canceled"
    task.canceled_at = _now()
    task.finished_at = _now()
    if task.celery_task_id:
        celery_app.control.revoke(task.celery_task_id, terminate=False)
    await session.commit()
    await session.refresh(task)
    return _serialize_task(task)


async def cleanup_export_tasks(
    session: AsyncSession, retention_days: int = EXPORT_RETENTION_DAYS
) -> dict:
    if retention_days < 1:
        raise ValueError("保留天数不能小于 1 天")
    before = _now() - timedelta(days=retention_days)
    await fail_stale_running_tasks(session)
    tasks = await export_task_repo.find_cleanup_candidates(session, before)
    deleted_files = 0
    for task in tasks:
        if task.file_path:
            file_path = _stored_export_path(task)
            if file_path and file_path.exists():
                file_path.unlink()
                deleted_files += 1
        await session.delete(task)
    await session.commit()
    return {"deleted_tasks": len(tasks), "deleted_files": deleted_files, "retention_days": retention_days}


async def fail_stale_running_tasks(session: AsyncSession) -> int:
    deadline = _now() - timedelta(minutes=EXPORT_RUNNING_TIMEOUT_MINUTES)
    tasks = await export_task_repo.find_stale_running(session, deadline)
    for task in tasks:
        task.status = "failed"
        task.error_message = "导出任务执行超时，请重试"
        task.finished_at = _now()
    if tasks:
        await session.commit()
    return len(tasks)


async def get_export_task(session: AsyncSession, task_id: int) -> ExportTask | None:
    return await export_task_repo.find_by_id(session, task_id)


def _default_task_name(source: str, export_type: str) -> str:
    source_label = next((item["label"] for item in SOURCE_OPTIONS if item["key"] == source), source)
    return f"{source_label}-{export_type}"
