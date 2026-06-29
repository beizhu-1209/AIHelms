"""LLM 调用日志同步与清理。

从 LiteLLM 的 `public.LiteLLM_SpendLogs` 表增量拉取调用记录，
关联反查（user / ai_key / deployment），算 internal_cost，
落表到 `aihelms.llm_call_logs`，按 request_id 去重。
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from celery_app import celery_app
from core.config import settings
from core.database import get_worker_session_factory
from models.db import (
    AiKey,
    LlmCallLog,
    Model,
    ModelDeployment,
    SyncState,
    User,
)
from services.model_service import ANTHROPIC_MODEL_SUFFIX

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="llm_log.sync")
def sync_llm_logs() -> None:
    _run_async(_sync())


@celery_app.task(name="llm_log.cleanup")
def cleanup_llm_logs() -> None:
    _run_async(_cleanup())


@celery_app.task(name="llm_log.recalc_cost")
def recalc_llm_cost(batch_size: int = 1000) -> dict[str, int]:
    return _run_async(_recalc_cost(batch_size))


@celery_app.task(name="llm_log.reconcile")
def reconcile_llm_logs() -> None:
    _run_async(_reconcile())


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _parse_cache_tokens(metadata: dict) -> tuple[int, int]:
    usage_obj = metadata.get("usage_object") or {}
    if not isinstance(usage_obj, dict):
        return 0, 0

    details = usage_obj.get("prompt_tokens_details") or {}
    cache_read = 0
    if isinstance(details, dict):
        cache_read = _safe_int(details.get("cached_tokens"))
    if cache_read == 0:
        cache_read = _safe_int(usage_obj.get("cache_read_input_tokens"))
    cache_creation = _safe_int(usage_obj.get("cache_creation_input_tokens"))
    return cache_read, cache_creation


def _billable_prompt_tokens(
    prompt_tokens: int, cache_read: int, cache_creation: int
) -> int:
    return max(prompt_tokens - cache_read - cache_creation, 0)



def _to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _as_utc_datetime(value: datetime | None) -> datetime | None:
    if value and not value.tzinfo:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_json_object(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_payload_or_none(raw: object) -> dict | list | None:
    return raw if isinstance(raw, (dict, list)) else None


def _messages_from_payload(
    messages_raw: object, proxy_request_raw: object
) -> dict | list | None:
    if isinstance(messages_raw, (dict, list)) and messages_raw:
        return messages_raw
    proxy_request = _parse_json_object(proxy_request_raw)
    proxy_messages = proxy_request.get("messages")
    if isinstance(proxy_messages, list) and proxy_messages:
        return proxy_messages
    return None


def _max_spend_cursor_time(rows) -> datetime | None:
    max_cursor_time = None
    for row in rows:
        cursor_time = _as_utc_datetime(row[11]) or _as_utc_datetime(row[10])
        if cursor_time and (max_cursor_time is None or cursor_time > max_cursor_time):
            max_cursor_time = cursor_time
    return max_cursor_time


async def _ensure_spend_logs_cursor_index(session: AsyncSession) -> None:
    await session.execute(
        text(
            'CREATE INDEX IF NOT EXISTS "LiteLLM_SpendLogs_cursorTime_request_id_idx" '
            'ON public."LiteLLM_SpendLogs" '
            '(COALESCE("endTime", "startTime"), request_id)'
        )
    )


async def _spend_log_model_id_select(
    session: AsyncSession, table_alias: str = ""
) -> str:
    prefix = f"{table_alias}." if table_alias else ""
    if await _spend_logs_has_column(session, "model_id"):
        return f"{prefix}model_id AS spend_log_model_id"
    return "NULL AS spend_log_model_id"

async def _spend_logs_has_column(session: AsyncSession, column_name: str) -> bool:
    result = await session.execute(
        text(
            "SELECT 1 "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "  AND table_name = 'LiteLLM_SpendLogs' "
            "  AND column_name = :column_name "
            "LIMIT 1"
        ),
        {"column_name": column_name},
    )
    return result.scalar_one_or_none() is not None


async def _sync() -> None:
    """从 LiteLLM SpendLogs 增量拉取 LLM 调用记录。"""
    try:
        async with get_worker_session_factory()() as session:
            await _ensure_spend_logs_cursor_index(session)
            await session.commit()

            now = datetime.now(timezone.utc)
            sync_state = await session.get(SyncState, "llm_logs")
            if sync_state is None:
                sync_state = SyncState(
                    key="llm_logs",
                    last_sync_at=now - timedelta(hours=1),
                )
                session.add(sync_state)
                await session.flush()

            start_time = sync_state.last_sync_at - timedelta(minutes=10)
            start_time_naive = _to_utc_naive(start_time)
            spend_log_model_id_select = await _spend_log_model_id_select(session)
            result = await session.execute(
                text(
                    'SELECT request_id, api_key, "user", model, custom_llm_provider, '
                    "call_type, spend, total_tokens, prompt_tokens, completion_tokens, "
                    '"startTime", "endTime", "completionStartTime", '
                    "session_id, status, metadata, mcp_namespaced_tool_name, "
                    "messages, response, proxy_server_request, "
                    f"{spend_log_model_id_select} "
                    'FROM public."LiteLLM_SpendLogs" '
                    'WHERE COALESCE("endTime", "startTime") >= :start_time '
                    "  AND (mcp_namespaced_tool_name IS NULL "
                    "       OR mcp_namespaced_tool_name = '') "
                    "  AND COALESCE(call_type, '') NOT IN ("
                    "       'list_mcp_tools', 'list_mcp_tool', "
                    "       'mcp_list_tools', 'mcp_list_tool') "
                    'ORDER BY COALESCE("endTime", "startTime") ASC, request_id ASC '
                    "LIMIT 1000"
                ),
                {"start_time": start_time_naive},
            )
            rows = result.fetchall()

            if not rows:
                await session.commit()
                return

            inserted = await _upsert_spend_log_rows(session, rows)
            max_cursor_time = _max_spend_cursor_time(rows)
            if max_cursor_time:
                sync_state.last_sync_at = max_cursor_time
            await session.commit()
            logger.info("synced %d llm call logs (scanned %d)", inserted, len(rows))
    except Exception:  # noqa: BLE001
        logger.error("failed to sync llm call logs", exc_info=True)


async def _reconcile() -> None:
    """对账兜底同步近 30 天漏掉的 LLM 调用日志。"""
    try:
        async with get_worker_session_factory()() as session:
            await _ensure_spend_logs_cursor_index(session)
            await session.commit()

            start_time = datetime.now(timezone.utc) - timedelta(days=30)
            spend_log_model_id_select = await _spend_log_model_id_select(session, "s")
            result = await session.execute(
                text(
                    'SELECT s.request_id, s.api_key, s."user", s.model, '
                    's.custom_llm_provider, s.call_type, s.spend, s.total_tokens, '
                    's.prompt_tokens, s.completion_tokens, s."startTime", '
                    's."endTime", s."completionStartTime", s.session_id, '
                    's.status, s.metadata, s.mcp_namespaced_tool_name, '
                    's.messages, s.response, s.proxy_server_request, '
                    f'{spend_log_model_id_select} '
                    'FROM public."LiteLLM_SpendLogs" s '
                    'WHERE s."startTime" >= :start_time '
                    "  AND (s.mcp_namespaced_tool_name IS NULL "
                    "       OR s.mcp_namespaced_tool_name = '') "
                    "  AND COALESCE(s.call_type, '') NOT IN ("
                    "       'list_mcp_tools', 'list_mcp_tool', "
                    "       'mcp_list_tools', 'mcp_list_tool') "
                    "  AND NOT EXISTS ("
                    "       SELECT 1 FROM aihelms.llm_call_logs l "
                    "       WHERE l.request_id = s.request_id) "
                    'ORDER BY s."endTime" ASC, s.request_id ASC '
                    "LIMIT 1000"
                ),
                {"start_time": _to_utc_naive(start_time)},
            )
            rows = result.fetchall()
            if not rows:
                return

            inserted = await _upsert_spend_log_rows(session, rows)
            await session.commit()
            logger.info("reconciled %d llm call logs (scanned %d)", inserted, len(rows))
    except Exception:  # noqa: BLE001
        logger.error("failed to reconcile llm call logs", exc_info=True)


async def _upsert_spend_log_rows(session: AsyncSession, rows) -> int:
    ai_key_cache: dict[str, AiKey | None] = {}
    user_cache: dict[str, User | None] = {}
    deployment_cache: dict[str, tuple[ModelDeployment, Model] | None] = {}
    inserted = 0

    for row in rows:
        request_id = row[0]
        if not request_id:
            continue

        api_key_token = row[1] or ""
        user_field = row[2] or ""
        model_name = row[3] or ""
        provider = row[4] or ""
        call_type = row[5] or ""
        total_tokens = int(row[7] or 0)
        prompt_tokens = int(row[8] or 0)
        completion_tokens = int(row[9] or 0)
        start = _as_utc_datetime(row[10])
        end = _as_utc_datetime(row[11])
        ttft_at = _as_utc_datetime(row[12])
        session_id = row[13] or ""
        status = row[14] or "success"
        metadata = _parse_json_object(row[15])
        messages_raw = row[17]
        response_raw = row[18]
        proxy_request_raw = row[19]
        spend_log_model_id = str(row[20]) if row[20] else ""

        cache_read, cache_creation = _parse_cache_tokens(metadata)
        billable_prompt_tokens = _billable_prompt_tokens(
            prompt_tokens, cache_read, cache_creation
        )

        ai_key_id: int | None = None
        if api_key_token and api_key_token != "litellm_proxy_master_key":
            key_alias = metadata.get("user_api_key_alias") or ""
            cache_key = key_alias or api_key_token
            if cache_key not in ai_key_cache:
                if key_alias:
                    result = await session.execute(
                        select(AiKey).where(AiKey.litellm_key_alias == key_alias)
                    )
                else:
                    result = await session.execute(
                        select(AiKey).where(AiKey.litellm_key_id == api_key_token)
                    )
                ai_key_cache[cache_key] = result.scalar_one_or_none()
            ai_key = ai_key_cache[cache_key]
            if ai_key:
                ai_key_id = ai_key.id

        user_id: int | None = None
        user_api_key_user_id = ""
        if isinstance(metadata.get("user_api_key_user_id"), str):
            user_api_key_user_id = metadata["user_api_key_user_id"]
        user_lookup = user_api_key_user_id or user_field
        if user_lookup and user_lookup != "default_user_id":
            if user_lookup not in user_cache:
                result = await session.execute(
                    select(User).where(User.litellm_user_id == user_lookup)
                )
                user_cache[user_lookup] = result.scalar_one_or_none()
            user = user_cache[user_lookup]
            if user:
                user_id = user.id

        deployment_id: int | None = None
        internal_cost = Decimal("0")
        external_cost = Decimal("0")
        litellm_model_id = spend_log_model_id or metadata.get("model_id") or ""
        dep_cache_key = litellm_model_id or model_name
        if dep_cache_key and dep_cache_key not in deployment_cache:
            pair = None
            if litellm_model_id:
                result = await session.execute(
                    select(ModelDeployment, Model)
                    .join(Model, Model.id == ModelDeployment.model_id)
                    .where(ModelDeployment.litellm_model_id == litellm_model_id)
                    .limit(1)
                )
                pair = result.first()
            if not pair and model_name:
                lookup_name = model_name
                if lookup_name.endswith(ANTHROPIC_MODEL_SUFFIX):
                    lookup_name = lookup_name[: -len(ANTHROPIC_MODEL_SUFFIX)]
                result = await session.execute(
                    select(ModelDeployment, Model)
                    .join(Model, Model.id == ModelDeployment.model_id)
                    .where(Model.model_id == lookup_name)
                    .limit(1)
                )
                pair = result.first()
                if not pair and "/" in lookup_name:
                    bare = lookup_name.split("/", 1)[1]
                    result = await session.execute(
                        select(ModelDeployment, Model)
                        .join(Model, Model.id == ModelDeployment.model_id)
                        .where(Model.model_id == bare)
                        .limit(1)
                    )
                    pair = result.first()
            deployment_cache[dep_cache_key] = pair
        deployment_pair = deployment_cache.get(dep_cache_key)
        if deployment_pair:
            deployment, _ = deployment_pair
            deployment_id = deployment.id
            internal_cost = _calc_internal_cost(
                deployment,
                billable_prompt_tokens,
                completion_tokens,
                cache_read,
                cache_creation,
            )
            external_cost = _calc_external_cost(
                deployment,
                billable_prompt_tokens,
                completion_tokens,
                cache_read,
                cache_creation,
            )

        duration_ms = None
        if start and end:
            try:
                duration_ms = int((end - start).total_seconds() * 1000)
            except (TypeError, AttributeError):
                pass

        ttft_ms = None
        if start and ttft_at:
            try:
                ttft_ms = int((ttft_at - start).total_seconds() * 1000)
            except (TypeError, AttributeError):
                pass

        error_message = None
        error_info = metadata.get("error_information")
        if isinstance(error_info, dict):
            error_message = error_info.get("error_message") or json.dumps(
                error_info, ensure_ascii=False
            )
        elif isinstance(error_info, str):
            error_message = error_info

        statement = insert(LlmCallLog).values(
            request_id=request_id,
            user_id=user_id,
            ai_key_id=ai_key_id,
            deployment_id=deployment_id,
            model=model_name,
            provider=provider,
            call_type=call_type,
            status=status,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            external_cost=external_cost,
            internal_cost=internal_cost,
            duration_ms=duration_ms,
            ttft_ms=ttft_ms,
            started_at=start,
            ended_at=end,
            session_id=session_id,
            error_message=error_message,
            messages=_messages_from_payload(messages_raw, proxy_request_raw),
            response=_json_payload_or_none(response_raw),
            metadata_=metadata,
        ).on_conflict_do_nothing(index_elements=["request_id"])
        result = await session.execute(statement)
        inserted += result.rowcount or 0

    return inserted

def _calc_internal_cost(
    deployment: ModelDeployment,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read: int,
    cache_creation: int,
) -> Decimal:
    """根据 deployment.model_info 中的内部定价算成本（单位 ¥/百万 token）。"""
    info = deployment.model_info or {}
    billing_type = deployment.billing_type or "token"

    if billing_type == "per_call":
        per_call = info.get("internal_cost_per_call")
        return Decimal(str(per_call)) if per_call else Decimal("0")

    # token 计费
    input_price = Decimal(str(info.get("internal_input_cost") or 0))
    output_price = Decimal(str(info.get("internal_output_cost") or 0))
    cache_read_price = Decimal(str(info.get("internal_cache_read_cost") or 0))
    cache_creation_price = Decimal(str(info.get("internal_cache_creation_cost") or 0))

    million = Decimal("1000000")
    cost = (
        input_price * prompt_tokens / million
        + output_price * completion_tokens / million
        + cache_read_price * cache_read / million
        + cache_creation_price * cache_creation / million
    )
    return cost.quantize(Decimal("0.000001"))


def _calc_external_cost(
    deployment: ModelDeployment,
    prompt_tokens: int,
    completion_tokens: int,
    cache_read: int,
    cache_creation: int,
) -> Decimal:
    """根据 deployment.model_info 中的外部定价算成本（单位 ¥/百万 token）。"""
    info = deployment.model_info or {}
    billing_type = deployment.billing_type or "token"

    if billing_type == "per_call":
        per_call = info.get("cost_per_call") or deployment.cost_per_call
        return Decimal(str(per_call)) if per_call else Decimal("0")

    # token 计费
    input_price = Decimal(str(info.get("input_cost") or 0))
    output_price = Decimal(str(info.get("output_cost") or 0))
    cache_read_price = Decimal(str(info.get("cache_read_cost") or 0))
    cache_creation_price = Decimal(str(info.get("cache_creation_cost") or 0))

    million = Decimal("1000000")
    cost = (
        input_price * prompt_tokens / million
        + output_price * completion_tokens / million
        + cache_read_price * cache_read / million
        + cache_creation_price * cache_creation / million
    )
    return cost.quantize(Decimal("0.000001"))


async def _recalc_cost(batch_size: int) -> dict[str, int]:
    processed = 0
    updated = 0
    last_id = 0
    async with get_worker_session_factory()() as session:
        while True:
            result = await session.execute(
                select(LlmCallLog, ModelDeployment)
                .outerjoin(
                    ModelDeployment, ModelDeployment.id == LlmCallLog.deployment_id
                )
                .where(LlmCallLog.id > last_id)
                .order_by(LlmCallLog.id)
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            for log, deployment in rows:
                last_id = log.id
                cache_read, cache_creation = _parse_cache_tokens(log.metadata_ or {})
                billable_prompt_tokens = _billable_prompt_tokens(
                    log.prompt_tokens, cache_read, cache_creation
                )
                internal_cost = Decimal("0")
                external_cost = Decimal("0")
                if deployment:
                    internal_cost = _calc_internal_cost(
                        deployment,
                        billable_prompt_tokens,
                        log.completion_tokens,
                        cache_read,
                        cache_creation,
                    )
                    external_cost = _calc_external_cost(
                        deployment,
                        billable_prompt_tokens,
                        log.completion_tokens,
                        cache_read,
                        cache_creation,
                    )

                log.cache_read_tokens = cache_read
                log.cache_creation_tokens = cache_creation
                log.internal_cost = internal_cost
                log.external_cost = external_cost
                processed += 1
                updated += 1

            await session.commit()
    logger.info("recalculated %d llm costs", updated)
    return {"processed": processed, "updated": updated}


async def _cleanup() -> None:
    """按 LLM_LOG_RETENTION_DAYS 配置清理过期日志，0 = 不清理。"""
    retention_days = settings.llm_log_retention_days
    if retention_days <= 0:
        logger.info("llm log retention disabled, skip cleanup")
        return
    before = datetime.now(timezone.utc) - timedelta(days=retention_days)
    try:
        async with get_worker_session_factory()() as session:
            result = await session.execute(
                delete(LlmCallLog).where(LlmCallLog.started_at < before)
            )
            await session.commit()
        deleted = result.rowcount or 0
        logger.info(
            "cleaned llm call logs before %s, deleted=%s",
            before.isoformat(),
            deleted,
        )
    except Exception:  # noqa: BLE001
        logger.error("failed to cleanup llm call logs", exc_info=True)
