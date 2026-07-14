from types import SimpleNamespace

import pytest

from exceptions import ForbiddenError, ValidationError
from services import branding_service


@pytest.mark.asyncio
async def test_community_branding_returns_defaults(monkeypatch) -> None:
    async def disabled(session, feature):
        return False

    monkeypatch.setattr(
        branding_service.license_service, "is_feature_enabled", disabled
    )

    branding = await branding_service.get_branding(object())

    assert branding == {
        "platform_name": "AIHelms",
        "has_logo": False,
        "has_square_logo": False,
        "has_favicon": False,
    }


@pytest.mark.asyncio
async def test_community_cannot_update_branding(monkeypatch) -> None:
    async def disabled(session, feature):
        return False

    monkeypatch.setattr(
        branding_service.license_service, "is_feature_enabled", disabled
    )

    with pytest.raises(ForbiddenError, match="企业版"):
        await branding_service.update_platform_name(object(), "测试平台")


def test_svg_rejects_script_content() -> None:
    content = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'

    with pytest.raises(ValidationError, match="不安全"):
        branding_service._validate_image(content, "svg", favicon=False)


def test_png_rejects_extension_only_spoof() -> None:
    with pytest.raises(ValidationError, match="PNG"):
        branding_service._validate_image(b"not-a-png", "png", favicon=False)


def test_square_logo_rejects_file_over_two_megabytes() -> None:
    content = branding_service.PNG_SIGNATURE + b"x" * (
        branding_service.MAX_SQUARE_LOGO_BYTES + 1
    )

    with pytest.raises(ValidationError, match="2MB"):
        branding_service._validate_image(content, "png", square_logo=True)


@pytest.mark.asyncio
async def test_enterprise_branding_reports_square_logo(monkeypatch) -> None:
    async def enabled(session, feature):
        return True

    async def get_branding_row(session):
        return SimpleNamespace(
            platform_name="测试平台",
            logo_path=None,
            square_logo_path="/tmp/square-logo.png",
            favicon_path=None,
        )

    monkeypatch.setattr(branding_service.license_service, "is_feature_enabled", enabled)
    monkeypatch.setattr(branding_service.branding_repo, "get", get_branding_row)
    monkeypatch.setattr(branding_service, "_asset_exists", lambda path: bool(path))

    branding = await branding_service.get_branding(object())

    assert branding["has_square_logo"] is True
