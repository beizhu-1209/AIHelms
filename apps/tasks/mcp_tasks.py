import asyncio
import logging
from datetime import datetime, timedelta, timezone

from celery_app import celery_app
from core.config import settings
from core.database import get_worker_session_factory
from models.db import McpCallLog, McpServer, McpTool, SyncState
from repositories import mcp_repo
from services import litellm_client
from services.litellm_client import LiteLLMError

# 复用 LLM 日志同步的批量参数、时区helper 和 SpendLogs 游标索引，避免两套配置
from tasks.llm_log_tasks import (
    SPEND_LOG_BATCH_SIZE,
    SPEND_LOG_MAX_BATCHES_PER_RUN,
    _as_utc_datetime,
    _ensure_spend_logs_cursor_index,
    _to_utc_naive,
)

logger = logging.getLogger(__name__)

# 复用 init.sql 已预置的 sync_state 键
MCP_SYNC_STATE_KEY = "mcp_logs"


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="mcp.sync_call_logs")
def sync_mcp_call_logs():
    _run_async(_sync_call_logs())


@celery_app.task(name="mcp.health_check_all")
def health_check_all_servers():
    _run_async(_health_check_all())


async def _sync_call_logs():
    try:
        from sqlalchemy import text

        async with get_worker_session_factory()() as session:
            await _ensure_spend_logs_cursor_index(session)
            await session.commit()

            now = datetime.now(timezone.utc)
            sync_state = await session.get(SyncState, MCP_SYNC_STATE_KEY)
            if sync_state is None:
                sync_state = SyncState(
                    key=MCP_SYNC_STATE_KEY,
                    last_sync_at=now - timedelta(hours=1),
                )
                session.add(sync_state)
                await session.flush()

            cursor_condition = (
                'AND (COALESCE("endTime", "startTime"), request_id) '
                "> (:last_time, :last_request_id) "
                if sync_state.last_request_id
                else 'AND COALESCE("endTime", "startTime") > :last_time '
            )
            query = text(
                'SELECT request_id, api_key, "user", model, spend, '
                '"startTime", "endTime", mcp_namespaced_tool_name, '
                "metadata, messages, response "
                'FROM public."LiteLLM_SpendLogs" '
                "WHERE mcp_namespaced_tool_name IS NOT NULL "
                "  AND mcp_namespaced_tool_name != '' "
                f"  {cursor_condition}"
                'ORDER BY COALESCE("endTime", "startTime") ASC, request_id ASC '
                "LIMIT :batch_size"
            )

            total_inserted = 0
            total_scanned = 0
            for _ in range(SPEND_LOG_MAX_BATCHES_PER_RUN):
                params = {
                    "last_time": _to_utc_naive(sync_state.last_sync_at),
                    "batch_size": SPEND_LOG_BATCH_SIZE,
                }
                if sync_state.last_request_id:
                    params["last_request_id"] = sync_state.last_request_id
                result = await session.execute(query, params)
                rows = result.fetchall()
                if not rows:
                    break

                previous_cursor = (
                    sync_state.last_sync_at,
                    sync_state.last_request_id or "",
                )
                next_cursor = _max_mcp_cursor(rows)
                if next_cursor is None or next_cursor <= previous_cursor:
                    logger.error(
                        "mcp log sync cursor did not advance, aborting run: "
                        "cursor=%s scanned=%d",
                        previous_cursor[0].isoformat(),
                        len(rows),
                    )
                    break

                total_inserted += await _insert_mcp_rows(session, rows)
                total_scanned += len(rows)
                sync_state.last_sync_at, sync_state.last_request_id = next_cursor
                await session.commit()

                if len(rows) < SPEND_LOG_BATCH_SIZE:
                    break

            await session.commit()
            if total_scanned:
                logger.info(
                    "synced %d mcp call logs (scanned %d)",
                    total_inserted,
                    total_scanned,
                )

    except Exception as e:
        logger.error("failed to sync mcp call logs: %s", str(e), exc_info=True)


def _max_mcp_cursor(rows) -> tuple[datetime, str] | None:
    """取本批最大的 (cursor_time, request_id) 复合游标，与 LLM 同步口径一致。"""
    max_cursor = None
    for row in rows:
        cursor_time = _as_utc_datetime(row[6]) or _as_utc_datetime(row[5])
        request_id = row[0]
        if not cursor_time or not request_id:
            continue
        candidate = (cursor_time, request_id)
        if max_cursor is None or candidate > max_cursor:
            max_cursor = candidate
    return max_cursor


