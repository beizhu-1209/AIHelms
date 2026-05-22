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
            # LiteLLM_SpendLogs.startTime 是 timestamp without timezone，需要去除 tzinfo
            start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time

            result = await session.execute(
                text(
                    'SELECT request_id, api_key, "user", model, custom_llm_provider, '
                    "call_type, spend, total_tokens, prompt_tokens, completion_tokens, "
                    '"startTime", "endTime", "completionStartTime", '
                    "session_id, status, metadata, mcp_namespaced_tool_name "
                    'FROM public."LiteLLM_SpendLogs" '
                    'WHERE "startTime" >= :start_time '
                    "  AND (mcp_namespaced_tool_name IS NULL "
                    "       OR mcp_namespaced_tool_name = '') "
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
                spend = float(row[6] or 0)
                total_tokens = int(row[7] or 0)
                prompt_tokens = int(row[8] or 0)
                completion_tokens = int(row[9] or 0)
                start = row[10]
                end = row[11]
                ttft_at = row[12]
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

                cache_read = 0
                cache_creation = 0
                usage_obj = metadata.get("usage_object") or {}
                if isinstance(usage_obj, dict):
                    cache_read = int(usage_obj.get("cache_read_input_tokens") or 0)
                    cache_creation = int(
                        usage_obj.get("cache_creation_input_tokens") or 0
                    )

                # 反查 ai_key
                ai_key_id: int | None = None
                if api_key_token and api_key_token != "litellm_proxy_master_key":
                    if api_key_token not in ai_key_cache:
                        r = await session.execute(
                            select(AiKey).where(AiKey.litellm_key_id == api_key_token)
                        )
                        ai_key_cache[api_key_token] = r.scalar_one_or_none()
                    ai_key = ai_key_cache[api_key_token]
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

                # 反查 deployment + 算 internal_cost
                deployment_id: int | None = None
                internal_cost = Decimal("0")
                if model_name and model_name not in deployment_cache:
                    r = await session.execute(
                        select(ModelDeployment, Model)
                        .join(Model, Model.id == ModelDeployment.model_id)
                        .where(Model.model_id == model_name)
                        .limit(1)
                    )
                    deployment_cache[model_name] = r.first()
                deployment_pair = deployment_cache.get(model_name)
                if deployment_pair:
                    deployment, _ = deployment_pair
                    deployment_id = deployment.id
                    internal_cost = _calc_internal_cost(
                        deployment,
                        prompt_tokens,
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
                    external_cost=Decimal(str(spend)),
                    internal_cost=internal_cost,
                    duration_ms=duration_ms,
                    ttft_ms=ttft_ms,
                    started_at=start,
                    ended_at=end,
                    session_id=session_id,
                    error_message=error_message,
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
