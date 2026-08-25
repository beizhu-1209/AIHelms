"""Web / admin 登录支持用户名或邮箱的测试。"""

from unittest.mock import AsyncMock, patch

import pytest

from core.security import get_password_hash
from exceptions import UnauthorizedError
from models.db import User
from services import auth_service

PASSWORD = "correct-horse"


def _user(username: str, email: str, is_active: bool = True) -> User:
    return User(
        id=1,
        username=username,
        email=email,
        hashed_password=get_password_hash(PASSWORD),
        is_active=is_active,
        is_admin=False,
    )


def _patch_finder(user: User | None) -> object:
    return patch.object(
        auth_service.user_repo,
        "find_user_by_account",
        AsyncMock(return_value=user),
    )


@pytest.mark.asyncio
async def test_authenticate_with_username_returns_user():
    user = _user("alice", "alice@example.com")
    with _patch_finder(user) as finder:
        result = await auth_service.authenticate(AsyncMock(), "alice", PASSWORD)
    assert result is user
    assert finder.await_args.args[1] == "alice"


@pytest.mark.asyncio
async def test_authenticate_with_email_returns_user():
    user = _user("alice", "alice@example.com")
    with _patch_finder(user) as finder:
        result = await auth_service.authenticate(
            AsyncMock(), "alice@example.com", PASSWORD
        )
    assert result is user
    assert finder.await_args.args[1] == "alice@example.com"


@pytest.mark.asyncio
async def test_authenticate_unknown_account_raises_unauthorized():
    with _patch_finder(None):
        with pytest.raises(UnauthorizedError, match="账号或密码错误"):
            await auth_service.authenticate(AsyncMock(), "nobody@example.com", PASSWORD)


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises_unauthorized():
    with _patch_finder(_user("alice", "alice@example.com")):
        with pytest.raises(UnauthorizedError, match="账号或密码错误"):
            await auth_service.authenticate(AsyncMock(), "alice@example.com", "wrong")


@pytest.mark.asyncio
async def test_authenticate_inactive_user_raises_unauthorized():
    with _patch_finder(_user("alice", "alice@example.com", is_active=False)):
        with pytest.raises(UnauthorizedError, match="账户已被禁用"):
            await auth_service.authenticate(AsyncMock(), "alice@example.com", PASSWORD)