async def _insert_mcp_rows(session, rows) -> int:
    from sqlalchemy import select, text

    servers_cache: dict[str, McpServer | None] = {}
    tools_cache: dict[str, McpTool | None] = {}
    call_counts: dict[int, int] = {}
    inserted_count = 0

    for row in rows:
        request_id = row[0]
        namespaced_tool = row[7] if len(row) > 7 else None
        if not namespaced_tool:
            continue

        existing = await session.execute(
            select(McpCallLog).where(McpCallLog.litellm_request_id == request_id)
        )
        if existing.scalar_one_or_none():
            continue

        server_name = (
            namespaced_tool.split("/")[0] if "/" in namespaced_tool
            else namespaced_tool.split("_")[0] if "_" in namespaced_tool
            else ""
        )
        tool_name = (
            namespaced_tool.split("/", 1)[1] if "/" in namespaced_tool
            else namespaced_tool.split("_", 1)[1] if "_" in namespaced_tool
            else namespaced_tool
        )

        if server_name not in servers_cache:
            server = await mcp_repo.find_server_by_name(session, server_name)
            servers_cache[server_name] = server
        server = servers_cache[server_name]

        server_id = server.id if server else 0

        # 通过 metadata.user_api_key_alias 关联平台 ai_key → user_id
        user_id = 0
        ai_key_id = None
        metadata_raw = row[8] if len(row) > 8 else None
        mcp_metadata_full = _parse_json(metadata_raw)
        key_alias = mcp_metadata_full.get("user_api_key_alias") or ""
        if key_alias:
            from repositories import ai_key_repo
            ai_key = await ai_key_repo.find_by_litellm_key_alias(session, key_alias)
            if ai_key:
                ai_key_id = ai_key.id
                user_id = ai_key.owner_id if ai_key.owner_type == "user" else 0

        internal_cost = 0.0
        external_cost = 0.0
        tool_obj = None
        if server:
            tool_cache_key = f"{server_id}:{tool_name}"
            if tool_cache_key not in tools_cache:
                tools = await mcp_repo.find_tools_by_server(session, server_id)
                tool_obj = next((t for t in tools if t.tool_name == tool_name), None)
                tools_cache[tool_cache_key] = tool_obj
            tool_obj = tools_cache[tool_cache_key]

            if tool_obj and tool_obj.billing_type:
                internal_cost = float(tool_obj.internal_cost_per_call or 0)
                external_cost = float(tool_obj.external_cost_per_call or 0)
            else:
                internal_cost = float(server.internal_cost_per_call or 0)
                external_cost = float(server.external_cost_per_call or 0)

        start = row[5]
        end = row[6] if len(row) > 6 else None
        duration_ms = None
        if start and end:
            try:
                duration_ms = int((end - start).total_seconds() * 1000)
            except (TypeError, AttributeError):
                pass

        # 从已解析的 metadata 获取 mcp_tool_call_metadata 作为完整请求信息
        mcp_metadata = mcp_metadata_full.get("mcp_tool_call_metadata", {})
        arguments = mcp_metadata.get("arguments", {})

        # request_args 存完整的 mcp_tool_call_metadata
        # 包含 name、arguments、server 等字段
        response_raw = row[10] if len(row) > 10 else None
        request_args = mcp_metadata if mcp_metadata else arguments
        response_full = _to_text(response_raw)
        response_summary = response_full[:500] if response_full else ""

        log = McpCallLog(
            user_id=user_id,
            server_id=server_id,
            tool_id=tool_obj.id if tool_obj else None,
            tool_name=tool_name,
            namespaced_tool_name=namespaced_tool,
            arguments=request_args if isinstance(request_args, dict) else {},
            request_args=request_args if isinstance(request_args, dict) else {},
            response_full=response_full,
            response_summary=response_summary,
            status="success",
            duration_ms=duration_ms,
            internal_cost=internal_cost,
            external_cost=external_cost,
            ai_key_id=ai_key_id,
            litellm_request_id=request_id,
            called_at=start or end or datetime.now(timezone.utc),
        )
        session.add(log)
        inserted_count += 1
        if server_id:
            call_counts[server_id] = call_counts.get(server_id, 0) + 1

    for sid, count in call_counts.items():
        await session.execute(
            text(
                "UPDATE aihelms.mcp_servers "
                "SET call_count = COALESCE(call_count, 0) + :count "
                "WHERE id = :server_id"
            ),
            {"count": count, "server_id": sid},
        )

    return inserted_count


def _parse_json(raw):
    """解析 LiteLLM 的 JSON 字符串字段，失败返回空 dict。"""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json
            return json.loads(raw)
        except (ValueError, TypeError):
            return {}
    return {}


def _to_text(raw) -> str:
    """LiteLLM 的 response 可能是 dict / list / str，统一转 JSON 字符串保存。"""
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw
    try:
        import json
        return json.dumps(raw, ensure_ascii=False)
    except (ValueError, TypeError):
        return str(raw)


async def _health_check_all():
    try:
        async with get_worker_session_factory()() as session:
            servers = await mcp_repo.find_all_servers(
                session, page=1, page_size=500, is_active=True
            )
            for server in servers:
                try:
                    await litellm_client.test_mcp_connection(
                        url=server.url,
                        transport=server.transport,
                        auth_type=(
                            server.auth_type
                            if server.auth_type != "none"
                            else None
                        ),
                        credentials=server.credentials if server.credentials else None,
                    )
                    server.status = "healthy"
                    server.health_check_error = None
                except LiteLLMError as e:
                    server.status = "unhealthy"
                    server.health_check_error = str(e)
                server.last_health_check = datetime.utcnow()
            await session.commit()
            logger.info("health checked %d mcp servers", len(servers))
    except Exception as e:
        logger.error("failed to health check mcp servers: %s", str(e), exc_info=True)


celery_app.conf.beat_schedule = {
    **getattr(celery_app.conf, "beat_schedule", {}),
    "mcp-sync-call-logs": {
        "task": "mcp.sync_call_logs",
        "schedule": settings.llm_log_sync_interval_minutes * 60,
    },
    "mcp-health-check-all": {
        "task": "mcp.health_check_all",
        "schedule": 600.0,
    },
}
