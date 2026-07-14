import logging
from pathlib import Path
from xml.etree import ElementTree

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from exceptions import ForbiddenError, ValidationError
from repositories import branding_repo
from services import license_service

logger = logging.getLogger(__name__)

WHITELABEL_FEATURE = "whitelabel"
DEFAULT_PLATFORM_NAME = "AIHelms"
LOGO_EXTS = {"png": "image/png", "svg": "image/svg+xml"}
SQUARE_LOGO_EXTS = {"png", "svg"}
FAVICON_EXTS = {"ico": "image/x-icon", "png": "image/png"}
MAX_LOGO_BYTES = 10 * 1024 * 1024
MAX_SQUARE_LOGO_BYTES = 2 * 1024 * 1024
MAX_FAVICON_BYTES = 200 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ICO_SIGNATURE = b"\x00\x00\x01\x00"


def _branding_dir() -> Path:
    path = (Path(settings.uploads_storage_dir) / "branding").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


async def ensure_whitelabel(session: AsyncSession) -> None:
    if not await license_service.is_feature_enabled(session, WHITELABEL_FEATURE):
        raise ForbiddenError("该功能需要企业版授权")


async def get_branding(session: AsyncSession) -> dict[str, object]:
    if not await license_service.is_feature_enabled(session, WHITELABEL_FEATURE):
        return {
            "platform_name": DEFAULT_PLATFORM_NAME,
            "has_logo": False,
            "has_square_logo": False,
            "has_favicon": False,
        }
    row = await branding_repo.get(session)
    return {
        "platform_name": row.platform_name,
        "has_logo": _asset_exists(row.logo_path),
        "has_square_logo": _asset_exists(row.square_logo_path),
        "has_favicon": _asset_exists(row.favicon_path),
    }


async def update_platform_name(session: AsyncSession, name: str) -> dict[str, object]:
    await ensure_whitelabel(session)
    normalized = name.strip()
    if not normalized:
        raise ValidationError("平台名称不能为空")
    if len(normalized) > 100:
        raise ValidationError("平台名称不能超过 100 个字符")
    await branding_repo.update(session, platform_name=normalized)
    await session.commit()
    return await get_branding(session)


def _validate_image(
    content: bytes, ext: str, *, favicon: bool = False, square_logo: bool = False
) -> None:
    if square_logo:
        allowed = SQUARE_LOGO_EXTS
        limit = MAX_SQUARE_LOGO_BYTES
        label = "方形 Logo"
    elif favicon:
        allowed = FAVICON_EXTS
        limit = MAX_FAVICON_BYTES
        label = "Favicon"
    else:
        allowed = LOGO_EXTS
        limit = MAX_LOGO_BYTES
        label = "Logo"
    if ext not in allowed:
        supported = "ico 或 png" if favicon and not square_logo else "png 或 svg"
        raise ValidationError(f"{label} 仅支持 {supported}")
    if not content:
        raise ValidationError(f"{label} 文件不能为空")
    if len(content) > limit:
        size = "2MB" if square_logo else "200KB" if favicon else "10MB"
        raise ValidationError(f"{label} 文件不能超过 {size}")
    if ext == "png" and not content.startswith(PNG_SIGNATURE):
        raise ValidationError("PNG 文件格式无效")
    if ext == "ico" and not content.startswith(ICO_SIGNATURE):
        raise ValidationError("ICO 文件格式无效")
    if ext == "svg":
        _validate_svg(content)


def _validate_svg(content: bytes) -> None:
    try:
        root = ElementTree.fromstring(content.decode("utf-8"))
    except (UnicodeDecodeError, ElementTree.ParseError) as exc:
        raise ValidationError("SVG 文件格式无效") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise ValidationError("SVG 文件格式无效")
    blocked_tags = {"script", "foreignobject", "iframe", "object", "embed"}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() in blocked_tags:
            raise ValidationError("SVG 包含不安全内容")
        for name, value in element.attrib.items():
            attr = name.rsplit("}", 1)[-1].lower()
            lowered = value.strip().lower()
            if attr.startswith("on") or "javascript:" in lowered:
                raise ValidationError("SVG 包含不安全内容")
            if attr == "href" and lowered and not lowered.startswith("#"):
                raise ValidationError("SVG 不允许引用外部资源")
            if attr == "style" and ("url(" in lowered or "expression(" in lowered):
                raise ValidationError("SVG 包含不安全样式")


async def _save_asset(
    session: AsyncSession,
    content: bytes,
    ext: str,
    *,
    favicon: bool = False,
    square_logo: bool = False,
) -> None:
    await ensure_whitelabel(session)
    _validate_image(content, ext, favicon=favicon, square_logo=square_logo)
    stem = "square_logo" if square_logo else "favicon" if favicon else "logo"
    directory = _branding_dir()
    destination = directory / f"{stem}.{ext}"
    temporary = directory / f".{stem}.{ext}.tmp"
    temporary.write_bytes(content)
    temporary.replace(destination)
    for old in directory.glob(f"{stem}.*"):
        if old != destination and not old.name.endswith(".tmp"):
            old.unlink(missing_ok=True)
    field = (
        "square_logo_path"
        if square_logo
        else "favicon_path" if favicon else "logo_path"
    )
    await branding_repo.update(session, **{field: str(destination)})
    await session.commit()


async def save_logo(session: AsyncSession, content: bytes, ext: str) -> None:
    await _save_asset(session, content, ext)


async def save_square_logo(session: AsyncSession, content: bytes, ext: str) -> None:
    await _save_asset(session, content, ext, square_logo=True)


async def save_favicon(session: AsyncSession, content: bytes, ext: str) -> None:
    await _save_asset(session, content, ext, favicon=True)


def _asset_exists(path_value: str | None) -> bool:
    return bool(path_value) and Path(path_value).is_file()


def _read_asset(
    path_value: str | None, media_types: dict[str, str]
) -> tuple[bytes, str] | None:
    if not path_value:
        return None
    path = Path(path_value).resolve()
    if not path.is_relative_to(_branding_dir()) or not path.is_file():
        logger.warning("ignored invalid branding asset path: %s", path)
        return None
    media_type = media_types.get(path.suffix.lstrip(".").lower())
    if not media_type:
        return None
    return path.read_bytes(), media_type


async def read_logo(session: AsyncSession) -> tuple[bytes, str] | None:
    if not await license_service.is_feature_enabled(session, WHITELABEL_FEATURE):
        return None
    row = await branding_repo.get(session)
    return _read_asset(row.logo_path, LOGO_EXTS)


async def read_square_logo(session: AsyncSession) -> tuple[bytes, str] | None:
    if not await license_service.is_feature_enabled(session, WHITELABEL_FEATURE):
        return None
    row = await branding_repo.get(session)
    return _read_asset(row.square_logo_path, LOGO_EXTS)


async def read_favicon(session: AsyncSession) -> tuple[bytes, str] | None:
    if not await license_service.is_feature_enabled(session, WHITELABEL_FEATURE):
        return None
    row = await branding_repo.get(session)
    return _read_asset(row.favicon_path, FAVICON_EXTS)
