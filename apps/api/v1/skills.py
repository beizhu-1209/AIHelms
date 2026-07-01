import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_ai_key_identity, get_current_user, get_db, require_permission
from exceptions import ConflictError, NotFoundError
from services import skill_service

router = APIRouter(prefix="/skills", tags=["skills"])


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field("", max_length=200)
    sort_order: int = 0


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:read")),
):
    data = await skill_service.list_categories(session)
    return {"code": 200, "message": "ok", "data": data}


@router.post("/categories", summary="创建 Skill 分类")
async def create_category(
    req: CreateCategoryRequest,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:create")),
):
    try:
        data = await skill_service.create_category(
            session, name=req.name, description=req.description, sort_order=req.sort_order
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"code": 200, "message": "分类创建成功", "data": data}


@router.delete("/categories/{category_id}", summary="删除 Skill 分类")
async def delete_category(
    category_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:delete")),
):
    try:
        await skill_service.delete_category(session, category_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="分类不存在")
    return {"code": 200, "message": "分类删除成功", "data": None}


@router.get("/published")
async def list_published_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """公开接口：已认证用户可查看已发布的 Skill 列表。"""
    data = await skill_service.list_skills(session, page, page_size, category, is_published=True)
    return {"code": 200, "message": "ok", "data": data}


@router.get("")
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: str | None = None,
    is_published: bool | None = None,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:read")),
):
    data = await skill_service.list_skills(session, page, page_size, category, is_published)
    return {"code": 200, "message": "ok", "data": data}


@router.get("/{skill_id}")
async def get_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:read")),
):
    try:
        data = await skill_service.get_skill(session, skill_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.post("", summary="创建 Skill")
async def create_skill(
    name: str = Form(...),
    icon: str = Form("📦"),
    description: str = Form(""),
    category: str = Form("general"),
    version: str = Form("1.0.0"),
    tags: str = Form("[]"),
    author: str = Form(""),
    agent_install_prompt: str = Form(""),
    usage_instructions: str = Form(""),
    is_published: bool = Form(False),
    requires_approval: bool = Form(False),
    zip_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("skill:create")),
):
    try:
        tags_list = json.loads(tags) if tags else []
    except json.JSONDecodeError:
        tags_list = []
    zip_content = None
    zip_filename = ""
    if zip_file is not None and zip_file.filename:
        zip_content = await zip_file.read()
        zip_filename = zip_file.filename

    data = await skill_service.create_skill(
        session,
        name=name,
        icon=icon,
        description=description,
        category=category,
        version=version,
        tags=tags_list,
        author=author,
        agent_install_prompt=agent_install_prompt,
        usage_instructions=usage_instructions,
        is_published=is_published,
        requires_approval=requires_approval,
        zip_content=zip_content,
        zip_filename=zip_filename,
        created_by=current_user["id"],
    )
    return {"code": 200, "message": "Skill 创建成功", "data": data}


@router.put("/{skill_id}", summary="更新 Skill")
async def update_skill(
    skill_id: int,
    name: str | None = Form(None),
    icon: str | None = Form(None),
    description: str | None = Form(None),
    category: str | None = Form(None),
    version: str | None = Form(None),
    tags: str | None = Form(None),
    author: str | None = Form(None),
    agent_install_prompt: str | None = Form(None),
    usage_instructions: str | None = Form(None),
    is_active: bool | None = Form(None),
    is_published: bool | None = Form(None),
    requires_approval: bool | None = Form(None),
    zip_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:update")),
):
    kwargs: dict = {}
    if name is not None:
        kwargs["name"] = name
    if icon is not None:
        kwargs["icon"] = icon
    if description is not None:
        kwargs["description"] = description
    if category is not None:
        kwargs["category"] = category
    if version is not None:
        kwargs["version"] = version
    if tags is not None:
        try:
            kwargs["tags"] = json.loads(tags)
        except json.JSONDecodeError:
            kwargs["tags"] = []
    if author is not None:
        kwargs["author"] = author
    if agent_install_prompt is not None:
        kwargs["agent_install_prompt"] = agent_install_prompt
    if usage_instructions is not None:
        kwargs["usage_instructions"] = usage_instructions
    if is_active is not None:
        kwargs["is_active"] = is_active
    if is_published is not None:
        kwargs["is_published"] = is_published
    if requires_approval is not None:
        kwargs["requires_approval"] = requires_approval

    zip_content = None
    zip_filename = None
    if zip_file is not None and zip_file.filename:
        zip_content = await zip_file.read()
        zip_filename = zip_file.filename

    try:
        data = await skill_service.update_skill(
            session, skill_id, zip_content=zip_content, zip_filename=zip_filename, **kwargs
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return {"code": 200, "message": "Skill 更新成功", "data": data}


@router.delete("/{skill_id}", summary="删除 Skill")
async def delete_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permission("skill:delete")),
):
    try:
        await skill_service.delete_skill(session, skill_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return {"code": 200, "message": "Skill 删除成功", "data": None}


@router.get("/{skill_id}/download")
async def download_skill(
    skill_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_permission("skill:read")),
):
    try:
        zip_path, download_name, _ = await skill_service.get_skill_zip(session, skill_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 或 zip 文件不存在")
    await skill_service.record_skill_usage(
        session, user_id=current_user["id"], skill_id=skill_id, action="download"
    )
    return FileResponse(zip_path, filename=download_name, media_type="application/zip")


@router.get("/{skill_id}/install-info")
async def get_install_info(
    skill_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    try:
        data = await skill_service.get_install_info(
            session, skill_id, user_id=current_user["id"]
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 不存在")
    return {"code": 200, "message": "ok", "data": data}


@router.get("/{skill_id}/zip", summary="Agent 下载 Skill zip")
async def get_skill_zip_public(
    skill_id: int,
    session: AsyncSession = Depends(get_db),
    identity: dict = Depends(get_ai_key_identity),
):
    """Agent 下载端点，通过 AI Key 认证。仅已发布的 Skill 可下载。"""
    try:
        zip_path, download_name, _ = await skill_service.get_skill_zip(
            session, skill_id, require_published=True
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Skill 或 zip 文件不存在")

    # 权限检查：需审批的 Skill 必须在 Key 的 skills 列表中
    skill_data = await skill_service.get_skill(session, skill_id)
    if skill_data.get("requires_approval"):
        if skill_id not in identity["skills"]:
            raise HTTPException(status_code=403, detail="请先申请使用该 Skill")

    await skill_service.record_skill_usage(
        session,
        user_id=identity["user_id"],
        skill_id=skill_id,
        action="agent_download",
        ai_key_id=identity["ai_key_id"],
    )
    return FileResponse(zip_path, filename=download_name, media_type="application/zip")
