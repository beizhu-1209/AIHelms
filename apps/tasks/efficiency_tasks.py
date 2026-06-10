"""AI 效能：聚合 llm_call_logs + mcp_call_logs 到 cost_summary_daily。

每 5 分钟跑一次，重建最近一段时间的派生汇总，避免 sync_state 推进但汇总表
缺行时无法自愈。业务成本源仍然只取平台日志表。
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from celery_app import celery_app
from core.database import get_worker_session_factory
from models.db import SyncState

logger = logging.getLogger(__name__)

SYNC_KEY = "cost_summary_daily"
ROLLING_REBUILD_DAYS = 60


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="efficiency.aggregate")
def aggregate_cost_summary() -> None:
    _run_async(_aggregate())


async def _aggregate() -> None:
    try:
        async with get_worker_session_factory()() as session:
            now = datetime.now(timezone.utc)
            sync_state = await session.get(SyncState, SYNC_KEY)
            if sync_state is None:
                sync_state = SyncState(key=SYNC_KEY, last_sync_at=now)
                session.add(sync_state)
                await session.flush()

            earliest = await session.execute(
                text("""
                    SELECT MIN(ts) FROM (
                        SELECT MIN(started_at) AS ts FROM aihelms.llm_call_logs
                        UNION ALL
                        SELECT MIN(called_at) AS ts FROM aihelms.mcp_call_logs
                    ) t
                """)
            )
            earliest_ts = earliest.scalar()
            summary_count = await session.execute(
                text("SELECT COUNT(*) FROM aihelms.cost_summary_daily")
            )
            has_summary = int(summary_count.scalar() or 0) > 0
            if not has_summary and earliest_ts:
                rebuild_start = earliest_ts.date()
            else:
                rebuild_start = (now - timedelta(days=ROLLING_REBUILD_DAYS)).date()

            # cost_summary_daily 是平台日志的派生汇总。滚动窗口重建可以修复漏聚合，
            # 不修改 llm_call_logs / mcp_call_logs 等业务源数据。
            await session.execute(
                text("""
                    DELETE FROM aihelms.cost_summary_daily
                    WHERE summary_date >= :rebuild_start
                """),
                {"rebuild_start": rebuild_start},
            )

            # LLM 日志聚合
            await session.execute(
                text("""
                    INSERT INTO aihelms.cost_summary_daily (
                        summary_date, user_id, ai_key_id, model, provider_id,
                        cost_type, key_type, total_requests, successful_requests,
                        failed_requests, input_tokens, output_tokens, cache_tokens,
                        external_cost, internal_cost, total_duration_ms,
                        last_aggregated_at
                    )
                    SELECT
                        date_trunc('day', l.started_at)::date AS summary_date,
                        l.user_id,
                        l.ai_key_id,
                        l.model,
                        d.credential_id AS provider_id,
                        'llm' AS cost_type,
                        k.key_type,
                        COUNT(*) AS total_requests,
                        COUNT(*) FILTER (WHERE l.status = 'success'),
                        COUNT(*) FILTER (WHERE l.status != 'success'),
                        COALESCE(SUM(l.prompt_tokens), 0),
                        COALESCE(SUM(l.completion_tokens), 0),
                        COALESCE(SUM(l.cache_read_tokens), 0),
                        COALESCE(SUM(l.external_cost), 0),
                        COALESCE(SUM(l.internal_cost), 0),
                        COALESCE(SUM(l.duration_ms), 0),
                        NOW()
                    FROM aihelms.llm_call_logs l
                    LEFT JOIN aihelms.ai_keys k ON k.id = l.ai_key_id
                    LEFT JOIN aihelms.model_deployments d ON d.id = l.deployment_id
                    WHERE l.started_at::date >= :rebuild_start
                      AND l.started_at < :now
                    GROUP BY 1,2,3,4,5,6,7
                """),
                {"rebuild_start": rebuild_start, "now": now},
            )

            # MCP 日志聚合
            await session.execute(
                text("""
                    INSERT INTO aihelms.cost_summary_daily (
                        summary_date, user_id, ai_key_id, server_id, cost_type,
                        key_type, total_requests, successful_requests, failed_requests,
                        external_cost, internal_cost, total_duration_ms,
                        last_aggregated_at
                    )
                    SELECT
                        date_trunc('day', m.called_at)::date AS summary_date,
                        m.user_id,
                        m.ai_key_id,
                        m.server_id,
                        'mcp' AS cost_type,
                        k.key_type,
                        COUNT(*),
                        COUNT(*) FILTER (WHERE m.status = 'success'),
                        COUNT(*) FILTER (WHERE m.status != 'success'),
                        COALESCE(SUM(m.external_cost), 0),
                        COALESCE(SUM(m.internal_cost), 0),
                        COALESCE(SUM(m.duration_ms), 0),
                        NOW()
                    FROM aihelms.mcp_call_logs m
                    LEFT JOIN aihelms.ai_keys k ON k.id = m.ai_key_id
                    WHERE m.called_at::date >= :rebuild_start
                      AND m.called_at < :now
                    GROUP BY 1,2,3,4,5,6
                """),
                {"rebuild_start": rebuild_start, "now": now},
            )

            # 更新 ai_keys.budget_used
            await _update_budget_used(session)

            sync_state.last_sync_at = now
            await session.commit()
            logger.info("efficiency aggregation completed: rebuild_start=%s", rebuild_start)
    except Exception:
        logger.error("efficiency aggregation failed", exc_info=True)


async def _update_budget_used(session) -> None:
    """批量更新每个 ai_key 在其 budget_duration 周期内的累计成本。"""
    for duration, interval in [("30d", "30 days"), ("7d", "7 days"), ("1d", "1 day")]:
        await session.execute(
            text(f"""
                WITH key_costs AS (
                    SELECT ai_key_id, COALESCE(SUM(cost), 0) AS total_cost
                    FROM (
                        SELECT ai_key_id, internal_cost AS cost
                        FROM aihelms.llm_call_logs
                        WHERE ai_key_id IS NOT NULL
                          AND started_at >= NOW() - INTERVAL '{interval}'
                        UNION ALL
                        SELECT ai_key_id, internal_cost AS cost
                        FROM aihelms.mcp_call_logs
                        WHERE ai_key_id IS NOT NULL
                          AND called_at >= NOW() - INTERVAL '{interval}'
                    ) combined
                    GROUP BY ai_key_id
                )
                UPDATE aihelms.ai_keys k
                SET budget_used = kc.total_cost
                FROM key_costs kc
                WHERE k.id = kc.ai_key_id
                  AND k.budget_duration = :duration
                  AND (k.budget_limit IS NOT NULL
                       OR k.budget_models_total IS NOT NULL
                       OR k.budget_mcps_total IS NOT NULL)
            """),
            {"duration": duration},
        )
    # 没有调用记录的 Key，归零
    await session.execute(
        text("""
            UPDATE aihelms.ai_keys
            SET budget_used = 0
            WHERE (budget_limit IS NOT NULL
                   OR budget_models_total IS NOT NULL
                   OR budget_mcps_total IS NOT NULL)
              AND id NOT IN (
                  SELECT DISTINCT ai_key_id FROM aihelms.llm_call_logs
                  WHERE ai_key_id IS NOT NULL
                  UNION
                  SELECT DISTINCT ai_key_id FROM aihelms.mcp_call_logs
                  WHERE ai_key_id IS NOT NULL
              )
        """)
    )
