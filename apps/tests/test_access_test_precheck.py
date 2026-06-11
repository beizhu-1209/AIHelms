from types import SimpleNamespace

import pytest

from services import access_test_precheck


class FakeSession:
    pass


async def fake_find_personal_main_active(session, user_id: int):
    return SimpleNamespace(
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
    )

    assert key is not None
    assert detail is None
