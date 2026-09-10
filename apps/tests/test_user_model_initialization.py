from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from services import ai_key_service, user_service
from repositories import ai_key_repo, model_repo, user_repo


@pytest.mark.asyncio
@pytest.mark.parametrize('initialized,departments,expected', [(False, [1], 1), (False, [], 0), (True, [2], 0)])
async def test_department_initialization_runs_once(monkeypatch, initialized, departments, expected):
    user = SimpleNamespace(id=1, model_departments_initialized=initialized, is_active=True, is_admin=False)
    monkeypatch.setattr(user_repo, 'find_user_by_id', AsyncMock(return_value=user))
    monkeypatch.setattr(user_repo, 'replace_user_departments', AsyncMock())
    monkeypatch.setattr(user_repo, 'find_user_departments', AsyncMock(return_value=[SimpleNamespace(department_id=2)]))
    snapshot = AsyncMock()
    grants = AsyncMock(return_value=True)
    monkeypatch.setattr(model_repo, 'initialize_user_model_visibility', snapshot)
    monkeypatch.setattr(ai_key_service, 'initialize_personal_department_models', grants)
    await user_service.update_user_departments(AsyncMock(), 1, departments)
    assert snapshot.await_count == expected
    assert grants.await_count == expected
    assert user.model_departments_initialized == (initialized or bool(departments))


@pytest.mark.asyncio
async def test_initial_department_grants_preserve_existing_approval(monkeypatch):
    key = SimpleNamespace(models=['approved-model'], is_active=True, rate_limit_mode='none')
    monkeypatch.setattr(ai_key_repo, 'find_personal_main', AsyncMock(return_value=key))
    monkeypatch.setattr(model_repo, 'find_public_model_ids_for_user', AsyncMock(return_value=['public-model']))
    monkeypatch.setattr(ai_key_service, 'flag_modified', lambda *args: None)
    sync = AsyncMock()
    monkeypatch.setattr(ai_key_service, '_sync_key_to_litellm', sync)
    await ai_key_service.initialize_personal_department_models(AsyncMock(), 1)
    assert key.models == ['approved-model', 'public-model']
    sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_creation_snapshots_departments_before_creating_key(monkeypatch):
    events = []
    user = SimpleNamespace(id=1, litellm_user_id=None)
    monkeypatch.setattr(user_repo, 'find_user_by_username_or_email', AsyncMock(return_value=None))
    monkeypatch.setattr(user_repo, 'create_user', AsyncMock(return_value=user))
    monkeypatch.setattr(user_service, 'get_password_hash', lambda value: 'hash')
    monkeypatch.setattr(user_service, '_serialize_user', lambda value: {'id': value.id})
    monkeypatch.setattr(user_service.litellm_client, 'create_user', AsyncMock())
    async def departments(*args): events.append('departments')
    async def visibility(*args): events.append('visibility')
    async def main_key(*args): events.append('key')
    monkeypatch.setattr(user_repo, 'replace_user_departments', departments)
    monkeypatch.setattr(model_repo, 'initialize_user_model_visibility', visibility)
    monkeypatch.setattr(ai_key_service, 'create_personal_main_key', main_key)
    await user_service.create_user(AsyncMock(), 'test', 'test@example.invalid', 'password', department_ids=[2])
    assert events == ['departments', 'visibility', 'key']
    assert user.model_departments_initialized is True


@pytest.mark.asyncio
async def test_disabled_user_first_department_remains_pending(monkeypatch):
    user = SimpleNamespace(id=1, model_departments_initialized=False, is_active=False, is_admin=False)
    monkeypatch.setattr(user_repo, 'find_user_by_id', AsyncMock(return_value=user))
    monkeypatch.setattr(user_repo, 'replace_user_departments', AsyncMock())
    monkeypatch.setattr(user_repo, 'find_user_departments', AsyncMock(return_value=[SimpleNamespace(department_id=2)]))
    snapshot = AsyncMock()
    grants = AsyncMock(return_value=True)
    monkeypatch.setattr(model_repo, 'initialize_user_model_visibility', snapshot)
    monkeypatch.setattr(ai_key_service, 'initialize_personal_department_models', grants)
    await user_service.update_user_departments(AsyncMock(), 1, [2])
    assert user.model_departments_initialized is False
    snapshot.assert_not_awaited()
    grants.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabling_pending_user_initializes_before_enabling_keys(monkeypatch):
    user = SimpleNamespace(id=1, is_active=False, is_admin=False, model_departments_initialized=False)
    monkeypatch.setattr(user_repo, 'find_user_by_id', AsyncMock(return_value=user))
    monkeypatch.setattr(user_repo, 'find_user_departments', AsyncMock(return_value=[SimpleNamespace(department_id=2)]))
    monkeypatch.setattr(user_service, '_serialize_user_detail', lambda value: {})
    events = []
    async def snapshot(*args): events.append('snapshot')
    async def grant(*args, **kwargs):
        events.append('grant')
        assert kwargs['allow_inactive_key'] is True
        return True
    async def enable(*args): events.append('enable')
    monkeypatch.setattr(model_repo, 'initialize_user_model_visibility', snapshot)
    monkeypatch.setattr(ai_key_service, 'initialize_personal_department_models', grant)
    monkeypatch.setattr(ai_key_service, 'sync_user_keys_active', enable)
    await user_service.update_user(AsyncMock(), 1, is_active=True)
    assert events == ['snapshot', 'grant', 'enable']
    assert user.model_departments_initialized is True
