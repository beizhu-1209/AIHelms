import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import NotFoundError, ConflictError
from services import key_scenario_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/key-scenarios", tags=["key-scenarios"])


class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field("", max_length=500)


class UpdateScenarioRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = Field(None, max_length=500)


@router.get("")
async def list_scenarios(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    keyword: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await key_scenario_service.list_scenarios(session, page, page_size, keyword)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/all")
async def get_all_scenarios(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    items = await key_scenario_service.get_all_active(session)
    return {"code": 200, "message": "ok", "data": items}


@router.post("")
async def create_scenario(
    req: CreateScenarioRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        scenario = await key_scenario_service.create_scenario(
            session, name=req.name, description=req.description
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "场景创建成功", "data": scenario}


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: int,
    req: UpdateScenarioRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        scenario = await key_scenario_service.update_scenario(
            session, scenario_id, name=req.name, description=req.description
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="场景不存在")
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "场景更新成功", "data": scenario}


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await key_scenario_service.delete_scenario(session, scenario_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="场景不存在")
    return {"code": 200, "message": "场景删除成功", "data": None}
