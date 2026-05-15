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


@router.post("/test")
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
