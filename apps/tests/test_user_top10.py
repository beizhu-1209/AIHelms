"""Token 卡片 + Top10 人员榜单 相关测试。

骨架由 Claude 按 dev/roadmap/token-card-top10.md 预置，断言已定死。
Codex 实现后必须让本文件全绿；不允许改断言迁就实现，只能改实现对齐方案。
凡标 # TODO(codex) 处依赖最终 SQL 措辞，Codex 需按实际实现补断言字符串。
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.v1 import efficiency as efficiency_api
from repositories import efficiency_cost_repo, efficiency_repo
from services import efficiency_cost_service


def _mock_session(rows: list[tuple]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.fetchall.return_value = rows
    session.execute.return_value = result
    return session


def _one_session(row: tuple) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.one.return_value = row
    session.execute.return_value = result
    return session


# ---------------------------------------------------------------------------
# get_user_top10 (repo)
# 期望 SELECT 列顺序（tuple 字段顺序必须与之一致）：
#   user_id, user_name, department, internal_cost,
#   input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, requests
# ---------------------------------------------------------------------------

_TOP10_ROW = (7, "Alice", "技术中心 / 前端组", 120.5, 1000, 2000, 300, 40, 55)


@pytest.mark.asyncio
async def test_user_top10_orders_by_cost_by_default():
    session = _mock_session([_TOP10_ROW])

    result = await efficiency_cost_repo.get_user_top10(
        session, date(2026, 7, 1), date(2026, 7, 17)
    )

    sql = str(session.execute.await_args.args[0])
    assert "SUM(c.internal_cost) DESC" in sql
    assert "LIMIT 10" in sql
    assert result[0]["user_id"] == 7
    assert result[0]["user_name"] == "Alice"
    assert result[0]["department"] == "技术中心 / 前端组"
    assert result[0]["internal_cost"] == 120.5
    assert result[0]["requests"] == 55
    # total_tokens = input + output + cache_read + cache_creation
    assert result[0]["total_tokens"] == 3340


@pytest.mark.asyncio
async def test_user_top10_orders_by_tokens():
    session = _mock_session([_TOP10_ROW])

    await efficiency_cost_repo.get_user_top10(
        session, date(2026, 7, 1), date(2026, 7, 17), metric="tokens"
    )

    sql = str(session.execute.await_args.args[0])
    # ORDER BY 必须是四个 token 列相加，按聚合表真实列名
    assert "input_tokens" in sql and "output_tokens" in sql
    assert "cache_read_tokens" in sql and "cache_creation_tokens" in sql
    # 姓名口径必须防空串
    assert "COALESCE(NULLIF(u.display_name, ''), u.username, '')" in sql
    # 未用废弃列
    assert "cache_tokens" not in sql.replace("cache_read_tokens", "").replace(
        "cache_creation_tokens", ""
    )


@pytest.mark.asyncio
async def test_user_top10_orders_by_requests():
    session = _mock_session([_TOP10_ROW])

    await efficiency_cost_repo.get_user_top10(
        session, date(2026, 7, 1), date(2026, 7, 17), metric="requests"
    )

    sql = str(session.execute.await_args.args[0])
    assert "SUM(c.total_requests) DESC" in sql


@pytest.mark.asyncio
async def test_user_top10_illegal_metric_falls_back_to_cost():
    session = _mock_session([])

    await efficiency_cost_repo.get_user_top10(
        session, date(2026, 7, 1), date(2026, 7, 17), metric="; DROP TABLE users;--"
    )

    sql = str(session.execute.await_args.args[0])
    assert "DROP TABLE" not in sql
    assert "SUM(c.internal_cost) DESC" in sql


@pytest.mark.asyncio
async def test_user_top10_uses_nullif_display_name():
    session = _mock_session([])

    await efficiency_cost_repo.get_user_top10(
        session, date(2026, 7, 1), date(2026, 7, 17)
    )

    sql = str(session.execute.await_args.args[0])
    assert "COALESCE(NULLIF(u.display_name, ''), u.username, '')" in sql
    assert "u.is_active = true" in sql
    assert "c.user_id IS NOT NULL" in sql


# ---------------------------------------------------------------------------
# get_top_users (service) — 加 rank，透传参数
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_top_users_service_adds_rank(monkeypatch):
    session = object()
    repo_rows = [
        {"user_id": 1, "user_name": "A", "department": "D1", "internal_cost": 9.0,
         "input_tokens": 1, "output_tokens": 1, "cache_read_tokens": 0,
         "cache_creation_tokens": 0, "total_tokens": 2, "requests": 3},
        {"user_id": 2, "user_name": "B", "department": "D2", "internal_cost": 4.0,
         "input_tokens": 1, "output_tokens": 0, "cache_read_tokens": 0,
         "cache_creation_tokens": 0, "total_tokens": 1, "requests": 1},
    ]
    get_user_top10 = AsyncMock(return_value=repo_rows)
    monkeypatch.setattr(efficiency_cost_service.efficiency_repo, "get_user_top10", get_user_top10)

    result = await efficiency_cost_service.get_top_users(
        session, date(2026, 7, 1), date(2026, 7, 17),
        metric="tokens", cost_type="llm", department_id=[26], project_id=None,
    )

    # cost_type=llm 转成 ct="llm"；metric 放最后一个位置参数（按方案 repo 签名）
    get_user_top10.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), "llm", [26], None, "tokens"
    )
    assert [r["rank"] for r in result] == [1, 2]
    assert result[0]["user_name"] == "A"


@pytest.mark.asyncio
async def test_top_users_service_all_cost_type_becomes_none(monkeypatch):
    session = object()
    get_user_top10 = AsyncMock(return_value=[])
    monkeypatch.setattr(efficiency_cost_service.efficiency_repo, "get_user_top10", get_user_top10)

    await efficiency_cost_service.get_top_users(
        session, date(2026, 7, 1), date(2026, 7, 17),
        metric="cost", cost_type="all", department_id=None, project_id=None,
    )

    # cost_type="all" → ct=None
    args = get_user_top10.await_args.args
    assert args[3] is None


# ---------------------------------------------------------------------------
# API /top-users — 参数转发
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_top_users_forwards_args(monkeypatch):
    session = object()
    service_call = AsyncMock(return_value=[])
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_top_users", service_call
    )

    resp = await efficiency_api.get_top_users(
        None,                    # period
        date(2026, 7, 1),        # start_date
        date(2026, 7, 17),       # end_date
        "tokens",                # metric
        "llm",                   # resource_type
        "department",            # dimension
        "12,34",                 # scope_ids
        session,
        {"id": 1},
    )

    service_call.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), "tokens", "llm", [12, 34], None
    )
    assert resp["code"] == 200


@pytest.mark.asyncio
async def test_api_top_users_project_scope_forwards_project_ids(monkeypatch):
    session = object()
    service_call = AsyncMock(return_value=[])
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_top_users", service_call
    )

    await efficiency_api.get_top_users(
        None, date(2026, 7, 1), date(2026, 7, 17),
        "cost", "", "project", "7,9", session, {"id": 1},
    )

    service_call.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), "cost", "all", None, [7, 9]
    )


# ---------------------------------------------------------------------------
# get_period_token_stats (repo)
# SELECT 顺序: input, output, cache_read, cache_creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_period_token_stats_total_is_sum():
    session = _one_session((1000, 2000, 300, 40))

    result = await efficiency_repo.get_period_token_stats(
        session, date(2026, 7, 1), date(2026, 7, 17)
    )

    assert result == {
        "total": 3340,
        "input": 1000,
        "output": 2000,
        "cache_read": 300,
        "cache_creation": 40,
    }


@pytest.mark.asyncio
async def test_period_token_stats_reads_summary_table():
    session = _one_session((0, 0, 0, 0))

    await efficiency_repo.get_period_token_stats(
        session, date(2026, 7, 1), date(2026, 7, 17)
    )

    sql = str(session.execute.await_args.args[0])
    assert "aihelms.cost_summary_daily" in sql
    # 不得读实时表
    assert "llm_call_logs" not in sql
    assert "mcp_call_logs" not in sql


# ---------------------------------------------------------------------------
# 预算：get_user_budget_top10 (repo)
# SELECT 顺序: user_id, user_name, department, used
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_budget_top10_limits_and_ranks():
    from repositories import efficiency_budget_repo

    session = _mock_session([(3, "Bob", "销售 / 华东", 88.0)])

    result = await efficiency_budget_repo.get_user_budget_top10(
        session, date(2026, 7, 1), date(2026, 7, 31)
    )

    sql = str(session.execute.await_args.args[0])
    assert "LIMIT 10" in sql
    assert "COALESCE(NULLIF(u.display_name, ''), u.username, '')" in sql
    assert "k.key_type IN ('personal_main','personal_scene')" in sql
    assert result == [
        {"rank": 1, "user_name": "Bob", "department": "销售 / 华东", "used": 88.0}
    ]


@pytest.mark.asyncio
async def test_user_personal_key_budget_marks_main():
    from repositories import efficiency_budget_repo

    # SELECT 顺序: user_name, key_name, key_type, budget_limit, used
    session = _mock_session([("Bob", "主Key", "personal_main", 100.0, 30.0)])

    result = await efficiency_budget_repo.get_user_personal_key_budget(
        session, date(2026, 7, 1), date(2026, 7, 31)
    )

    assert result[0]["is_main"] is True
    assert result[0]["budget"] == 100.0
    assert result[0]["used"] == 30.0
    assert result[0]["execution_rate"] == 30.0
