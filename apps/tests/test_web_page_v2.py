from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v2.web_pages import router
from core.deps import get_current_user, get_db
from services import web_page_service


def _key() -> dict:
    return {
        "id": 49,
        "name": "main",
        "description": "",
        "key_type": "personal_main",
        "litellm_key_id": "sk-example",
        "litellm_key_alias": "internal-alias",
        "owner_type": "user",
        "owner_id": 50,
        "created_by": 50,
        "models": ["model-a"],
        "mcps": [2],
        "skills": [1],
        "agents": [7],
        "budget_limit": None,
        "budget_used": "0",
        "budget_hard_limit": False,
        "budget_duration": "30d",
        "budget_scope": "unified",
        "budget_models_total": None,
        "budget_mcps_total": None,
        "budget_models_per": "unified",
        "budget_mcps_per": "unified",
        "model_budgets": {},
        "mcp_budgets": {},
        "rate_limit_mode": "none",
        "tpm_limit": None,
        "rpm_limit": None,
        "max_parallel_requests": None,
        "is_active": True,
        "expires_at": None,
    }


def _user() -> dict:
    return {
        "id": 50,
        "username": "zhanghaotian",
        "email": "zhanghaotian@example.com",
        "display_name": "",
        "avatar": "",
        "position": "",
        "is_admin": True,
        "departments": [],
        "permissions": ["admin"],
        "roles": [{"name": "admin"}],
    }


def _page(items: list[dict], page_size: int = 100) -> dict:
    return {"items": items, "total": len(items), "page": 1, "page_size": page_size}


def _agent() -> dict:
    return {
        "id": 7,
        "name": "Agent",
        "icon_url": "",
        "description": "",
        "platform": "Maxkb",
        "category": "general",
        "chat_url": "",
        "tags": [],
        "requires_approval": False,
        "status": "online",
        "user_count": 0,
    }


def _skill() -> dict:
    return {
        "id": 1,
        "name": "Skill",
        "icon_url": "",
        "description": "",
        "category": "general",
        "tags": [],
        "author": "",
        "requires_approval": False,
        "install_count": 0,
    }


def _mcp() -> dict:
    return {
        "id": 2,
        "name": "MCP",
        "icon_url": "",
        "description": "",
        "category": "general",
        "tags": [],
        "author": "",
        "requires_approval": False,
        "status": "healthy",
        "call_count": 0,
        "url": "https://upstream.example/mcp",
        "credentials": {"token": "secret"},
        "authorization_url": "https://upstream.example/auth",
        "litellm_synced": True,
        "health_check_error": "internal error",
        "internal_cost_per_call": 1,
    }


def test_hub_user_keeps_admin_switch_flag_and_drops_permissions():
    result = web_page_service._hub_user(_user())

    assert result["is_admin"] is True
    assert "permissions" not in result
    assert "roles" not in result


def test_hub_key_keeps_access_fields_and_drops_admin_fields():
    result = web_page_service._hub_key(_key())

    assert result["key_value"] == "sk-example"
    assert result["models"] == ["model-a"]
    for field in ("litellm_key_alias", "owner_type", "owner_id", "created_by"):
        assert field not in result


def test_hub_mcp_drops_upstream_and_admin_fields():
    result = web_page_service._hub_mcp(_mcp())

    assert result["name"] == "MCP"
    for field in (
        "url",
        "credentials",
        "authorization_url",
        "litellm_synced",
        "health_check_error",
        "internal_cost_per_call",
    ):
        assert field not in result


@pytest.mark.asyncio
async def test_get_model_square_uses_one_consistent_main_key_path():
    with (
        patch.object(
            web_page_service.model_service,
            "get_all_active_models",
            AsyncMock(
                return_value=[{"model_id": "model-a", "base_url": "https://api"}]
            ),
        ),
        patch.object(
            web_page_service.ai_key_service,
            "get_my_keys",
            AsyncMock(
                return_value={"personal": [_key()], "department": [], "project": []}
            ),
        ),
    ):
        result = await web_page_service.get_model_square(AsyncMock(), 50)

    assert result["keys"]["personal"]["main_key"]["key_value"] == "sk-example"
    assert "department" not in result["keys"]
    assert result["models"][0]["base_url"] == "https://api"


