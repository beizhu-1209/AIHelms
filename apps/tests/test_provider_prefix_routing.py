from types import SimpleNamespace

import pytest

from services.model_service import _build_litellm_params_for_sync


class FakeResult:
    def __init__(self, prefix_info: object) -> None:
        self.prefix_info = prefix_info

    def scalar_one_or_none(self) -> object:
        return self.prefix_info


class FakeSession:
    def __init__(self, provider_type: str, prefix: str, needs_v1: bool) -> None:
        self.provider_type = provider_type
        self.prefix_info = SimpleNamespace(prefix=prefix, needs_v1=needs_v1)

    async def scalar(self, statement: object) -> str:
        return self.provider_type

    async def execute(self, statement: object) -> FakeResult:
        return FakeResult(self.prefix_info)


def build_credential(api_base: str) -> SimpleNamespace:
    return SimpleNamespace(
        provider_id=1,
        credential_name="test-credential",
        credential_values={"api_base": api_base},
        credential_info={"format": "openai"},
    )


@pytest.mark.asyncio
async def test_tencent_chat_uses_native_prefix_and_keeps_v1() -> None:
    result = await _build_litellm_params_for_sync(
        {"model": "hy3"},
        SimpleNamespace(model_id="hy3", category="chat"),
        build_credential("https://tokenhub.tencentmaas.com/v1"),
        FakeSession("tencent", "tencent", False),
    )

    assert result["model"] == "tencent/hy3"
    assert result["api_base"] == "https://tokenhub.tencentmaas.com/v1"


@pytest.mark.asyncio
async def test_xai_chat_uses_native_prefix_and_keeps_v1() -> None:
    result = await _build_litellm_params_for_sync(
        {"model": "grok-4"},
        SimpleNamespace(model_id="grok-4", category="chat"),
        build_credential("https://api.x.ai/v1"),
        FakeSession("xai", "xai", False),
    )

    assert result["model"] == "xai/grok-4"
    assert result["api_base"] == "https://api.x.ai/v1"
