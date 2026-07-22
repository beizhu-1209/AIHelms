from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.v1 import efficiency as efficiency_api
from repositories import efficiency_cost_repo
from services import export_task_builders


def _mock_session(rows: list[tuple]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.fetchall.return_value = rows
    session.execute.return_value = result
    return session


@pytest.mark.asyncio
async def test_scope_users_department_penetrates_subtree_and_maps_path():
    row = (7, "alice", "Alice", "技术中心 / 前端组", 12.5, 10.0, 30, 100, 200, 5, 8)
    session = _mock_session([row])

    result = await efficiency_cost_repo.get_cost_detail_scope_users(
        session, date(2026, 7, 1), date(2026, 7, 17), "department", 26, None
    )

    sql = str(session.execute.await_args.args[0])
    params = session.execute.await_args.args[1]
    assert "WITH RECURSIVE" in sql
    assert "subtree" in sql
    assert "ud.department_id IN (SELECT id FROM subtree)" in sql
    assert params["scope_id"] == 26

    assert result == [
        {
            "user_id": 7,
            "user_name": "Alice",
            "department": "技术中心 / 前端组",
            "internal_cost": 12.5,
            "external_cost": 10.0,
            "cost_diff": 2.5,
            "requests": 30,
            "input_tokens": 100,
            "output_tokens": 200,
            "cache_read_tokens": 5,
            "cache_creation_tokens": 8,
        }
    ]


@pytest.mark.asyncio
async def test_scope_users_project_filters_by_user_projects():
    session = _mock_session([])

    await efficiency_cost_repo.get_cost_detail_scope_users(
        session, date(2026, 7, 1), date(2026, 7, 17), "project", 8, "llm"
    )

    sql = str(session.execute.await_args.args[0])
    params = session.execute.await_args.args[1]
    assert "up.project_id = :scope_id" in sql
    assert "subtree" not in sql.split("member")[0] or "up.project_id" in sql
    assert params["scope_id"] == 8
    assert params["cost_type"] == "llm"


@pytest.mark.asyncio
async def test_scope_users_falls_back_to_username_when_display_name_empty():
    row = (9, "bob", "", "", 1.0, 1.0, 1, 0, 0, 0, 0)
    session = _mock_session([row])

    result = await efficiency_cost_repo.get_cost_detail_scope_users(
        session, date(2026, 7, 1), date(2026, 7, 17), "department", 1, None
    )

    assert result[0]["user_name"] == "bob"
    assert result[0]["department"] == ""


@pytest.mark.asyncio
async def test_api_scope_users_forwards_args(monkeypatch):
    session = object()
    service_call = AsyncMock(return_value=[])
    monkeypatch.setattr(
        efficiency_api.efficiency_service,
        "get_cost_detail_scope_users",
        service_call,
    )

    resp = await efficiency_api.get_cost_detail_scope_users(
        None,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "llm",
        "department",
        26,
        session,
        {"id": 1},
    )

    service_call.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), "department", 26, "llm"
    )
    assert resp["code"] == 200


@pytest.mark.asyncio
async def test_export_department_cost_includes_token_columns(monkeypatch):
    detail = {
        "department": [
            {
                "scope_name": "技术中心",
                "department": "技术中心",
                "scope_id": 26,
                "llm_cost": 100.0,
                "mcp_cost": 20.0,
                "total_cost": 120.0,
                "external_cost": 110.0,
                "cost_diff": 10.0,
                "requests": 50,
                "input_tokens": 1000,
                "output_tokens": 2000,
                "cache_read_tokens": 300,
                "cache_creation_tokens": 40,
                "per_capita_cost": 12.0,
                "active_per_capita_cost": 15.0,
                "cost_change": 5.0,
            }
        ]
    }
    monkeypatch.setattr(
        export_task_builders.efficiency_service,
        "get_cost_detail",
        AsyncMock(return_value=detail),
    )

    header, rows = await export_task_builders._build_efficiency_rows(
        object(),
        "cost_department",
        {"dimension": "department", "start_date": "2026-07-01", "end_date": "2026-07-17"},
    )

    assert "输入Token" in header
    assert "输出Token" in header
    assert "缓存读Token" in header
    assert "缓存写Token" in header
    assert len(header) == len(rows[0])
    token_start = header.index("输入Token")
    assert rows[0][token_start : token_start + 4] == [1000, 2000, 300, 40]
