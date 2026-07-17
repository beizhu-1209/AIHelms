from unittest.mock import AsyncMock

import pytest

from services import usage_log_service


@pytest.mark.asyncio
async def test_llm_filters_returns_actual_user_key_pairs(monkeypatch):
    session = object()
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "llm_log_filters",
        AsyncMock(
            return_value={
                "user_ids": [7],
                "ai_key_ids": [19],
                "models": [],
                "providers": [],
                "user_key_pairs": [(7, 19)],
            }
        ),
    )
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "load_users",
        AsyncMock(return_value={7: {"id": 7, "username": "user-7"}}),
    )
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "load_ai_keys",
        AsyncMock(return_value={19: {"id": 19, "name": "shared-key"}}),
    )

    result = await usage_log_service.llm_filters(session)

    assert result["user_key_pairs"] == [{"user_id": 7, "ai_key_id": 19}]


@pytest.mark.asyncio
async def test_mcp_filters_returns_actual_user_key_pairs(monkeypatch):
    session = object()
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "mcp_log_filters",
        AsyncMock(
            return_value={
                "user_ids": [8],
                "server_ids": [],
                "ai_key_ids": [20],
                "tool_names": [],
                "user_key_pairs": [(8, 20)],
            }
        ),
    )
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "load_users",
        AsyncMock(return_value={8: {"id": 8, "username": "user-8"}}),
    )
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "load_ai_keys",
        AsyncMock(return_value={20: {"id": 20, "name": "shared-key"}}),
    )
    monkeypatch.setattr(
        usage_log_service.usage_log_repo,
        "load_mcp_servers",
        AsyncMock(return_value={}),
    )

    result = await usage_log_service.mcp_filters(session)

    assert result["user_key_pairs"] == [{"user_id": 8, "ai_key_id": 20}]
