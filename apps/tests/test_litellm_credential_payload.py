from services.litellm_credential_payload import prepare_litellm_credential_values


def test_vllm_anthropic_adds_bearer_header_without_mutating_source():
    source = {"api_key": "secret", "api_base": "http://vllm.local"}

    result = prepare_litellm_credential_values(
        source, {"format": "anthropic"}, "vllm"
    )

    assert result["extra_headers"] == {"authorization": "Bearer secret"}
    assert "extra_headers" not in source


def test_existing_authorization_header_is_not_overwritten_case_insensitive():
    result = prepare_litellm_credential_values(
        {
            "api_key": "secret",
            "extra_headers": {"Authorization": "Bearer custom", "x-trace": "1"},
        },
        {"format": "anthropic"},
        "vllm",
    )

    assert result["extra_headers"] == {
        "Authorization": "Bearer custom",
        "x-trace": "1",
    }


def test_non_vllm_anthropic_is_unchanged():
    result = prepare_litellm_credential_values(
        {"api_key": "secret"}, {"format": "anthropic"}, "anthropic"
    )

    assert result == {"api_key": "secret"}