@pytest.mark.asyncio
async def test_get_ai_identity_degrades_noncritical_blocks(caplog):
    async def fail_overview(*_args):
        raise RuntimeError("overview unavailable")

    with (
        patch.object(
            web_page_service.auth_service,
            "get_current_user_info",
            AsyncMock(return_value=_user()),
        ),
        patch.object(
            web_page_service.ai_key_service,
            "get_my_keys",
            AsyncMock(
                return_value={"personal": [_key()], "department": [], "project": []}
            ),
        ),
        patch.object(
            web_page_service.efficiency_service,
            "get_user_overview",
            fail_overview,
        ),
        patch.object(
            web_page_service.efficiency_service,
            "get_trend",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            web_page_service.resource_application_service,
            "list_applications",
            AsyncMock(return_value=_page([], 10)),
        ),
        patch.object(
            web_page_service.mcp_service,
            "list_servers",
            AsyncMock(side_effect=RuntimeError("MCP unavailable")),
        ),
        patch.object(
            web_page_service.skill_service,
            "list_skills",
            AsyncMock(return_value=_page([_skill()], 200)),
        ),
        patch.object(
            web_page_service.model_service,
            "get_all_active_models",
            AsyncMock(side_effect=RuntimeError("models unavailable")),
        ),
    ):
        result = await web_page_service.get_ai_identity(AsyncMock(), 50)

    assert result["overview"] is None
    assert result["keys"]["personal"]["main_key"]["id"] == 49
    assert result["mcp"]["items"] == []
    assert result["models"] == []
    assert result["skills"]["items"][0]["name"] == "Skill"
    assert "overview unavailable" in caplog.text
    assert "MCP list unavailable" in caplog.text
    assert "model list unavailable" in caplog.text


@pytest.mark.asyncio
async def test_get_ai_identity_does_not_hide_critical_user_failure():
    with patch.object(
        web_page_service.auth_service,
        "get_current_user_info",
        AsyncMock(side_effect=RuntimeError("user unavailable")),
    ):
        with pytest.raises(RuntimeError, match="user unavailable"):
            await web_page_service.get_ai_identity(AsyncMock(), 50)


@pytest.mark.asyncio
async def test_get_ai_identity_does_not_hide_critical_key_failure():
    with (
        patch.object(
            web_page_service.auth_service,
            "get_current_user_info",
            AsyncMock(return_value=_user()),
        ),
        patch.object(
            web_page_service.ai_key_service,
            "get_my_keys",
            AsyncMock(side_effect=RuntimeError("key unavailable")),
        ),
    ):
        with pytest.raises(RuntimeError, match="key unavailable"):
            await web_page_service.get_ai_identity(AsyncMock(), 50)


def _client(authenticated: bool) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v2")

    async def db_override():
        yield AsyncMock()

    app.dependency_overrides[get_db] = db_override
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 50,
            "username": "zhanghaotian",
        }
    return TestClient(app)


@pytest.mark.parametrize(
    ("path", "service_name"),
    (
        ("/api/v2/ai-identity", "get_ai_identity"),
        ("/api/v2/agent-center", "get_agent_center"),
        ("/api/v2/market", "get_market"),
        ("/api/v2/model-square", "get_model_square"),
    ),
)
def test_v2_router_uses_standard_success_envelope(path: str, service_name: str):
    with patch.object(
        web_page_service, service_name, AsyncMock(return_value={"ok": True})
    ):
        response = _client(True).get(path)

    assert response.status_code == 200
    assert response.json() == {"code": 200, "message": "ok", "data": {"ok": True}}


def test_v2_router_requires_existing_login_authentication():
    response = _client(False).get("/api/v2/model-square")

    assert response.status_code == 401
