"""管理员操作审计日志中间件

ASGI 中间件，拦截写方法（POST/PUT/DELETE/PATCH），异步落表 admin_audit_logs。
- 仅管理员（is_admin=True）的请求被记录；登录接口无条件记录
- 请求体敏感字段脱敏后完整存储
- 写日志失败不影响业务请求
- 兼容流式响应（StreamingResponse）
"""

import asyncio
import json
import logging
import time

from core.database import async_session
from models.db import AdminAuditLog

logger = logging.getLogger(__name__)

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# 路径白名单（前缀匹配）
PATH_WHITELIST_PREFIXES = (
    "/api/health",
    "/api/v1/ping",
)

LOGIN_PATH = "/api/v1/auth/login"

SENSITIVE_KEYS = {
    "password",
    "hashed_password",
    "old_password",
    "new_password",
    "secret",
    "token",
    "access_token",
    "api_key",
    "credential_values",
}


class AuditLogMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")

        if method not in WRITE_METHODS or _is_whitelisted(path) or _is_multipart(scope):
            await self.app(scope, receive, send)
            return

        # 读取并缓存请求体
        body_bytes = await _read_body(receive)

        # 重放 receive 给下游
        sent = False

        async def wrapped_receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            # body 已重放完，后续转发原 receive（用于监听客户端 disconnect）
            return await receive()

        # 截获 status_code
        status_code = 0

        async def wrapped_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await send(message)

        start = time.monotonic()
        try:
            await self.app(scope, wrapped_receive, wrapped_send)
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                _schedule_audit(scope, status_code, body_bytes, duration_ms)
            except Exception:  # noqa: BLE001
                logger.warning("audit middleware schedule failed", exc_info=True)


def _is_whitelisted(path: str) -> bool:
    return any(path.startswith(p) for p in PATH_WHITELIST_PREFIXES)


def _is_multipart(scope) -> bool:
    for name, value in scope.get("headers", []):
        if name == b"content-type":
            decoded = value.decode("latin-1", errors="replace")
            return decoded.startswith("multipart/form-data")
    return False


async def _read_body(receive) -> bytes:
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        msg = await receive()
        if msg["type"] == "http.request":
            chunks.append(msg.get("body", b"") or b"")
            more_body = msg.get("more_body", False)
        elif msg["type"] == "http.disconnect":
            more_body = False
    return b"".join(chunks)


def _schedule_audit(
    scope,
    status_code: int,
    body_bytes: bytes,
    duration_ms: int,
) -> None:
    path = scope.get("path", "")
    method = scope.get("method", "")
    is_login = path == LOGIN_PATH

    state = scope.get("state") or {}
    user = state.get("current_user")

    if is_login:
        if status_code == 200 and user:
            user_id = user["id"]
            username = user["username"]
            identity_type = user.get("identity_type", "user")
        else:
            user_id = 0
            username = _extract_username_from_body(body_bytes)
            identity_type = "user"
    else:
        if not user or not user.get("is_admin"):
            return
        user_id = user["id"]
        username = user["username"]
        identity_type = user.get("identity_type", "user")

    route = scope.get("route")
    summary = getattr(route, "summary", None) if route else None
    path_template = getattr(route, "path", None) if route else path
    action = summary or f"{method} {path_template}"

    headers = {
        k.decode("latin-1"): v.decode("latin-1", errors="replace")
        for k, v in scope.get("headers", [])
    }
    ip = _get_client_ip(scope, headers)
    user_agent = headers.get("user-agent", "")[:500]

    request_summary = _redact_body(body_bytes)

    asyncio.create_task(
        _write_audit_log(
            user_id=user_id,
            username=username,
            identity_type=identity_type,
            method=method,
            path=path,
            action=action,
            status_code=status_code,
            ip=ip,
            user_agent=user_agent,
            duration_ms=duration_ms,
            request_summary=request_summary,
        )
    )


def _get_client_ip(scope, headers: dict) -> str:
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    client = scope.get("client")
    if client:
        return str(client[0])[:64]
    return ""


def _extract_username_from_body(body_bytes: bytes) -> str:
    if not body_bytes:
        return ""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if isinstance(data, dict):
        username = data.get("username")
        if isinstance(username, str):
            return username[:64]
    return ""


def _redact_body(body_bytes: bytes) -> str:
    if not body_bytes:
        return ""
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "<non-json body>"
    redacted = _redact(data)
    return json.dumps(redacted, ensure_ascii=False)


def _redact(value):
    if isinstance(value, dict):
        return {
            k: ("***" if k.lower() in SENSITIVE_KEYS else _redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


async def _write_audit_log(
    *,
    user_id: int,
    username: str,
    identity_type: str,
    method: str,
    path: str,
    action: str,
    status_code: int,
    ip: str,
    user_agent: str,
    duration_ms: int,
    request_summary: str,
) -> None:
    try:
        async with async_session() as session:
            log = AdminAuditLog(
                user_id=user_id,
                username=username,
                identity_type=identity_type,
                method=method,
                path=path,
                action=action,
                status_code=status_code,
                ip=ip,
                user_agent=user_agent,
                duration_ms=duration_ms,
                request_summary=request_summary,
            )
            session.add(log)
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("write audit log failed", exc_info=True)
