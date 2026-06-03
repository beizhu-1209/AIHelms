from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, get_current_user, require_permission
from exceptions import NotFoundError, ConflictError, ValidationError
from services import ai_key_service
from services import litellm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-keys", tags=["ai-keys"])


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    key_type: str = Field(..., pattern=r"^(personal_main|personal_scene|dept_main|dept_scene|project_main|project_scene)$")
    owner_type: str = Field(..., pattern=r"^(user|department|project)$")
    owner_id: int
    description: str = Field("", max_length=500)
    tags: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    mcps: list[int] = Field(default_factory=list)
    skills: list[int] = Field(default_factory=list)
    agents: list[int] = Field(default_factory=list)
    budget_limit: Decimal | None = None
    budget_hard_limit: bool = False
    budget_duration: str | None = Field("30d", pattern=r"^(1d|7d|30d)$")
    budget_scope: str = Field("unified", pattern=r"^(unified|per_type|per_resource)$")
    budget_models_total: Decimal | None = None
    budget_mcps_total: Decimal | None = None
    budget_models_per: str = Field("unified", pattern=r"^(unified|each)$")
    budget_mcps_per: str = Field("unified", pattern=r"^(unified|each)$")
    model_budgets: dict[str, float] | None = None
    mcp_budgets: dict[str, float] | None = None
    scenario_id: int | None = None
    duration: str | None = None
    rate_limits: list[dict] | None = None


class UpdateKeyRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    models: list[str] | None = None
    mcps: list[int] | None = None
    skills: list[int] | None = None
    agents: list[int] | None = None
    budget_limit: Decimal | None = None
    budget_hard_limit: bool | None = None
    budget_duration: str | None = Field(None, pattern=r"^(1d|7d|30d)$")
    budget_scope: str | None = Field(None, pattern=r"^(unified|per_type|per_resource)$")
    budget_models_total: Decimal | None = None
    budget_mcps_total: Decimal | None = None
    budget_models_per: str | None = Field(None, pattern=r"^(unified|each)$")
    budget_mcps_per: str | None = Field(None, pattern=r"^(unified|each)$")
    model_budgets: dict[str, float] | None = None
    mcp_budgets: dict[str, float] | None = None
    scenario_id: int | None = None
    rate_limits: list[dict] | None = None


class BatchUpdateRequest(BaseModel):
    key_ids: list[int] | None = None
    user_ids: list[int] | None = None
    models: list[str] | None = None
    mcps: list[int] | None = None
    skills: list[int] | None = None
    agents: list[int] | None = None
    budget_limit: Decimal | None = None
    budget_hard_limit: bool | None = None
    budget_duration: str | None = Field(None, pattern=r"^(1d|7d|30d)$")
    budget_scope: str | None = Field(None, pattern=r"^(unified|per_type|per_resource)$")
    budget_models_total: Decimal | None = None
    budget_mcps_total: Decimal | None = None
    budget_models_per: str | None = Field(None, pattern=r"^(unified|each)$")
    budget_mcps_per: str | None = Field(None, pattern=r"^(unified|each)$")
    model_budgets: dict[str, float] | None = None
    mcp_budgets: dict[str, float] | None = None


class BatchCreateRequest(BaseModel):
    user_ids: list[int] = Field(..., min_length=1)
    key_type: str = Field(..., pattern=r"^(personal_main|personal_scene)$")
    name_template: str = Field(..., min_length=1, max_length=128)
    description: str = Field("", max_length=500)
    models: list[str] = Field(default_factory=list)
    mcps: list[int] = Field(default_factory=list)
    skills: list[int] = Field(default_factory=list)
    agents: list[int] = Field(default_factory=list)
    budget_limit: Decimal | None = None
    budget_hard_limit: bool = False
    budget_duration: str | None = Field("30d", pattern=r"^(1d|7d|30d)$")
    budget_scope: str = Field("unified", pattern=r"^(unified|per_type|per_resource)$")
    budget_models_total: Decimal | None = None
    budget_mcps_total: Decimal | None = None
    budget_models_per: str = Field("unified", pattern=r"^(unified|each)$")
    budget_mcps_per: str = Field("unified", pattern=r"^(unified|each)$")
    model_budgets: dict[str, float] | None = None
    mcp_budgets: dict[str, float] | None = None
    scenario_id: int | None = None
    rate_limits: list[dict] | None = None


