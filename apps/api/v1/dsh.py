from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response

from core.config import settings
from core.deps import get_current_user
from core.security import create_access_token

router = APIRouter(prefix="/dsh", tags=["DS Harness"])


@router.get("/session")
async def create_dsh_session(
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict[str, object]:
    if not settings.dsh_enabled:
        raise HTTPException(status_code=404, detail="DS Harness 未启用")
    session_token = create_access_token(
        {"sub": str(current_user["id"]), "dsh_session": True},
        expires_delta=timedelta(minutes=10),
    )
    response.set_cookie(
        key="dsh_session",
        value=session_token,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return {"code": 200, "message": "ok", "data": {"path": "/dsh/"}}
