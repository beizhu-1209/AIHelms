from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError
from services import usage_log_service

router = APIRouter(prefix="/usage-logs", tags=["usage-logs"])


# ───────── LLM ─────────

@router.get("/llm")
async def list_llm_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: int | None = Query(None),
    ai_key_id: int | None = Query(None),
    model: str | None = Query(None),
    provider: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.list_llm_logs(
        session,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        ai_key_id=ai_key_id,
        model=model,
        provider=provider,
        status=status,
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/llm/filters")
async def get_llm_log_filters(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.llm_filters(session)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/llm/{log_id}")
async def get_llm_log(
    log_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    try:
        log = await usage_log_service.get_llm_log(session, log_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="LLM 日志不存在")
    return {"code": 200, "message": "ok", "data": log}


# ───────── MCP ─────────

@router.get("/mcp")
async def list_mcp_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: int | None = Query(None),
    ai_key_id: int | None = Query(None),
    server_id: int | None = Query(None),
    tool_name: str | None = Query(None),
    status: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.list_mcp_logs(
        session,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        ai_key_id=ai_key_id,
        server_id=server_id,
        tool_name=tool_name,
        status=status,
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/mcp/filters")
async def get_mcp_log_filters(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.mcp_filters(session)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/mcp/{log_id}")
async def get_mcp_log(
    log_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    try:
        log = await usage_log_service.get_mcp_log(session, log_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="MCP 日志不存在")
    return {"code": 200, "message": "ok", "data": log}


# ───────── Skill ─────────

@router.get("/skill")
async def list_skill_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: int | None = Query(None),
    skill_id: int | None = Query(None),
    action: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.list_skill_logs(
        session,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        skill_id=skill_id,
        action=action,
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/skill/filters")
async def get_skill_log_filters(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.skill_filters(session)
    return {"code": 200, "message": "ok", "data": result}


# ───────── Agent ─────────

@router.get("/agent")
async def list_agent_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: int | None = Query(None),
    agent_id: int | None = Query(None),
    platform: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.list_agent_logs(
        session,
        page=page,
        page_size=page_size,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        agent_id=agent_id,
        platform=platform,
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/agent/filters")
async def get_agent_log_filters(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("usage_log:read")),
):
    result = await usage_log_service.agent_filters(session)
    return {"code": 200, "message": "ok", "data": result}