class ModelLimitItem(BaseModel):
    model_id: int
    tpm: int | None = Field(None, ge=1)
    rpm: int | None = Field(None, ge=1)
    max_tokens: int | None = Field(None, ge=1)
    max_calls: int | None = Field(None, ge=1)


class SetModelLimitsRequest(BaseModel):
    limits: list[ModelLimitItem]


@router.get("")
async def list_keys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    owner_type: str | None = Query(None),
    owner_id: int | None = Query(None),
    key_type: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    result = await ai_key_service.list_keys(session, page, page_size, owner_type, owner_id, key_type)
    return {"code": 200, "message": "ok", "data": result}


@router.post("", summary="创建 AI 身份 Key")
async def create_key(
    req: CreateKeyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.create_key(
            session,
            name=req.name,
            key_type=req.key_type,
            owner_type=req.owner_type,
            owner_id=req.owner_id,
            created_by=current_user["id"],
            description=req.description,
            tags=req.tags,
            models=req.models,
            mcps=req.mcps,
            skills=req.skills,
            agents=req.agents,
            budget_limit=req.budget_limit,
            budget_hard_limit=req.budget_hard_limit,
            budget_duration=req.budget_duration,
            budget_scope=req.budget_scope,
            budget_models_total=req.budget_models_total,
            budget_mcps_total=req.budget_mcps_total,
            budget_models_per=req.budget_models_per,
            budget_mcps_per=req.budget_mcps_per,
            model_budgets=req.model_budgets,
            mcp_budgets=req.mcp_budgets,
            scenario_id=req.scenario_id,
            duration=req.duration,
            rate_limits=req.rate_limits,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 200, "message": "AI Key 创建成功", "data": key}


@router.post("/batch", summary="批量创建 AI 身份 Key")
async def batch_create_keys(
    req: BatchCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:update")),
):
    from exceptions import ValidationError as VE
    try:
        results = await ai_key_service.batch_create_keys(
            session,
            user_ids=req.user_ids,
            key_type=req.key_type,
            name_template=req.name_template,
            created_by=current_user["id"],
            description=req.description,
            models=req.models,
            mcps=req.mcps,
            skills=req.skills,
            agents=req.agents,
            budget_limit=req.budget_limit,
            budget_hard_limit=req.budget_hard_limit,
            budget_duration=req.budget_duration,
            budget_scope=req.budget_scope,
            budget_models_total=req.budget_models_total,
            budget_mcps_total=req.budget_mcps_total,
            budget_models_per=req.budget_models_per,
            budget_mcps_per=req.budget_mcps_per,
            model_budgets=req.model_budgets,
            mcp_budgets=req.mcp_budgets,
            scenario_id=req.scenario_id,
            rate_limits=req.rate_limits,
        )
    except VE as e:
        raise HTTPException(status_code=400, detail=str(e))
    success_count = sum(1 for r in results if r["success"])
    return {
        "code": 200,
        "message": f"批量创建完成，成功 {success_count}/{len(results)}",
        "data": results,
    }


@router.get("/my")
async def get_my_keys(
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await ai_key_service.get_my_keys(session, current_user["id"])
    return {"code": 200, "message": "ok", "data": result}


@router.get("/identity")
async def list_identity(
    tab: str = Query(..., pattern=r"^(user|department|project)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        result = await ai_key_service.list_identity(session, tab, page, page_size, keyword)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "ok", "data": result}


@router.get("/{key_id}/model-limits")
async def get_model_limits(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        limits = await ai_key_service.get_model_limits(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": limits}


@router.put("/{key_id}/model-limits", summary="更新 Key 模型限制")
async def set_model_limits(
    key_id: int,
    req: SetModelLimitsRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        limits = await ai_key_service.set_model_limits(
            session, key_id, [item.model_dump() for item in req.limits]
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 200, "message": "模型限制更新成功", "data": limits}


@router.delete("/{key_id}/model-limits/{model_id}", summary="删除 Key 模型限制")
async def delete_model_limit(
    key_id: int,
    model_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        await ai_key_service.delete_model_limit(session, key_id, model_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="限制记录不存在")
    return {"code": 200, "message": "模型限制删除成功", "data": None}


@router.get("/{key_id}")
async def get_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    try:
        key = await ai_key_service.get_key_by_id(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "ok", "data": key}


@router.put("/batch", summary="批量更新 AI 身份 Key")
async def batch_update_keys(
    req: BatchUpdateRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    key_ids = list(req.key_ids) if req.key_ids else []
    if req.user_ids:
        from repositories import ai_key_repo
        for uid in req.user_ids:
            main_key = await ai_key_repo.find_personal_main(session, uid)
            if main_key:
                key_ids.append(main_key.id)
    if not key_ids:
        raise HTTPException(status_code=400, detail="未找到可更新的 Key")
    successes: list[int] = []
    failures: list[dict] = []
    for key_id in key_ids:
        try:
            await ai_key_service.update_key(
                session, key_id,
                models=req.models,
                mcps=req.mcps,
                skills=req.skills,
                agents=req.agents,
                budget_limit=req.budget_limit,
                budget_hard_limit=req.budget_hard_limit,
                budget_duration=req.budget_duration,
                budget_scope=req.budget_scope,
                budget_models_total=req.budget_models_total,
                budget_mcps_total=req.budget_mcps_total,
                budget_models_per=req.budget_models_per,
                budget_mcps_per=req.budget_mcps_per,
                model_budgets=req.model_budgets,
                mcp_budgets=req.mcp_budgets,
            )
            successes.append(key_id)
        except NotFoundError:
            failures.append({"key_id": key_id, "error": "Key 不存在"})
        except Exception as e:
            failures.append({"key_id": key_id, "error": str(e)})
    return {
        "code": 200,
        "message": f"批量更新完成，成功 {len(successes)}/{len(key_ids)}",
        "data": {"successes": successes, "failures": failures},
    }


@router.put("/{key_id}", summary="更新 AI 身份 Key")
async def update_key(
    key_id: int,
    req: UpdateKeyRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.update_key(
            session, key_id,
            name=req.name,
            description=req.description,
            tags=req.tags,
            models=req.models,
            mcps=req.mcps,
            skills=req.skills,
            agents=req.agents,
            budget_limit=req.budget_limit,
            budget_hard_limit=req.budget_hard_limit,
            budget_duration=req.budget_duration,
            budget_scope=req.budget_scope,
            budget_models_total=req.budget_models_total,
            budget_mcps_total=req.budget_mcps_total,
            budget_models_per=req.budget_models_per,
            budget_mcps_per=req.budget_mcps_per,
            model_budgets=req.model_budgets,
            mcp_budgets=req.mcp_budgets,
            scenario_id=req.scenario_id,
            rate_limits=req.rate_limits,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "AI Key 更新成功", "data": key}


@router.put("/{key_id}/toggle", summary="切换 Key 启用状态")
async def toggle_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:update")),
):
    try:
        key = await ai_key_service.toggle_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "状态切换成功", "data": key}


@router.delete("/{key_id}", summary="删除 AI 身份 Key")
async def delete_key(
    key_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:delete")),
):
    try:
        await ai_key_service.delete_key(session, key_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Key 不存在")
    return {"code": 200, "message": "AI Key 删除成功", "data": None}


@router.get("/available-models")
async def get_available_models(
    _: dict = Depends(require_permission("user:read")),
):
    try:
        models = await litellm_client.list_models()
        model_names = [m.get("model_name", m.get("model_info", {}).get("id", "")) for m in models if m]
        model_names = sorted(set(n for n in model_names if n))
    except litellm_client.LiteLLMError:
        logger.warning("failed to fetch models from litellm")
        model_names = []
    return {"code": 200, "message": "ok", "data": model_names}
