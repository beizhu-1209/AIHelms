import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessTestErrorTemplate:
    title: str
    message: str


ERROR_TEMPLATES: dict[str, AccessTestErrorTemplate] = {
    "no_identity": AccessTestErrorTemplate(
        title="测试失败：当前用户没有可用 AI 身份",
        message=(
            "请进入「AI身份管理」，为该用户创建「个人主身份」，或将已有身份状态"
            "改为「启用」。"
        ),
    ),
    "model_not_authorized": AccessTestErrorTemplate(
        title="测试失败：当前用户的 AI 身份未包含该模型",
        message=(
            "请进入「AI身份管理」，在该用户个人主身份的可用模型中勾选当前模型"
            "并保存。"
        ),
    ),
    "model_not_published": AccessTestErrorTemplate(
        title="测试失败：当前模型未发布",
        message="请进入「模型管理」，打开该模型，将发布状态改为已发布。",
    ),
    "no_active_deployment": AccessTestErrorTemplate(
        title="测试失败：当前模型没有可用部署通道",
        message=(
            "请进入「模型管理」的部署配置，新增部署，或将已有部署和关联凭证"
            "改为启用。"
        ),
    ),
    "upstream_credential_invalid": AccessTestErrorTemplate(
        title="测试失败：上游供应商凭证无效",
        message=(
            "请进入「供应商管理」，编辑当前模型使用的凭证，重新填写供应商 API Key，"
            "保存后重试。"
        ),
    ),
    "upstream_permission_denied": AccessTestErrorTemplate(
        title="测试失败：上游供应商账号无权调用该模型",
        message=(
            "请进入「供应商管理」，确认当前凭证对应的供应商账号已开通该模型；"
            "如未开通，请到供应商控制台申请权限，或在「模型管理」的部署配置中"
            "改用已授权的上游模型名或凭证。"
        ),
    ),
    "upstream_base_url_invalid": AccessTestErrorTemplate(
        title="测试失败：上游模型地址不可用",
        message=(
            "请进入「供应商管理」，确认 Base URL 只填写服务基础地址，"
            "例如 https://api.deepseek.com，不要填写 /v1/chat、"
            "/v1/chat/completions 等接口路径。"
        ),
    ),
    "upstream_model_name_invalid": AccessTestErrorTemplate(
        title="测试失败：上游供应商模型名称填写错误",
        message=(
            "请进入「模型管理」的部署配置，将「上游模型名」改为供应商官方支持的"
            "模型名称，例如 deepseek-chat，不要填写平台展示名称、平台模型 ID "
            "或中文名称。"
        ),
    ),
    "upstream_connection_failed": AccessTestErrorTemplate(
        title="测试失败：平台无法连接上游模型服务",
        message=(
            "请先进入「供应商管理」核对 Base URL 和凭证；再进入「模型管理」的"
            "部署配置核对上游模型名。如果字段都正确，再确认服务器网络能访问供应商地址。"
        ),
    ),
    "identity_rate_limited": AccessTestErrorTemplate(
        title="测试失败：当前 AI 身份触发速率限制",
        message="请进入「AI身份管理」，调整该身份 RPM / TPM 后重试。",
    ),
    "upstream_rate_limited": AccessTestErrorTemplate(
        title="测试失败：上游供应商触发速率限制",
        message=("如果平台身份限制未超出，请到供应商控制台查看账号限流或稍后重试。"),
    ),
    "identity_budget_exceeded": AccessTestErrorTemplate(
        title="测试失败：当前 AI 身份预算已用完",
        message="请进入「AI身份管理」，调整预算额度或模型预算后重试。",
    ),
    "team_or_upstream_budget_exceeded": AccessTestErrorTemplate(
        title="测试失败：团队或上游供应商预算已用完",
        message=(
            "请进入「AI身份管理」核对归属与预算；如果平台预算未超出，"
            "请到供应商控制台查看账号额度。"
        ),
    ),
    "model_type_mismatch": AccessTestErrorTemplate(
        title="测试失败：当前测试方式和模型类型不一致",
        message=(
            "请进入「模型管理」，确认分类是否正确：对话模型选 Chat，"
            "向量模型选 Embedding，重排模型选 Rerank。"
        ),
    ),
    "context_length_exceeded": AccessTestErrorTemplate(
        title="测试失败：测试输入超过模型上下文限制",
        message="请减少测试内容长度，或降低 max_tokens 后重试。",
    ),
    "upstream_unknown": AccessTestErrorTemplate(
        title="测试失败：上游模型服务返回异常",
        message=(
            "请查看技术详情中的供应商错误摘要；再进入「供应商管理」核对 Base URL "
            "和凭证；进入「模型管理」的部署配置核对上游模型名。"
            "字段正确仍失败时，请联系供应商确认服务状态。"
        ),
    ),
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(
        r"(?i)(api[_\- ]?key|authorization|bearer|token)([\"'=:\s]+)([^\s,;，。]+)"
    ),
]


def build_error_detail(
    category: str,
    technical_detail: str = "",
    status_code: int | None = None,
) -> dict[str, object]:
    template = ERROR_TEMPLATES.get(category, ERROR_TEMPLATES["upstream_unknown"])
    detail: dict[str, object] = {
        "category": category,
        "title": template.title,
        "message": template.message,
        "technical_detail": _sanitize_technical_detail(technical_detail),
    }
    if status_code is not None:
        detail["status_code"] = status_code
    return detail


