"""API Key 生成与哈希工具

Key 格式: ak-<48 字符 url-safe random>
存储策略: 仅持久化 SHA-256 哈希，raw key 仅创建时返回一次
前缀: ak-xxxxxx（11 字符），用于列表展示
"""

import hashlib
import secrets

KEY_PREFIX_LITERAL = "ak-"
RANDOM_BYTES = 18  # base64-url 编码后约 24 字符
PREFIX_DISPLAY_LEN = 11  # 形如 "ak-xxxxxxxx"


def generate_api_key() -> tuple[str, str, str]:
    """生成一个新的 API Key。

    Returns:
        (raw_key, key_prefix, key_hash)
        - raw_key: 完整 key（仅返回一次）
        - key_prefix: 前 11 字符（持久化用于列表展示）
        - key_hash: sha256(raw_key)（持久化用于校验）
    """
    random_part = secrets.token_urlsafe(RANDOM_BYTES)
    raw_key = f"{KEY_PREFIX_LITERAL}{random_part}"
    return raw_key, raw_key[:PREFIX_DISPLAY_LEN], hash_api_key(raw_key)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def looks_like_api_key(token: str) -> bool:
    return token.startswith(KEY_PREFIX_LITERAL)
