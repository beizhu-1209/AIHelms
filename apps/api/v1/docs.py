"""用户端接入文档 API。"""

from fastapi import APIRouter, Depends

from core.deps import get_current_user
from services import docs_service

router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("")
async def list_docs(
    _: dict = Depends(get_current_user),
):
    return {"code": 200, "message": "ok", "data": docs_service.list_docs()}


@router.get("/{slug}")
async def get_doc(
    slug: str,
    _: dict = Depends(get_current_user),
):
    doc = docs_service.get_doc(slug)
    if not doc:
        return {"code": 404, "message": "文档不存在", "data": None}
    return {"code": 200, "message": "ok", "data": doc}
