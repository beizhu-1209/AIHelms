from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.deps import require_permission
from services import access_test_service

router = APIRouter(prefix="/access-test", tags=["access-test"])


class TestAccessRequest(BaseModel):
    model: str = Field(..., min_length=1, description="模型 ID（如 claude-opus-4-6）")
    messages: list[dict] = Field(
        default_factory=lambda: [{"role": "user", "content": "hi"}],
        description="消息列表",
    )
    stream: bool = Field(default=True, description="是否流式输出")


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
    _: dict = Depends(require_permission("user:read")),
):
    if req.stream:
        return StreamingResponse(
            access_test_service.test_model_stream(
                model=req.model,
                messages=req.messages,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    result = await access_test_service.test_model_sync(
        model=req.model,
        messages=req.messages,
    )
    return {"code": 200, "message": "模型测试完成", "data": result}


@router.post("/test-embedding", summary="Embedding 测试")
async def test_embedding(
    req: TestEmbeddingRequest,
    _: dict = Depends(require_permission("user:read")),
):
    result = await access_test_service.test_embedding(
        model=req.model,
        text=req.text,
    )
    return {"code": 200, "message": "Embedding 测试完成", "data": result}


@router.post("/test-rerank", summary="Rerank 测试")
async def test_rerank(
    req: TestRerankRequest,
    _: dict = Depends(require_permission("user:read")),
):
    result = await access_test_service.test_rerank(
        model=req.model,
        query=req.query,
        documents=req.documents,
    )
    return {"code": 200, "message": "Rerank 测试完成", "data": result}
