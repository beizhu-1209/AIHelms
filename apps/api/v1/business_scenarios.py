import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from services import business_scenario_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/business-scenarios", tags=["business-scenarios"])


class CreateScenarioRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)
    icon: str = Field("Target", max_length=50)
    sort_order: int = Field(0)


class UpdateScenarioRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    icon: str | None = Field(None, max_length=50)
    sort_order: int | None = Field(None)
    is_active: bool | None = Field(None)


@router.get("")
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    keyword: str | None = Query(None),
    include_inactive: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await business_scenario_service.list_scenarios(
        session, page, page_size, keyword, include_inactive
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/all")
async def get_all_scenarios(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    items = await business_scenario_service.get_all_active(session)
    return {"code": 200, "message": "ok", "data": items}


@router.post("", summary="创建业务场景")
async def create_scenario(
    req: CreateScenarioRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        scenario = await business_scenario_service.create_scenario(
            session,
            code=req.code,
            name=req.name,
            description=req.description,
            icon=req.icon,
            sort_order=req.sort_order,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "业务场景创建成功", "data": scenario}


@router.put("/{scenario_id}", summary="更新业务场景")
async def update_scenario(
    scenario_id: int,
    req: UpdateScenarioRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        scenario = await business_scenario_service.update_scenario(
            session,
            scenario_id,
            name=req.name,
            description=req.description,
            icon=req.icon,
            sort_order=req.sort_order,
            is_active=req.is_active,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="业务场景不存在")
    return {"code": 200, "message": "业务场景更新成功", "data": scenario}


@router.delete("/{scenario_id}", summary="删除业务场景")
async def delete_scenario(
    scenario_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await business_scenario_service.delete_scenario(session, scenario_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="业务场景不存在")
    return {"code": 200, "message": "业务场景删除成功", "data": None}
