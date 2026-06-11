from services.access_test_error_mapper import build_error_detail, map_error


class FakeProviderError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def test_access_test_mapper_auth_error_returns_supplier_credential_help() -> None:
    detail = map_error(
        FakeProviderError("Invalid API key sk-test-secret-123456789", status_code=401)
    )

    assert detail["category"] == "upstream_credential_invalid"
    assert "供应商管理" in str(detail["message"])
    assert "***" in str(detail["technical_detail"])
    assert "sk-test-secret" not in str(detail["technical_detail"])


def test_access_test_mapper_model_not_found_returns_upstream_model_help() -> None:
    detail = map_error(
        FakeProviderError("model_not_found: unknown model deepseek-v9", status_code=404)
    )

    assert detail["category"] == "upstream_model_name_invalid"
    assert "上游模型名" in str(detail["message"])
    assert "deepseek-chat" in str(detail["message"])


def test_access_test_mapper_plain_404_returns_base_url_help() -> None:
    detail = map_error(status_code=404, response_text="404 page not found")

    assert detail["category"] == "upstream_base_url_invalid"
    assert "Base URL" in str(detail["message"])
    assert "/v1/chat/completions" in str(detail["message"])


def test_access_test_mapper_permission_error_returns_supplier_permission_help() -> None:
    detail = map_error(
        FakeProviderError(
            "Project does not have access to model gpt-4.1", status_code=403
        )
    )

    assert detail["category"] == "upstream_permission_denied"
    assert "供应商管理" in str(detail["message"])
    assert "供应商控制台" in str(detail["message"])


def test_access_test_mapper_rate_limit_returns_identity_limit_when_key_related() -> (
    None
):
    detail = map_error(
        FakeProviderError("Virtual key RPM limit exceeded", status_code=429)
    )

    assert detail["category"] == "identity_rate_limited"
    assert "AI身份管理" in str(detail["message"])


def test_access_test_mapper_budget_returns_identity_budget_when_key_related() -> None:
    detail = map_error(
        FakeProviderError("Virtual key budget exceeded", status_code=429)
    )

    assert detail["category"] == "identity_budget_exceeded"
    assert "预算额度" in str(detail["message"])


def test_access_test_error_detail_can_be_built_for_precheck_category() -> None:
    detail = build_error_detail("model_not_authorized")

    assert detail["category"] == "model_not_authorized"
    assert "可用模型" in str(detail["message"])
