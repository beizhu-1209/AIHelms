from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services import usage_log_service

ADMIN_USER = {"id": 3, "identity_type": "user"}


@pytest.mark.asyncio
async def test_can_view_log_content_config_enabled_returns_true(monkeypatch):
    monkeypatch.setattr(usage_log_service.settings, "log_detail_content_visible_to_admin", True)

    assert await usage_log_service.can_view_log_content(object(), ADMIN_USER) is True


@pytest.mark.asyncio
async def test_can_view_log_content_disabled_normal_admin_returns_false(monkeypatch):
    monkeypatch.setattr(usage_log_service.settings, "log_detail_content_visible_to_admin", False)
    monkeypatch.setattr(
        usage_log_service.user_repo,
        "find_user_by_id",
        AsyncMock(return_value=SimpleNamespace(is_super_admin=False)),
    )

    assert await usage_log_service.can_view_log_content(object(), ADMIN_USER) is False


@pytest.mark.asyncio
async def test_can_view_log_content_disabled_super_admin_returns_true(monkeypatch):
    monkeypatch.setattr(usage_log_service.settings, "log_detail_content_visible_to_admin", False)
    monkeypatch.setattr(
        usage_log_service.user_repo,
        "find_user_by_id",
        AsyncMock(return_value=SimpleNamespace(is_super_admin=True)),
    )

    assert await usage_log_service.can_view_log_content(object(), ADMIN_USER) is True


@pytest.mark.asyncio
async def test_get_mcp_log_content_hidden_strips_payload(monkeypatch):
    log = SimpleNamespace(user_id=1, ai_key_id=2, server_id=3, request_args={"q": 1}, response_full="secret")
    monkeypatch.setattr(usage_log_service.usage_log_repo, "find_mcp_log_by_id", AsyncMock(return_value=log))
    for loader in ("load_users", "load_ai_keys", "load_mcp_servers"):
        monkeypatch.setattr(usage_log_service.usage_log_repo, loader, AsyncMock(return_value={}))
    monkeypatch.setattr(usage_log_service, "_serialize_mcp", lambda *args: {"id": 9})

    result = await usage_log_service.get_mcp_log(object(), 9, content_visible=False)

    assert result["content_hidden"] is True
    assert result["request_args"] is None
    assert result["response_full"] is None
