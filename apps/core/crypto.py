"""对称加密工具

用 SECRET_KEY 派生 Fernet 密钥，加密敏感字段（如 API Key 原文）。

注意：SECRET_KEY 一旦改变，所有已加密数据将无法解密。
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import settings


def _derive_fernet_key() -> bytes:
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