def map_error(
    exc: BaseException | None = None,
    status_code: int | None = None,
    response_text: str | None = None,
) -> dict[str, object]:
    resolved_status = _resolve_status_code(exc, status_code)
    raw_message = _resolve_raw_message(exc, response_text)
    category = _classify_error(exc, resolved_status, raw_message)
    technical_detail = _build_technical_detail(exc, resolved_status, raw_message)
    return build_error_detail(category, technical_detail, resolved_status)


def build_failure(error_detail: dict[str, object]) -> dict[str, object]:
    return {
        "success": False,
        "error": str(error_detail.get("title") or "测试失败"),
        "error_detail": error_detail,
    }


def _resolve_status_code(
    exc: BaseException | None,
    status_code: int | None,
) -> int | None:
    if status_code is not None:
        return status_code
    if exc is None:
        return None
    exc_status = getattr(exc, "status_code", None)
    if isinstance(exc_status, int):
        return exc_status
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _resolve_raw_message(
    exc: BaseException | None,
    response_text: str | None,
) -> str:
    if response_text:
        return response_text
    if exc is None:
        return ""
    exc_message = getattr(exc, "message", None)
    if isinstance(exc_message, str) and exc_message:
        return exc_message
    return str(exc)


def _build_technical_detail(
    exc: BaseException | None,
    status_code: int | None,
    raw_message: str,
) -> str:
    class_name = exc.__class__.__name__ if exc is not None else "HTTPError"
    prefix = f"{status_code} {class_name}" if status_code is not None else class_name
    return f"{prefix}: {raw_message}" if raw_message else prefix


def _sanitize_technical_detail(detail: str) -> str:
    sanitized = " ".join(detail.split())
    sanitized = SECRET_PATTERNS[0].sub("sk-***", sanitized)
    sanitized = SECRET_PATTERNS[1].sub(r"\1\2***", sanitized)
    return sanitized[:500]


def _classify_error(
    exc: BaseException | None,
    status_code: int | None,
    raw_message: str,
) -> str:
    text = raw_message.lower()
    class_name = exc.__class__.__name__.lower() if exc is not None else ""
    if _contains_any(text, ["context length", "context_window", "maximum context"]):
        return "context_length_exceeded"
    if _is_budget_error(text):
        return _budget_category(text)
    if _is_rate_limit_error(text, status_code):
        return _rate_limit_category(text)
    if _is_permission_error(text, status_code):
        return "upstream_permission_denied"
    if _is_auth_error(text, class_name, status_code):
        return "upstream_credential_invalid"
    if _is_model_type_error(text):
        return "model_type_mismatch"
    if _is_model_name_error(text, status_code):
        return "upstream_model_name_invalid"
    if _is_base_url_error(text):
        return "upstream_base_url_invalid"
    if _is_connection_error(text, class_name, status_code):
        return "upstream_connection_failed"
    return "upstream_unknown"


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _is_budget_error(text: str) -> bool:
    return "budget" in text and _contains_any(
        text, ["exceed", "limit", "quota", "insufficient", "用完"]
    )


def _budget_category(text: str) -> str:
    if _contains_any(text, ["key", "token", "virtual key", "user"]):
        return "identity_budget_exceeded"
    return "team_or_upstream_budget_exceeded"


def _is_rate_limit_error(text: str, status_code: int | None) -> bool:
    return status_code == 429 or _contains_any(
        text, ["rate limit", "rpm", "tpm", "too many requests", "限流"]
    )


def _rate_limit_category(text: str) -> str:
    if _contains_any(text, ["rpm", "tpm", "key", "virtual key", "user"]):
        return "identity_rate_limited"
    return "upstream_rate_limited"


def _is_auth_error(text: str, class_name: str, status_code: int | None) -> bool:
    return (
        status_code == 401
        or "authentication" in class_name
        or _contains_any(text, ["invalid api key", "incorrect api key", "unauthorized"])
    )


def _is_permission_error(text: str, status_code: int | None) -> bool:
    return status_code == 403 or _contains_any(
        text,
        [
            "not allowed",
            "not authorized",
            "permission",
            "forbidden",
            "does not have access",
            "not in allowed",
        ],
    )


def _is_model_type_error(text: str) -> bool:
    return _contains_any(
        text,
        [
            "embedding",
            "rerank",
            "chat completion",
            "not support",
            "unsupported",
            "endpoint",
        ],
    ) and _contains_any(text, ["model", "request", "parameter", "input"])


def _is_model_name_error(text: str, status_code: int | None) -> bool:
    model_error = _contains_any(
        text,
        [
            "model_not_found",
            "model not found",
            "invalid model",
            "unknown model",
            "does not exist",
            "no model",
        ],
    )
    return model_error or (status_code == 404 and "model" in text)


def _is_base_url_error(text: str) -> bool:
    return _contains_any(
        text,
        [
            "/v1/chat",
            "/chat/completions",
            "/v1/messages",
            "api_base",
            "base url",
            "invalid url",
            "404 page",
        ],
    )


def _is_connection_error(
    text: str,
    class_name: str,
    status_code: int | None,
) -> bool:
    if status_code in {408, 502, 503, 504}:
        return True
    if _contains_any(class_name, ["timeout", "connection", "network"]):
        return True
    return _contains_any(
        text,
        [
            "timeout",
            "timed out",
            "connection",
            "connect error",
            "connection refused",
            "name or service not known",
            "nodename nor servname",
            "network",
        ],
    )
