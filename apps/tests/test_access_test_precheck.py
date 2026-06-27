from types import SimpleNamespace

import pytest

from services import access_test_precheck


class FakeSession:
    pass


async def fake_find_personal_main_active(session, user_id: int):
    return SimpleNamespace(
        id=7,
        is_active=True,
        litellm_key_id="sk-test-key",
        models=["deepseek-chat"],
    )


async def fake_find_deployments_by_model_active(session, model_id: int):
    return [SimpleNamespace(is_active=True, credential=SimpleNamespace(is_active=True))]


@pytest.mark.asyncio
async def test_access_test_precheck_no_identity_returns_no_identity(
    monkeypatch,
) -> None:
    async def fake_find_personal_main(session, user_id: int):
        return None

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main,
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(id=1, is_active=True, is_published=True),
        "deepseek-chat",
        is_admin=False,
    )

    assert key is None
    assert detail is not None
    assert detail["category"] == "no_identity"


@pytest.mark.asyncio
async def test_access_test_precheck_unauthorized_model_returns_permission_help(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(id=1, is_active=True, is_published=True),
        "gpt-4o",
        is_admin=False,
    )

    assert key is not None
    assert detail is not None
    assert detail["category"] == "model_not_authorized"


@pytest.mark.asyncio
async def test_access_test_precheck_unpublished_model_returns_publish_help(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(id=1, is_active=True, is_published=False),
        "deepseek-chat",
        is_admin=False,
    )

    assert key is not None
    assert detail is not None
    assert detail["category"] == "model_not_published"


@pytest.mark.asyncio
async def test_access_test_precheck_no_active_deployment_returns_deployment_help(
    monkeypatch,
) -> None:
    async def fake_find_deployments_by_model(session, model_id: int):
        return [SimpleNamespace(is_active=False, credential=None)]

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )
    monkeypatch.setattr(
        access_test_precheck.model_repo,
        "find_deployments_by_model",
        fake_find_deployments_by_model,
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(id=1, is_active=True, is_published=True),
        "deepseek-chat",
        is_admin=False,
    )

    assert key is not None
    assert detail is not None
    assert detail["category"] == "no_active_deployment"


@pytest.mark.asyncio
async def test_access_test_precheck_ready_returns_key_without_error(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )
    monkeypatch.setattr(
        access_test_precheck.model_repo,
        "find_deployments_by_model",
        fake_find_deployments_by_model_active,
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(id=1, is_active=True, is_published=True),
        "deepseek-chat",
        is_admin=False,
    )

    assert key is not None
    assert detail is None


@pytest.mark.asyncio
async def test_access_test_precheck_admin_unpublished_model_grants_access(
    monkeypatch,
) -> None:
    updates = []

    async def fake_update_key(session, key_id: int, **kwargs):
        updates.append({"key_id": key_id, **kwargs})
        return {}

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )
    monkeypatch.setattr(
        access_test_precheck.model_repo,
        "find_deployments_by_model",
        fake_find_deployments_by_model_active,
    )
    monkeypatch.setattr(
        access_test_precheck.ai_key_service, "update_key", fake_update_key
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(
            id=1,
            model_id="draft-model",
            is_active=True,
            is_published=False,
        ),
        "draft-model",
        is_admin=True,
    )

    assert key is not None
    assert detail is None
    assert updates == [
        {
            "key_id": 7,
            "models": ["deepseek-chat", "draft-model"],
            "update_rate_limit": False,
        }
    ]


@pytest.mark.asyncio
async def test_access_test_precheck_admin_authorized_model_does_not_grant_again(
    monkeypatch,
) -> None:
    async def fake_find_personal_main(session, user_id: int):
        return SimpleNamespace(
            id=7,
            is_active=True,
            litellm_key_id="sk-test-key",
            models=["draft-model"],
        )

    async def fake_update_key(session, key_id: int, **kwargs):
        raise AssertionError("update_key should not be called")

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main,
    )
    monkeypatch.setattr(
        access_test_precheck.model_repo,
        "find_deployments_by_model",
        fake_find_deployments_by_model_active,
    )
    monkeypatch.setattr(
        access_test_precheck.ai_key_service, "update_key", fake_update_key
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(
            id=1,
            model_id="draft-model",
            is_active=True,
            is_published=False,
        ),
        "draft-model",
        is_admin=True,
    )

    assert key is not None
    assert detail is None


@pytest.mark.asyncio
async def test_access_test_precheck_admin_inactive_model_returns_deployment_help(
    monkeypatch,
) -> None:
    async def fake_update_key(session, key_id: int, **kwargs):
        raise AssertionError("update_key should not be called")

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )
    monkeypatch.setattr(
        access_test_precheck.ai_key_service, "update_key", fake_update_key
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(
            id=1,
            model_id="draft-model",
            is_active=False,
            is_published=False,
        ),
        "draft-model",
        is_admin=True,
    )

    assert key is not None
    assert detail is not None
    assert detail["category"] == "no_active_deployment"


@pytest.mark.asyncio
async def test_access_test_precheck_admin_no_deployment_does_not_grant(
    monkeypatch,
) -> None:
    async def fake_find_deployments_by_model(session, model_id: int):
        return [SimpleNamespace(is_active=False, credential=None)]

    async def fake_update_key(session, key_id: int, **kwargs):
        raise AssertionError("update_key should not be called")

    monkeypatch.setattr(
        access_test_precheck.ai_key_repo,
        "find_personal_main",
        fake_find_personal_main_active,
    )
    monkeypatch.setattr(
        access_test_precheck.model_repo,
        "find_deployments_by_model",
        fake_find_deployments_by_model,
    )
    monkeypatch.setattr(
        access_test_precheck.ai_key_service, "update_key", fake_update_key
    )

    key, detail = await access_test_precheck.precheck_access_test(
        FakeSession(),
        1,
        SimpleNamespace(
            id=1,
            model_id="draft-model",
            is_active=True,
            is_published=False,
        ),
        "draft-model",
        is_admin=True,
    )

    assert key is not None
    assert detail is not None
    assert detail["category"] == "no_active_deployment"
