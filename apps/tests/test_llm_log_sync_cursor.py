"""LLM 日志同步游标推进测试。

复现「回退窗口内记录数超过单批上限时游标原地不动」的死锁，
以及 reconcile 补数方向应优先补新数据。

测试数据全部带 TEST_PREFIX 标记，用固定的未来时间段，
teardown 按前缀清理，不触碰任何真实数据。
"""

import logging
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from core.database import get_worker_session_factory
from models.db import SyncState
from tasks import llm_log_tasks

TEST_PREFIX = "pytest-cursor-"
WINDOW_START = datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
BATCH_SIZE = 5


def _naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def _insert_spend_logs(
    session, count: int, start: datetime, step_seconds: int
) -> list[str]:
    request_ids = []
    for index in range(count):
        request_id = f"{TEST_PREFIX}{index:04d}"
        moment = _naive(start + timedelta(seconds=index * step_seconds))
        await session.execute(
            text(
                'INSERT INTO public."LiteLLM_SpendLogs" '
                '(request_id, call_type, api_key, spend, total_tokens, prompt_tokens, '
                'completion_tokens, "startTime", "endTime", model, status) '
                "VALUES (:rid, 'acompletion', :api_key, 0, 10, 6, 4, "
                ":start_time, :end_time, 'pytest-model', 'success')"
            ),
            {
                "rid": request_id,
                "api_key": f"{TEST_PREFIX}key",
                "start_time": moment,
                "end_time": moment,
            },
        )
        request_ids.append(request_id)
    return request_ids


async def _cleanup(session) -> None:
    await session.execute(
        text("DELETE FROM aihelms.llm_call_logs WHERE request_id LIKE :p"),
        {"p": f"{TEST_PREFIX}%"},
    )
    await session.execute(
        text('DELETE FROM public."LiteLLM_SpendLogs" WHERE request_id LIKE :p'),
        {"p": f"{TEST_PREFIX}%"},
    )


@pytest_asyncio.fixture
async def sync_env(monkeypatch):
    """造数据 + 备份游标，测试结束还原并清理。"""
    monkeypatch.setattr(llm_log_tasks, "SPEND_LOG_BATCH_SIZE", BATCH_SIZE)

    factory = get_worker_session_factory()
    async with factory() as session:
        await _cleanup(session)
        saved = await session.get(SyncState, "llm_logs")
        saved_last_sync_at = saved.last_sync_at if saved else None
        saved_last_request_id = saved.last_request_id if saved else None
        await session.commit()

    yield factory

    async with factory() as session:
        await _cleanup(session)
        state = await session.get(SyncState, "llm_logs")
        if state is not None:
            if saved_last_sync_at is not None:
                state.last_sync_at = saved_last_sync_at
                state.last_request_id = saved_last_request_id
            else:
                await session.delete(state)
        await session.commit()


async def _seed_dense_window(factory, count: int) -> tuple[list[str], datetime]:
    """在 1 分钟内塞 count 条记录，游标设在这批数据之前。

    count > BATCH_SIZE 时单批被 LIMIT 截断，旧代码把游标推到本批最大时间后，
    10 分钟回退窗口又会把同一批重新纳入扫描，游标从此原地不动。
    """
    async with factory() as session:
        request_ids = await _insert_spend_logs(
            session, count, WINDOW_START, step_seconds=1
        )
        newest = WINDOW_START + timedelta(seconds=(count - 1))
        state = await session.get(SyncState, "llm_logs")
        cursor = WINDOW_START - timedelta(seconds=1)
        if state is None:
            state = SyncState(key="llm_logs", last_sync_at=cursor)
            session.add(state)
        else:
            state.last_sync_at = cursor
            state.last_request_id = None
        await session.commit()
    return request_ids, newest


async def _read_cursor(factory) -> datetime:
    async with factory() as session:
        state = await session.get(SyncState, "llm_logs")
        return state.last_sync_at


async def _count_synced(factory) -> int:
    async with factory() as session:
        result = await session.execute(
            text("SELECT count(*) FROM aihelms.llm_call_logs WHERE request_id LIKE :p"),
            {"p": f"{TEST_PREFIX}%"},
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_llm_log_sync_dense_window_advances_cursor_past_newest_row(sync_env):
    """单批被 LIMIT 截断时，游标必须越过窗口内最新一条记录，不能卡住。"""
    _, newest = await _seed_dense_window(sync_env, count=BATCH_SIZE + 1)

    await llm_log_tasks._sync()
    cursor_after_first = await _read_cursor(sync_env)
    await llm_log_tasks._sync()
    cursor_after_second = await _read_cursor(sync_env)

    assert cursor_after_first >= newest, (
        f"首轮未追平积压：游标 {cursor_after_first} < 最新记录 {newest}"
    )
    assert cursor_after_second >= newest, (
        f"游标回退：{cursor_after_first} -> {cursor_after_second}"
    )


@pytest.mark.asyncio
async def test_llm_log_sync_dense_window_syncs_all_rows(sync_env):
    """连续两轮同步后，密集窗口内的记录必须全部入库且不重复。"""
    request_ids, _ = await _seed_dense_window(sync_env, count=BATCH_SIZE + 1)

    await llm_log_tasks._sync()
    await llm_log_tasks._sync()

    synced = await _count_synced(sync_env)
    assert synced == len(request_ids), f"应入库 {len(request_ids)} 条，实际 {synced} 条"


@pytest.mark.asyncio
async def test_llm_log_sync_stalled_cursor_logs_error(sync_env, monkeypatch, caplog):
    """游标未前进时必须报 ERROR，不能静默空转。"""
    request_ids, _ = await _seed_dense_window(sync_env, count=BATCH_SIZE + 1)
    stalled = (WINDOW_START - timedelta(seconds=1), request_ids[0])
    monkeypatch.setattr(llm_log_tasks, "_max_spend_cursor", lambda rows: stalled)

    with caplog.at_level(logging.ERROR, logger=llm_log_tasks.__name__):
        await llm_log_tasks._sync()

    assert "cursor did not advance" in caplog.text, (
        f"游标卡住时未报 ERROR，实际日志：{caplog.text!r}"
    )


@pytest.mark.asyncio
async def test_llm_log_reconcile_backfills_newest_rows_first(sync_env):
    """reconcile 补数必须先补最新的缺失记录。"""
    async with sync_env() as session:
        await _insert_spend_logs(
            session, count=BATCH_SIZE * 2, start=WINDOW_START, step_seconds=3600
        )
        await session.commit()

    await llm_log_tasks._reconcile()

    async with sync_env() as session:
        result = await session.execute(
            text(
                "SELECT request_id FROM aihelms.llm_call_logs "
                "WHERE request_id LIKE :p ORDER BY request_id"
            ),
            {"p": f"{TEST_PREFIX}%"},
        )
        synced_ids = [row[0] for row in result.fetchall()]

    newest_ids = {f"{TEST_PREFIX}{i:04d}" for i in range(BATCH_SIZE, BATCH_SIZE * 2)}
    assert set(synced_ids) == newest_ids, (
        f"应先补最新 {BATCH_SIZE} 条 {sorted(newest_ids)}，实际补了 {synced_ids}"
    )
