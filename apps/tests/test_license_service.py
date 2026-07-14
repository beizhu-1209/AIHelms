from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from exceptions import ValidationError
from services import license_service


def _make_keypair(tmp_path: Path, name: str = "key.pem") -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    (tmp_path / name).write_bytes(public_pem)
    return private_pem


def _sign(private_pem: bytes, expires_in_days: int) -> str:
    expiration = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    payload = {
        "customer": "测试公司",
        "issued_at": "2026-07-14",
        "expires_at": expiration.strftime("%Y-%m-%d"),
        "features": ["all"],
        "license_id": "test-license",
        "exp": int(expiration.timestamp()),
    }
    return jwt.encode(payload, private_pem.decode(), algorithm="RS256")


def test_verify_token_tries_multiple_public_keys(tmp_path, monkeypatch) -> None:
    _make_keypair(tmp_path, "wrong.pem")
    private_pem = _make_keypair(tmp_path, "right.pem")
    monkeypatch.setattr(license_service, "PUBKEYS_DIR", tmp_path)

    payload = license_service.verify_token(_sign(private_pem, 30))

    assert payload["customer"] == "测试公司"
    assert payload["features"] == ["all"]


def test_verify_token_rejects_tampered_token(tmp_path, monkeypatch) -> None:
    private_pem = _make_keypair(tmp_path)
    monkeypatch.setattr(license_service, "PUBKEYS_DIR", tmp_path)
    token = _sign(private_pem, 30)

    with pytest.raises(ValidationError, match="License 无效"):
        license_service.verify_token(token[:-4] + "AAAA")


def test_verify_token_rejects_expired_token(tmp_path, monkeypatch) -> None:
    private_pem = _make_keypair(tmp_path)
    monkeypatch.setattr(license_service, "PUBKEYS_DIR", tmp_path)

    with pytest.raises(ValidationError, match="License 已过期"):
        license_service.verify_token(_sign(private_pem, -1))


@pytest.mark.asyncio
async def test_get_status_hides_features_after_expiration(monkeypatch) -> None:
    row = SimpleNamespace(
        status="active",
        licensed_to="测试公司",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        features=["whitelabel"],
    )

    async def fake_get(session):
        return row

    monkeypatch.setattr(license_service.license_repo, "get", fake_get)

    status = await license_service.get_status(object())

    assert status["edition"] == "community"
    assert status["status"] == "expired"
    assert status["features"] == []


@pytest.mark.asyncio
async def test_valid_license_enables_every_feature(monkeypatch) -> None:
    async def fake_get_status(session):
        return {
            "edition": "enterprise",
            "status": "active",
            "features": ["all"],
        }

    monkeypatch.setattr(license_service, "get_status", fake_get_status)

    assert await license_service.is_feature_enabled(object(), "whitelabel") is True
    assert await license_service.is_feature_enabled(object(), "future_feature") is True


@pytest.mark.asyncio
async def test_inactive_license_does_not_enable_features(monkeypatch) -> None:
    async def fake_get_status(session):
        return {
            "edition": "community",
            "status": "expired",
            "features": [],
        }

    monkeypatch.setattr(license_service, "get_status", fake_get_status)

    assert await license_service.is_feature_enabled(object(), "whitelabel") is False
