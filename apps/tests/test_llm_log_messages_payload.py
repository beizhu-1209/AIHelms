"""LLM 日志请求内容提取测试。

覆盖 /v1/responses（call_type=aresponses）的请求体用 input 承载对话内容、
没有 messages 字段的情况，以及 chat/completions、anthropic 的原有形态。

测试数据带 TEST_PREFIX 标记，teardown 按前缀清理，不触碰真实数据。
"""

import json
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from core.database import get_worker_session_factory
from models.db import SyncState
from tasks import llm_log_tasks

TEST_PREFIX = "pytest-payload-"
WINDOW_START = datetime(2027, 2, 1, 0, 0, 0, tzinfo=timezone.utc)


def _naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def _insert_spend_log(
    session,
    request_id: str,
    call_type: str,
    proxy_server_request: dict,
    messages: object = None,
    offset_seconds: int = 0,
) -> None:
    moment = _naive(WINDOW_START + timedelta(seconds=offset_seconds))
    await session.execute(
        text(
            'INSERT INTO public."LiteLLM_SpendLogs" '
            "(request_id, call_type, api_key, spend, total_tokens, prompt_tokens, "
            'completion_tokens, "startTime", "endTime", model, status, '
            "messages, proxy_server_request) "
            "VALUES (:rid, :call_type, :api_key, 0, 10, 6, 4, "
            ":moment, :moment, 'pytest-model', 'success', "
            "CAST(:messages AS jsonb), CAST(:proxy AS jsonb))"
        ),
        {
            "rid": request_id,
            "call_type": call_type,
            "api_key": f"{TEST_PREFIX}key",
            "moment": moment,
            "messages": json.dumps(messages) if messages is not None else None,
            "proxy": json.dumps(proxy_server_request),
        },
    )


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
async def payload_env():
    """备份同步游标，测试结束还原并清理测试数据。"""
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


async def _set_cursor_before_window(session) -> None:
    cursor = WINDOW_START - timedelta(seconds=1)
    state = await session.get(SyncState, "llm_logs")
    if state is None:
        session.add(SyncState(key="llm_logs", last_sync_at=cursor))
    else:
        state.last_sync_at = cursor
        state.last_request_id = None


async def _read_messages(factory, request_id: str) -> object:
    async with factory() as session:
        result = await session.execute(
            text("SELECT messages FROM aihelms.llm_call_logs WHERE request_id = :rid"),
            {"rid": request_id},
        )
        return result.scalar_one()


@pytest.mark.asyncio
async def test_llm_log_sync_responses_input_array_stored_as_messages(payload_env):
    """/v1/responses 的 input 数组必须落到 messages 字段。"""
    request_id = f"{TEST_PREFIX}responses-array"
    conversation = [{"role": "user", "content": "你好"}]
    async with payload_env() as session:
        await _insert_spend_log(
            session,
            request_id,
            "aresponses",
            {"model": "gpt-5", "input": conversation},
        )
        await _set_cursor_before_window(session)
        await session.commit()

    await llm_log_tasks._sync()

    assert await _read_messages(payload_env, request_id) == conversation


@pytest.mark.asyncio
async def test_llm_log_sync_responses_input_string_wrapped_as_user_message(payload_env):
    """/v1/responses 的 input 字符串必须包成单条 user 消息。"""
    request_id = f"{TEST_PREFIX}responses-string"
    async with payload_env() as session:
        await _insert_spend_log(
            session,
            request_id,
            "aresponses",
            {"model": "gpt-5", "input": "一句话介绍自己"},
        )
        await _set_cursor_before_window(session)
        await session.commit()

    await llm_log_tasks._sync()

    assert await _read_messages(payload_env, request_id) == [
        {"role": "user", "content": "一句话介绍自己"}
    ]


@pytest.mark.asyncio
async def test_llm_log_sync_chat_completions_messages_still_preferred(payload_env):
    """chat/completions 的 messages 优先级高于 input，原有行为不变。"""
    request_id = f"{TEST_PREFIX}chat"
    conversation = [{"role": "user", "content": "chat 请求"}]
    async with payload_env() as session:
        await _insert_spend_log(
            session,
            request_id,
            "acompletion",
            {"model": "gpt-4o", "messages": conversation, "input": "不应被采用"},
        )
        await _set_cursor_before_window(session)
        await session.commit()

    await llm_log_tasks._sync()

    assert await _read_messages(payload_env, request_id) == conversation


@pytest.mark.asyncio
async def test_llm_log_sync_payload_without_content_keeps_messages_null(payload_env):
    """请求体既无 messages 也无 input 时 messages 保持为空。"""
    request_id = f"{TEST_PREFIX}empty"
    async with payload_env() as session:
        await _insert_spend_log(
            session,
            request_id,
            "aembedding",
            {"model": "text-embedding-3-small"},
        )
        await _set_cursor_before_window(session)
        await session.commit()

    await llm_log_tasks._sync()

    assert await _read_messages(payload_env, request_id) is None
