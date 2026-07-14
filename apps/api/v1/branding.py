from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from services import branding_service

router = APIRouter(prefix="/branding", tags=["系统"])


@router.get("")
async def get_branding(session: AsyncSession = Depends(get_db)):
    data = await branding_service.get_branding(session)
    return {"code": 200, "message": "ok", "data": data}


@router.put("", summary="更新品牌配置")
async def update_branding(
    platform_name: str = Form(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    data = await branding_service.update_platform_name(session, platform_name)
    return {"code": 200, "message": "品牌配置更新成功", "data": data}


@router.post("/logo", summary="上传 Logo")
async def upload_logo(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    content = await file.read(branding_service.MAX_LOGO_BYTES + 1)
    await branding_service.save_logo(session, content, ext)
    return {"code": 200, "message": "Logo 上传成功", "data": None}


@router.post("/favicon", summary="上传 Favicon")
async def upload_favicon(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    content = await file.read(branding_service.MAX_FAVICON_BYTES + 1)
    await branding_service.save_favicon(session, content, ext)
    return {"code": 200, "message": "Favicon 上传成功", "data": None}


@router.post("/square-logo", summary="上传方形 Logo")
async def upload_square_logo(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    content = await file.read(branding_service.MAX_SQUARE_LOGO_BYTES + 1)
    await branding_service.save_square_logo(session, content, ext)
    return {"code": 200, "message": "方形 Logo 上传成功", "data": None}


def _asset_response(content: bytes, media_type: str) -> Response:
    headers = {"X-Content-Type-Options": "nosniff"}
    if media_type == "image/svg+xml":
        headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'"
        )
    return Response(content=content, media_type=media_type, headers=headers)


@router.get("/logo")
async def get_logo(session: AsyncSession = Depends(get_db)):
    result = await branding_service.read_logo(session)
    if result is None:
        raise HTTPException(status_code=404, detail="未设置 Logo")
    return _asset_response(*result)


@router.get("/favicon")
async def get_favicon(session: AsyncSession = Depends(get_db)):
    result = await branding_service.read_favicon(session)
    if result is None:
        raise HTTPException(status_code=404, detail="未设置 Favicon")
    return _asset_response(*result)


@router.get("/square-logo")
async def get_square_logo(session: AsyncSession = Depends(get_db)):
    result = await branding_service.read_square_logo(session)
    if result is None:
        raise HTTPException(status_code=404, detail="未设置方形 Logo")
    return _asset_response(*result)
