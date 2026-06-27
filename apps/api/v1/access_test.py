from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from models.db import Model
from repositories import model_repo
from services import access_test_service
from services.access_test_error_mapper import build_failure
from services.access_test_precheck import precheck_access_test

router = APIRouter(prefix="/access-test", tags=["access-test"])

STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


class TestAccessRequest(BaseModel):
    model: str = Field(..., min_length=1, description="模型 ID（如 claude-opus-4-6）")
    messages: list[dict] = Field(
        default_factory=lambda: [{"role": "user", "content": "hi"}],
        description="消息列表",
    )
    stream: bool = Field(default=True, description="是否流式输出")
    max_tokens: int = Field(default=100, ge=1, le=4096, description="最大输出 token 数")


class TestEmbeddingRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Embedding 模型 ID")
    text: str = Field(default="你好世界", description="测试文本")


class TestRerankRequest(BaseModel):
    model: str = Field(..., min_length=1, description="Rerank 模型 ID")
    query: str = Field(default="什么是人工智能？", description="查询文本")
    documents: list[str] = Field(
        default_factory=lambda: [
            "人工智能是计算机科学的一个分支",
            "今天天气很好",
            "机器学习是AI的核心技术",
        ],
        description="待排序文档列表",
    )


@router.post("/test", summary="模型连通性测试")
async def test_access(
    req: TestAccessRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:read")),
):
    # 自动判断模型类型
    model_id = req.model
    model_obj = await model_repo.find_by_model_id(session, model_id)
    if not model_obj and "/" in model_id:
        model_obj = await model_repo.find_by_model_id(session, model_id.split("/")[-1])
    category = model_obj.category if model_obj else "chat"
    test_model = model_obj.model_id if model_obj and model_obj.model_id else model_id
    user_key, error_detail = await precheck_access_test(
        session,
        current_user["id"],
        model_obj,
        test_model,
        is_admin=current_user["is_admin"],
    )
    if error_detail:
        return _build_error_response(error_detail, category, req.stream)
    user_api_key = user_key.litellm_key_id if user_key else ""

    if category == "embedding":
        text = (
            req.messages[0].get("content", "你好世界") if req.messages else "你好世界"
        )
        result = await access_test_service.test_embedding(
            model=test_model,
            text=text,
            api_key=user_api_key,
        )
        return {"code": 200, "message": "Embedding 测试完成", "data": result}

    if category == "rerank":
        query = (
            req.messages[0].get("content", "什么是人工智能？")
            if req.messages
            else "什么是人工智能？"
        )
        result = await access_test_service.test_rerank(
            model=test_model,
            query=query,
            documents=[
                "人工智能是计算机科学的一个分支",
                "今天天气很好",
                "机器学习是AI的核心技术",
            ],
            api_key=user_api_key,
        )
        return {"code": 200, "message": "Rerank 测试完成", "data": result}

    if req.stream:
        return StreamingResponse(
            access_test_service.test_model_stream(
                model=test_model,
                messages=req.messages,
                max_tokens=req.max_tokens,
                api_key=user_api_key,
            ),
            media_type="text/event-stream",
            headers=STREAM_HEADERS,
        )
    result = await access_test_service.test_model_sync(
        model=test_model,
        messages=req.messages,
        max_tokens=req.max_tokens,
        api_key=user_api_key,
    )
    return {"code": 200, "message": "模型测试完成", "data": result}


def _build_error_response(
    error_detail: dict[str, object],
    category: str,
    stream: bool,
) -> dict[str, object] | StreamingResponse:
    if category == "chat" and stream:
        return StreamingResponse(
            access_test_service.test_error_stream(error_detail),
            media_type="text/event-stream",
            headers=STREAM_HEADERS,
        )
    return {
        "code": 200,
        "message": "模型测试完成",
        "data": build_failure(error_detail),
    }


async def _resolve_model(
    session: AsyncSession, model_id: str
) -> tuple[Model | None, str]:
    model_obj = await model_repo.find_by_model_id(session, model_id)
    if not model_obj and "/" in model_id:
        model_obj = await model_repo.find_by_model_id(session, model_id.split("/")[-1])
    test_model = model_obj.model_id if model_obj and model_obj.model_id else model_id
    return model_obj, test_model


@router.post("/test-embedding", summary="Embedding 测试")
async def test_embedding(
    req: TestEmbeddingRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:read")),
):
    model_obj, test_model = await _resolve_model(session, req.model)
    user_key, error_detail = await precheck_access_test(
        session,
        current_user["id"],
        model_obj,
        test_model,
        is_admin=current_user["is_admin"],
    )
    if error_detail:
        return {
            "code": 200,
            "message": "Embedding 测试完成",
            "data": build_failure(error_detail),
        }
    result = await access_test_service.test_embedding(
        model=test_model,
        text=req.text,
        api_key=user_key.litellm_key_id if user_key else "",
    )
    return {"code": 200, "message": "Embedding 测试完成", "data": result}


@router.post("/test-rerank", summary="Rerank 测试")
async def test_rerank(
    req: TestRerankRequest,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("user:read")),
):
    model_obj, test_model = await _resolve_model(session, req.model)
    user_key, error_detail = await precheck_access_test(
        session,
        current_user["id"],
        model_obj,
        test_model,
        is_admin=current_user["is_admin"],
    )
    if error_detail:
        return {
            "code": 200,
            "message": "Rerank 测试完成",
            "data": build_failure(error_detail),
        }
    result = await access_test_service.test_rerank(
        model=test_model,
        query=req.query,
        documents=req.documents,
        api_key=user_key.litellm_key_id if user_key else "",
    )
    return {"code": 200, "message": "Rerank 测试完成", "data": result}
