import pytest

from exceptions import ValidationError
from services import icon_url


@pytest.fixture(autouse=True)
def platform_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        icon_url.settings, "platform_public_url", "https://platform.example/"
    )


@pytest.mark.parametrize(
    ("raw", "path"),
    [
        ("Package", "/icons/v1/lucide/package.svg"),
        ("SpellCheck", "/icons/v1/lucide/spell-check.svg"),
        ("BarChart3", "/icons/v1/lucide/bar-chart-3.svg"),
        ("📦", "/icons/v1/lucide/package.svg"),
        ("package.svg", "/icons/v1/lucide/package.svg"),
        (None, "/icons/v1/default.svg"),
        ("UnknownIcon", "/icons/v1/default.svg"),
    ],
)
def test_resolve_icon_url_returns_hosted_asset(raw: str | None, path: str) -> None:
    assert icon_url.resolve_icon_url(raw) == f"https://platform.example{path}"


def test_resolve_icon_url_keeps_existing_urls() -> None:
    relative = "/icons/v1/lucide/globe.svg"
    absolute = "https://cdn.example/icon.svg"

    assert icon_url.resolve_icon_url(relative) == f"https://platform.example{relative}"
    assert icon_url.resolve_icon_url(absolute) == absolute


@pytest.mark.parametrize(
    ("provider_type", "filename"),
    [
        ("openai", "openai.svg"),
        ("vllm", "vllm.png"),
        ("sglang", "sglang.png"),
        ("tencent", "tencent.png"),
        ("other", "custom.svg"),
    ],
)
def test_resolve_provider_icon_url_uses_real_extension(
    provider_type: str, filename: str
) -> None:
    assert icon_url.resolve_provider_icon_url(provider_type) == (
        f"https://platform.example/icons/v1/providers/{filename}"
    )


def test_resolve_provider_icon_url_unknown_uses_default() -> None:
    assert icon_url.resolve_provider_icon_url("unknown") == (
        "https://platform.example/icons/v1/default.svg"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/icons/v1/lucide/package.svg", "/icons/v1/lucide/package.svg"),
        (
            "https://platform.example/icons/v1/providers/openai.svg",
            "/icons/v1/providers/openai.svg",
        ),
        ("", None),
    ],
)
def test_normalize_hosted_icon_path_accepts_platform_assets(
    raw: str, expected: str | None
) -> None:
    assert icon_url.normalize_hosted_icon_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Globe",
        "https://other.example/icons/v1/lucide/globe.svg",
        "/icons/../secret.svg",
        "/icons/v1/lucide/globe.svg?x=1",
    ],
)
def test_normalize_hosted_icon_path_rejects_non_platform_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        icon_url.normalize_hosted_icon_path(raw)
