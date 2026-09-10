from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from exceptions import ConflictError
from models.db import AiKey, User
from repositories import ai_key_repo, model_repo, resource_application_repo, user_repo
from services import ai_key_service, resource_application_service, user_service


@pytest.mark.asyncio
@pytest.mark.parametrize('published,active', [(False, True), (True, False), (False, False)])
async def test_approval_rejects_unavailable_model(monkeypatch, published, active):
    app = SimpleNamespace(status='pending', resource_type='model', resource_id=1)
    monkeypatch.setattr(resource_application_repo, 'find_by_id', AsyncMock(return_value=app))
    monkeypatch.setattr(model_repo, 'find_by_id', AsyncMock(return_value=SimpleNamespace(is_published=published, is_active=active)))
    grant = AsyncMock()
    monkeypatch.setattr(resource_application_service, '_grant_resource', grant)
    with pytest.raises(ConflictError, match='不能批准'):
        await resource_application_service.approve_application(AsyncMock(), 1, 9)
    assert app.status == 'pending'
    grant.assert_not_awaited()


@pytest.mark.asyncio
async def test_inactive_key_keeps_initialization_pending(monkeypatch):
    user = User(id=1, is_active=True, is_admin=False, model_departments_initialized=False)
    key = AiKey(id=2, is_active=False, models=[], rate_limit_mode='none')
    monkeypatch.setattr(user_repo, 'find_user_departments', AsyncMock(return_value=[SimpleNamespace(department_id=2)]))
    monkeypatch.setattr(model_repo, 'initialize_user_model_visibility', AsyncMock())
    monkeypatch.setattr(ai_key_repo, 'find_personal_main', AsyncMock(return_value=key))
    lookup = AsyncMock(return_value=['public-model'])
    monkeypatch.setattr(model_repo, 'find_public_model_ids_for_user', lookup)
    sync = AsyncMock()
    monkeypatch.setattr(ai_key_service, '_sync_key_to_litellm', sync)
    await user_service.initialize_pending_model_access(AsyncMock(), user)
    assert user.model_departments_initialized is False
    sync.assert_not_awaited()
    await user_service.initialize_pending_model_access(AsyncMock(), user, allow_inactive_key=True)
    assert key.models == ['public-model']
    assert user.model_departments_initialized is True
    sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_disabled_user_created_with_disabled_deny_all_key(monkeypatch):
    user = User(id=1, is_active=False, litellm_user_id='test-user')
    monkeypatch.setattr(ai_key_repo, 'find_personal_main', AsyncMock(return_value=None))
    monkeypatch.setattr(user_repo, 'find_user_by_id', AsyncMock(return_value=user))
    monkeypatch.setattr(ai_key_service, 'get_public_resources', AsyncMock(return_value={'models':['public-model'], 'skills':[], 'mcps':[], 'agents':[]}))
    async def create(session, key):
        key.id = 2
        return key
    monkeypatch.setattr(ai_key_repo, 'create', create)
    remote = AsyncMock(return_value={'key':'sk-synthetic'})
    monkeypatch.setattr(ai_key_service.litellm_client, 'create_key', remote)
    key = await ai_key_service.create_personal_main_key(AsyncMock(), 1, 'test-user')
    assert key.is_active is False
    assert key.models == []
    assert remote.call_args.kwargs['models'] == ['no-default-models']
    assert remote.call_args.kwargs['max_budget'] == 0.0
