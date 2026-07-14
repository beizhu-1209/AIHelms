from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db, require_permission
from exceptions import ValidationError
from services import license_service

router = APIRouter(prefix="/license", tags=["系统"])


@router.get("")
async def get_license(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    data = await license_service.get_status(session)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/import", summary="导入 License")
async def import_license(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("user:read")),
):
    content = await file.read(license_service.MAX_LICENSE_BYTES + 1)
    try:
        token = content.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValidationError("License 文件编码无效") from exc
    data = await license_service.import_license(session, token)
    return {"code": 200, "message": "License 导入成功", "data": data}
