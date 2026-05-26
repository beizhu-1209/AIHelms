"""管理后台 Dashboard API。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await dashboard_service.get_dashboard(session)
    return {"code": 200, "message": "ok", "data": data}
