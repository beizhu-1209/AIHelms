from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import async_session
from core.security import ALGORITHM
from exceptions import ForbiddenError


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证 token")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="token 无效")
    return {
        "id": int(user_id),
        "username": payload.get("username", ""),
        "is_admin": payload.get("is_admin", False),
        "permissions": payload.get("permissions", []),
    }


def require_permission(permission_code: str):
    async def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["is_admin"]:
            return current_user
        if permission_code not in current_user["permissions"]:
            raise HTTPException(status_code=403, detail="权限不足")
        return current_user

    return checker
