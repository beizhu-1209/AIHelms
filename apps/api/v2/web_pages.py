from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from services import web_page_service

router = APIRouter(tags=["Web 页面"])


@router.get("/ai-identity", summary="获取我的 AI 身份页面数据")
async def get_ai_identity(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await web_page_service.get_ai_identity(session, current_user["id"])
    return {"code": 200, "message": "ok", "data": data}


@router.get("/agent-center", summary="获取智能体中心页面数据")
async def get_agent_center(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await web_page_service.get_agent_center(
        session, current_user["id"], page, page_size
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/market", summary="获取 AI 市场页面数据")
async def get_market(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await web_page_service.get_market(
        session, current_user["id"], page, page_size
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/model-square", summary="获取模型广场页面数据")
async def get_model_square(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    data = await web_page_service.get_model_square(session, current_user["id"])
    return {"code": 200, "message": "ok", "data": data}
