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
            now = datetime.now(timezone.utc)
            sync_state = await session.get(SyncState, "llm_logs")
            if sync_state is None:
                sync_state = SyncState(
                    key="llm_logs",
                    last_sync_at=now - timedelta(hours=1),
                )
                session.add(sync_state)
                await session.flush()

            start_time = sync_state.last_sync_at - timedelta(minutes=1)
            # SpendLogs.startTime 是 UTC naive，去掉 tzinfo 用于比较
            start_time_naive = (
                start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            )

            has_spend_log_model_id = await _spend_logs_has_column(session, "model_id")
            spend_log_model_id_select = (
                "model_id AS spend_log_model_id"
                if has_spend_log_model_id
                else "NULL AS spend_log_model_id"
            )
            result = await session.execute(
                text(
                    'SELECT request_id, api_key, "user", model, custom_llm_provider, '
                    "call_type, spend, total_tokens, prompt_tokens, completion_tokens, "
                    '"startTime", "endTime", "completionStartTime", '
                    "session_id, status, metadata, mcp_namespaced_tool_name, "
                    f"messages, response, {spend_log_model_id_select} "
                    'FROM public."LiteLLM_SpendLogs" '
                    'WHERE "startTime" >= :start_time '
                    "  AND (mcp_namespaced_tool_name IS NULL "
                    "       OR mcp_namespaced_tool_name = '') "
                    "  AND COALESCE(call_type, '') NOT IN ("
                    "       'list_mcp_tools', 'list_mcp_tool', "
                    "       'mcp_list_tools', 'mcp_list_tool') "
                    'ORDER BY "startTime" ASC '
                    "LIMIT 1000"
                ),
                {"start_time": start_time_naive},
            )
            rows = result.fetchall()

            if not rows:
                sync_state.last_sync_at = now
                await session.commit()
                return

            ai_key_cache: dict[str, AiKey | None] = {}
            user_cache: dict[str, User | None] = {}
            deployment_cache: dict[str, tuple[ModelDeployment, Model] | None] = {}

            inserted = 0
            for row in rows:
                request_id = row[0]
                if not request_id:
                    continue

                existing = await session.execute(
                    select(LlmCallLog.id).where(LlmCallLog.request_id == request_id)
                )
                if existing.scalar_one_or_none():
                    continue

                api_key_token = row[1] or ""
                user_field = row[2] or ""
                model_name = row[3] or ""
                provider = row[4] or ""
                call_type = row[5] or ""
                total_tokens = int(row[7] or 0)
                prompt_tokens = int(row[8] or 0)
                completion_tokens = int(row[9] or 0)
                start = row[10]
                end = row[11]
                ttft_at = row[12]

                # SpendLogs 时间是 UTC naive，标记为 UTC 避免 PG 按会话时区误转
                if start and not start.tzinfo:
                    start = start.replace(tzinfo=timezone.utc)
                if end and not end.tzinfo:
                    end = end.replace(tzinfo=timezone.utc)
                if ttft_at and not ttft_at.tzinfo:
                    ttft_at = ttft_at.replace(tzinfo=timezone.utc)
                session_id = row[13] or ""
                status = row[14] or "success"
                metadata_raw = row[15]
                metadata: dict = {}
                if metadata_raw:
                    if isinstance(metadata_raw, str):
                        try:
                            metadata = json.loads(metadata_raw)
                        except (json.JSONDecodeError, ValueError):
                            metadata = {}
                    elif isinstance(metadata_raw, dict):
                        metadata = metadata_raw

                messages_raw = row[17]
                response_raw = row[18]
                spend_log_model_id = str(row[19]) if row[19] else ""

                cache_read, cache_creation = _parse_cache_tokens(metadata)
                billable_prompt_tokens = _billable_prompt_tokens(
                    prompt_tokens, cache_read, cache_creation
                )

                # 反查 ai_key
                ai_key_id: int | None = None
                if api_key_token and api_key_token != "litellm_proxy_master_key":
                    key_alias = metadata.get("user_api_key_alias") or ""
                    cache_key = key_alias or api_key_token
                    if cache_key not in ai_key_cache:
                        if key_alias:
                            r = await session.execute(
                                select(AiKey).where(
                                    AiKey.litellm_key_alias == key_alias
                                )
                            )
                        else:
                            r = await session.execute(
                                select(AiKey).where(
                                    AiKey.litellm_key_id == api_key_token
                                )
                            )
                        ai_key_cache[cache_key] = r.scalar_one_or_none()
                    ai_key = ai_key_cache[cache_key]
                    if ai_key:
                        ai_key_id = ai_key.id

                # 反查 user
                user_id: int | None = None
                user_api_key_user_id = ""
                if isinstance(metadata.get("user_api_key_user_id"), str):
                    user_api_key_user_id = metadata["user_api_key_user_id"]
                user_lookup = user_api_key_user_id or user_field
                if user_lookup and user_lookup != "default_user_id":
                    if user_lookup not in user_cache:
                        r = await session.execute(
                            select(User).where(User.litellm_user_id == user_lookup)
                        )
                        user_cache[user_lookup] = r.scalar_one_or_none()
                    user = user_cache[user_lookup]
                    if user:
                        user_id = user.id

                # 反查 deployment + 算成本
                deployment_id: int | None = None
                internal_cost = Decimal("0")
                external_cost = Decimal("0")
                litellm_model_id = spend_log_model_id or metadata.get("model_id") or ""
                dep_cache_key = litellm_model_id or model_name
                if dep_cache_key and dep_cache_key not in deployment_cache:
                    pair = None
                    # 优先用 litellm_model_id 精确匹配
                    if litellm_model_id:
                        r = await session.execute(
                            select(ModelDeployment, Model)
                            .join(Model, Model.id == ModelDeployment.model_id)
                            .where(ModelDeployment.litellm_model_id == litellm_model_id)
                            .limit(1)
                        )
                        pair = r.first()
                    # fallback: 按模型名匹配
                    if not pair and model_name:
                        lookup_name = model_name
                        # Strip (Anthropic) suffix for platform model matching
                        if lookup_name.endswith(ANTHROPIC_MODEL_SUFFIX):
                            lookup_name = lookup_name[: -len(ANTHROPIC_MODEL_SUFFIX)]
                        r = await session.execute(
                            select(ModelDeployment, Model)
                            .join(Model, Model.id == ModelDeployment.model_id)
                            .where(Model.model_id == lookup_name)
                            .limit(1)
                        )
                        pair = r.first()
                        # 去前缀再试: "deepseek/deepseek-v4-pro" → "deepseek-v4-pro"
                        if not pair and "/" in lookup_name:
                            bare = lookup_name.split("/", 1)[1]
                            r = await session.execute(
                                select(ModelDeployment, Model)
                                .join(Model, Model.id == ModelDeployment.model_id)
                                .where(Model.model_id == bare)
                                .limit(1)
                            )
                            pair = r.first()
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

                log = LlmCallLog(
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
                    messages=(
                        messages_raw if isinstance(messages_raw, (dict, list)) else None
                    ),
                    response=(
                        response_raw if isinstance(response_raw, (dict, list)) else None
                    ),
                    metadata_=metadata,
                )
                session.add(log)
                inserted += 1

            sync_state.last_sync_at = now
            await session.commit()
            logger.info("synced %d llm call logs (scanned %d)", inserted, len(rows))
    except Exception:  # noqa: BLE001
        logger.error("failed to sync llm call logs", exc_info=True)


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
