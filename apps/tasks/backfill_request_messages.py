"""回填历史日志的请求内容。

/v1/responses 的请求体用 input 承载对话内容，没有 messages 字段。
旧版本同步任务只读 messages，这批日志的 messages 落成了空值。
本脚本反查 LiteLLM 原始日志，用同步任务同一份取值逻辑补回去。

只补 LiteLLM 侧还留着原始请求的记录，已被清理的无法恢复。
可重复执行，不覆盖已有内容。

    cd apps && python -m tasks.backfill_request_messages --dry-run
    cd apps && python -m tasks.backfill_request_messages
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import or_, select, text, update

from core.database import get_worker_session_factory
from models.db import LlmCallLog
from tasks.llm_log_tasks import _messages_from_payload

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000


def _print(message: str) -> None:
    print(message, flush=True)


async def _backfill(dry_run: bool) -> dict[str, int]:
    """按 id 分页扫描 messages 为空的日志，反查 LiteLLM 补请求内容。"""
    scanned = 0
    filled = 0
    last_id = 0

    async with get_worker_session_factory()() as session:
        while True:
            # messages 可能是 SQL NULL，也可能是 jsonb null（LiteLLM 写入空值所致）。
            # 排除 call_type 为空的早期数据：这批在 LiteLLM 侧已无对应记录，
            # 反查必然落空，扫它们纯属空转。
            result = await session.execute(
                select(LlmCallLog.id, LlmCallLog.request_id)
                .where(
                    LlmCallLog.id > last_id,
                    LlmCallLog.call_type.is_not(None),
                    or_(
                        LlmCallLog.messages.is_(None),
                        text("llm_call_logs.messages::text = 'null'"),
                    ),
                )
                .order_by(LlmCallLog.id)
                .limit(BATCH_SIZE)
            )
            rows = result.all()
            if not rows:
                break

            last_id = rows[-1][0]
            scanned += len(rows)
            filled += await _fill_batch(session, rows, dry_run)
            _print(f"  已扫描 {scanned} 条，可回填 {filled} 条")

    return {"scanned": scanned, "filled": filled}


async def _fill_batch(session, rows, dry_run: bool) -> int:
    """反查这批 request_id 对应的 LiteLLM 原始请求，逐条补 messages。"""
    request_ids = [request_id for _, request_id in rows if request_id]
    if not request_ids:
        return 0

    # LiteLLM 表由 LiteLLM 自身维护，升级时需复查以下字段：
    # public."LiteLLM_SpendLogs" 的 request_id text、messages jsonb、
    # proxy_server_request jsonb
    result = await session.execute(
        text(
            "SELECT request_id, messages, proxy_server_request "
            'FROM public."LiteLLM_SpendLogs" '
            "WHERE request_id = ANY(:request_ids)"
        ),
        {"request_ids": request_ids},
    )
    payloads = {
        row[0]: _messages_from_payload(row[1], row[2]) for row in result.fetchall()
    }

    filled = 0
    for log_id, request_id in rows:
        messages = payloads.get(request_id)
        if not messages:
            continue
        filled += 1
        if dry_run:
            continue
        await session.execute(
            update(LlmCallLog).where(LlmCallLog.id == log_id).values(messages=messages)
        )

    if not dry_run and filled:
        await session.commit()
    return filled


def main() -> int:
    parser = argparse.ArgumentParser(description="回填历史日志的请求内容")
    parser.add_argument(
        "--dry-run", action="store_true", help="只统计可回填数量，不写入"
    )
    args = parser.parse_args()

    if args.dry_run:
        _print("dry-run 模式，不会写入任何数据")
    _print("开始扫描请求内容为空的日志（数据量大时需要几分钟）...")

    stats = asyncio.run(_backfill(args.dry_run))

    _print("")
    if stats["filled"] == 0:
        _print(f"扫描 {stats['scanned']} 条，没有需要回填的记录")
        return 0

    if args.dry_run:
        _print(f"扫描 {stats['scanned']} 条，可回填 {stats['filled']} 条")
        _print("确认后去掉 --dry-run 重新执行")
    else:
        _print(f"扫描 {stats['scanned']} 条，已回填 {stats['filled']} 条")
        _print("请在管理后台「数据中心 → 日志管理」确认请求内容已显示")
    return 0


if __name__ == "__main__":
    sys.exit(main())
