from fastapi import APIRouter, Depends, HTTPException

from core.deps import get_current_user
from exceptions import UnauthorizedError, NotFoundError
from models.auth import LoginRequest, TokenResponse, ChangePasswordRequest
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginRequest):
    try:
        token = await auth_service.login(req.username, req.password)
    except UnauthorizedError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return {"code": 200, "message": "ok", "data": {"access_token": token, "token_type": "bearer"}}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    try:
        user_info = await auth_service.get_current_user_info(current_user["id"])
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": user_info}


@router.put("/password")
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        await auth_service.change_password(current_user["id"], req.old_password, req.new_password)
    except UnauthorizedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"code": 200, "message": "ok", "data": None}
