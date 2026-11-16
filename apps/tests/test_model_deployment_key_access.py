"""部署编辑只在影响访问的字段变化时才重算主 Key 模型授权。"""

from unittest.mock import AsyncMock

import pytest

from models.db import Model, ModelDeployment
from repositories import credential_repo, model_repo
from services import model_service

MODEL_NAME = "qa-deployment-model"


@pytest.fixture
def deployment_case(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[AsyncMock, AsyncMock, ModelDeployment]:
    model = Model(
        id=7,
        model_id=MODEL_NAME,
        is_published=True,
        requires_approval=True,
        visibility_type="all",
    )
    deployment = ModelDeployment(
        id=3,
        model_id=model.id,
        credential_id=11,
        litellm_model_id="litellm-dep-3",
        litellm_params={"model": "moonshot/kimi", "input_cost_per_token": 0.000001},
        model_info={},
        is_active=True,
        billing_type="token",
    )
    credential = type(
        "Credential",
        (),
        {
            "id": 11,
            "credential_name": "qa-cred",
            "credential_info": {"format": "openai"},
            "credential_values": {"api_base": "https://api.invalid/v1"},
            "is_active": True,
            "litellm_synced": True,
        },
    )()

    monkeypatch.setattr(
        model_repo, "find_deployment_by_id", AsyncMock(return_value=deployment)
    )
    monkeypatch.setattr(model_repo, "find_by_id", AsyncMock(return_value=model))
    monkeypatch.setattr(
        credential_repo, "find_by_id", AsyncMock(return_value=credential)
    )
    monkeypatch.setattr(
        model_service, "_build_litellm_params_for_sync",
        AsyncMock(side_effect=lambda params, *_args, **_kwargs: dict(params)),
    )
    monkeypatch.setattr(
        model_service, "_ensure_litellm_credential_synced", AsyncMock()
    )
    monkeypatch.setattr(
        model_service.litellm_client, "update_model", AsyncMock()
    )
    resync = AsyncMock()
    monkeypatch.setattr(
        model_service, "_sync_model_key_access_after_deployment", resync
    )
    anthropic_resync = AsyncMock()
    monkeypatch.setattr(
        model_service, "_sync_keys_anthropic_access", anthropic_resync
    )
    return resync, anthropic_resync, deployment


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "edit",
    [
        {"litellm_params": {"model": "moonshot/kimi", "input_cost_per_token": 0.000004}},
        {"billing_type": "per_call", "cost_per_call": 0.02},
        {"is_active": False},
        {"is_active": True},
        {"credential_id": 12},
        {"deploy_name": "改个名字"},
        {"monthly_call_quota": 5000},
        {"model_info": {"internal_input_cost": 0.000002}},
    ],
)
async def test_editing_deployment_never_touches_user_keys(
    deployment_case: tuple[AsyncMock, AsyncMock, ModelDeployment],
    edit: dict,
) -> None:
    resync, anthropic_resync, deployment = deployment_case
    await model_service.update_deployment(AsyncMock(), deployment.id, **edit)
    resync.assert_not_awaited()
    anthropic_resync.assert_not_awaited()


@pytest.mark.asyncio
async def test_first_litellm_sync_builds_key_access(
    deployment_case: tuple[AsyncMock, AsyncMock, ModelDeployment],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resync, _anthropic_resync, deployment = deployment_case
    deployment.litellm_model_id = None
    monkeypatch.setattr(model_service, "_sync_deployment_to_litellm", AsyncMock())
    await model_service.update_deployment(
        AsyncMock(), deployment.id, cost_per_call=0.01
    )
    resync.assert_awaited_once()
