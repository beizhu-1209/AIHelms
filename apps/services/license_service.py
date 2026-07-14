import logging
from datetime import datetime, time, timezone
from pathlib import Path

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import ValidationError
from repositories import license_repo

logger = logging.getLogger(__name__)

ALGORITHM = "RS256"
PUBKEYS_DIR = Path(__file__).resolve().parent.parent / "core" / "license_pubkeys"
MAX_LICENSE_BYTES = 64 * 1024


def _load_public_keys() -> list[tuple[Path, str]]:
    if not PUBKEYS_DIR.exists():
        return []
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(PUBKEYS_DIR.glob("*.pem"))
    ]


def _validate_payload(payload: dict[str, object]) -> None:
    if not str(payload.get("customer", "")).strip():
        raise ValidationError("License 缺少客户信息")
    features = payload.get("features")
    if not isinstance(features, list) or not all(
        isinstance(item, str) for item in features
    ):
        raise ValidationError("License 功能列表无效")
    _parse_date(payload.get("issued_at"), end_of_day=False)
    _parse_date(payload.get("expires_at"), end_of_day=True)


def verify_token(token: str) -> dict[str, object]:
    token = token.strip()
    if not token or len(token.encode("utf-8")) > MAX_LICENSE_BYTES:
        raise ValidationError("License 文件无效")
    keys = _load_public_keys()
    if not keys:
        raise ValidationError("未配置验签公钥")

    last_error: Exception | None = None
    for path, public_key in keys:
        try:
            payload = jwt.decode(token, public_key, algorithms=[ALGORITHM])
            _validate_payload(payload)
            logger.info("license verified with public key %s", path.name)
            return payload
        except ExpiredSignatureError as exc:
            raise ValidationError("License 已过期") from exc
        except ValidationError:
            raise
        except JWTError as exc:
            last_error = exc
    logger.warning("license verification failed: %s", type(last_error).__name__)
    raise ValidationError("License 无效")


def _parse_date(value: object, *, end_of_day: bool) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValidationError("License 日期信息无效")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("License 日期格式无效") from exc
    parsed_time = time(23, 59, 59) if end_of_day else time.min
    return datetime.combine(parsed, parsed_time, tzinfo=timezone.utc)


async def import_license(session: AsyncSession, token: str) -> dict[str, object]:
    payload = verify_token(token)
    await license_repo.upsert(
        session,
        licensed_to=str(payload["customer"]).strip(),
        features=list(payload["features"]),
        issued_at=_parse_date(payload["issued_at"], end_of_day=False),
        expires_at=_parse_date(payload["expires_at"], end_of_day=True),
        license_key=token.strip(),
        status="active",
        imported_at=datetime.now(timezone.utc),
    )
    await session.commit()
    return await get_status(session)


async def get_status(session: AsyncSession) -> dict[str, object]:
    row = await license_repo.get(session)
    if row is None or row.status != "active":
        return {
            "edition": "community",
            "licensed_to": None,
            "expires_at": None,
            "features": [],
            "status": row.status if row else "none",
        }
    expired = row.expires_at is not None and row.expires_at < datetime.now(timezone.utc)
    return {
        "edition": "community" if expired else "enterprise",
        "licensed_to": row.licensed_to,
        "expires_at": row.expires_at.strftime("%Y-%m-%d") if row.expires_at else None,
        "features": [] if expired else list(row.features or []),
        "status": "expired" if expired else "active",
    }


async def is_feature_enabled(session: AsyncSession, _feature: str) -> bool:
    status = await get_status(session)
    return status["status"] == "active" and status["edition"] == "enterprise"
