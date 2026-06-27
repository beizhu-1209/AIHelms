from types import SimpleNamespace

import pytest

from exceptions import ValidationError
from services import ai_key_service


@pytest.mark.asyncio
async def test_create_key_rejects_manual_main_key() -> None:
    with pytest.raises(ValidationError):
        await ai_key_service.create_key(
            None,
            name="main",
            key_type=ai_key_service.KEY_TYPE_PERSONAL_MAIN,
            owner_type="user",
            owner_id=1,
            created_by=1,
        )


def test_assign_key_rate_limits_total_sets_main_fields() -> None:
    key = SimpleNamespace()

    ai_key_service._assign_key_rate_limits(
        key,
        ai_key_service.RATE_LIMIT_MODE_TOTAL,
        tpm_limit=1000,
        rpm_limit=60,
        max_parallel_requests=3,
    )

    assert key.rate_limit_mode == "total"
    assert key.tpm_limit == 1000
    assert key.rpm_limit == 60
    assert key.max_parallel_requests == 3


def test_assign_key_rate_limits_none_clears_main_fields() -> None:
    key = SimpleNamespace(tpm_limit=1000, rpm_limit=60, max_parallel_requests=3)

    ai_key_service._assign_key_rate_limits(
        key,
        ai_key_service.RATE_LIMIT_MODE_NONE,
        tpm_limit=1000,
        rpm_limit=60,
        max_parallel_requests=3,
    )

    assert key.rate_limit_mode == "none"
    assert key.tpm_limit is None
    assert key.rpm_limit is None
    assert key.max_parallel_requests is None


@pytest.mark.asyncio
async def test_build_key_metadata_per_model_filters_authorized_and_expands_anthropic(
    monkeypatch,
) -> None:
    key = SimpleNamespace(
        id=7,
        key_type="personal_scene",
        rate_limit_mode="per_model",
        models=["kimi26"],
    )
    limits = [SimpleNamespace(model_id=1, tpm=1000, rpm=60)]
    model = SimpleNamespace(id=1, model_id="kimi26")

    async def fake_find_by_key_id(session, key_id):
        return limits

    async def fake_find_by_id(session, model_id):
        return model

    async def fake_find_anthropic(session, model_ids):
        return ["kimi26"]

    monkeypatch.setattr(
        ai_key_service.ai_key_model_limit_repo,
        "find_by_key_id",
        fake_find_by_key_id,
    )
    monkeypatch.setattr(ai_key_service.model_repo, "find_by_id", fake_find_by_id)
    monkeypatch.setattr(
        ai_key_service.model_repo,
        "find_model_ids_with_anthropic_deployments",
        fake_find_anthropic,
    )

    metadata = await ai_key_service._build_key_metadata(None, key)

    assert metadata["model_tpm_limit"] == {
        "kimi26": 1000,
        "kimi26(Anthropic)": 1000,
    }
    assert metadata["model_rpm_limit"] == {
        "kimi26": 60,
        "kimi26(Anthropic)": 60,
    }
