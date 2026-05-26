from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from exceptions import NotFoundError, UnauthorizedError
from models.auth import ChangePasswordRequest, LoginRequest
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", summary="用户登录")
async def login(req: LoginRequest, request: Request, session: AsyncSession = Depends(get_db)):
    try:
        token, user = await auth_service.login(session, req.username, req.password)
    except UnauthorizedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    request.state.current_user = {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
    }
    return {"code": 200, "message": "登录成功", "data": {"access_token": token, "token_type": "bearer"}}


@router.get("/me")
async def get_me(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        user_info = await auth_service.get_current_user_info(session, current_user["id"])
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": user_info}


@router.put("/password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        await auth_service.change_password(session, current_user["id"], req.old_password, req.new_password)
    except UnauthorizedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "密码修改成功", "data": None}
