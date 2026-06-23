from repositories.usage_log_repo import (
    _current_llm_model_names,
    _is_current_llm_model,
)
from services.usage_log_service import _llm_cost_breakdown
from tasks.llm_log_tasks import _billable_prompt_tokens, _parse_cache_tokens


def test_llm_log_cost_deepseek_cached_tokens_are_subtracted() -> None:
    metadata = {
        "usage_object": {
            "prompt_tokens": 130369,
            "prompt_tokens_details": {"cached_tokens": 130176},
        }
    }

    cache_read, cache_creation = _parse_cache_tokens(metadata)

    assert cache_read == 130176
    assert cache_creation == 0
    assert _billable_prompt_tokens(130369, cache_read, cache_creation) == 193


def test_llm_log_cost_anthropic_cache_read_and_creation_are_subtracted() -> None:
    metadata = {
        "usage_object": {
            "prompt_tokens": 25574,
            "prompt_tokens_details": {"cached_tokens": 23100},
            "cache_read_input_tokens": 23100,
            "cache_creation_input_tokens": 2325,
        }
    }

    cache_read, cache_creation = _parse_cache_tokens(metadata)

    assert cache_read == 23100
    assert cache_creation == 2325
    assert _billable_prompt_tokens(25574, cache_read, cache_creation) == 149


def test_llm_log_cost_missing_details_falls_back_to_zero() -> None:
    metadata = {"usage_object": {"prompt_tokens": 35, "prompt_tokens_details": None}}

    cache_read, cache_creation = _parse_cache_tokens(metadata)

    assert cache_read == 0
    assert cache_creation == 0
    assert _billable_prompt_tokens(35, cache_read, cache_creation) == 35


def test_llm_log_cost_uses_legacy_cache_read_fallback() -> None:
    metadata = {"usage_object": {"cache_read_input_tokens": 52}}

    cache_read, cache_creation = _parse_cache_tokens(metadata)

    assert cache_read == 52
    assert cache_creation == 0


class _Log:
    prompt_tokens = 1000
    completion_tokens = 200
    cache_read_tokens = 300
    cache_creation_tokens = 100


def test_llm_log_cost_breakdown_uses_billable_input_tokens() -> None:
    deployment = {
        "billing_type": "token",
        "model_info": {
            "internal_input_cost": 10,
            "internal_output_cost": 20,
            "internal_cache_read_cost": 1,
            "internal_cache_creation_cost": 2,
            "input_cost": 5,
            "output_cost": 8,
            "cache_read_cost": 0.5,
            "cache_creation_cost": 0.75,
        },
    }

    breakdown = _llm_cost_breakdown(_Log(), deployment)

    assert breakdown["internal_input_cost"] == "0.006000"
    assert breakdown["internal_output_cost"] == "0.004000"
    assert breakdown["internal_cache_read_cost"] == "0.000300"
    assert breakdown["internal_cache_creation_cost"] == "0.000200"
    assert breakdown["external_input_cost"] == "0.003000"
    assert breakdown["external_output_cost"] == "0.001600"
    assert breakdown["external_cache_read_cost"] == "0.000150"
    assert breakdown["external_cache_creation_cost"] == "0.000075"


def test_llm_log_filter_marks_model_aliases_as_current() -> None:
    current_model_ids = {"deepseek-v4-pro"}

    assert _is_current_llm_model("deepseek-v4-pro", current_model_ids)
    assert _is_current_llm_model("DeepSeek-V4-Pro", current_model_ids)
    assert _is_current_llm_model("anthropic/deepseek-v4-pro", current_model_ids)
    assert _is_current_llm_model("deepseek-v4-pro(Anthropic)", current_model_ids)


def test_llm_log_filter_matches_active_deployment_alias() -> None:
    current_model_names = _current_llm_model_names(
        [("kimi-k2.6", "Kimi2.6", {"model": "hosted_vllm/kimi26"})],
    )

    assert _is_current_llm_model("kimi26", current_model_names)
    assert _is_current_llm_model("hosted_vllm/kimi26", current_model_names)
    assert _is_current_llm_model("openai/kimi26", current_model_names)


def test_llm_log_filter_marks_missing_models_as_deleted() -> None:
    assert not _is_current_llm_model("claude-opus-4-7", {"claude-opus-4-6"})


def test_llm_log_filter_excludes_models_without_routable_deployment_names() -> None:
    current_model_names = _current_llm_model_names([])

    assert not _is_current_llm_model("disabled-model", current_model_names)
    assert not _is_current_llm_model("1", current_model_names)
    assert not _is_current_llm_model("MCP: list_tools", current_model_names)
