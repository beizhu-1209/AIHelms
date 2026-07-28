import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.time_utils import fmt_local_time
from exceptions import ConflictError, NotFoundError
from models.db import Skill, SkillCategory, SkillUsageLog
from repositories import ai_policies_repo, skill_repo
from services.icon_url import normalize_hosted_icon_path, resolve_icon_url

logger = logging.getLogger(__name__)


async def record_skill_usage(
    session: AsyncSession,
    user_id: int,
    skill_id: int,
    action: str,
    ai_key_id: int | None = None,
) -> None:
    """记录 Skill 使用日志（download / install / agent_download）。失败不影响主流程。"""
    try:
        log = SkillUsageLog(
            user_id=user_id,
            skill_id=skill_id,
            action=action,
            ai_key_id=ai_key_id,
        )
        session.add(log)
        await session.commit()
    except Exception:  # noqa: BLE001
        logger.warning("record skill usage failed", exc_info=True)


def _ensure_skills_dir() -> str:
    base = settings.skills_storage_dir
    os.makedirs(base, exist_ok=True)
    return base


# ─── Skill CRUD ──────────────────────────────────────────────────────────────


async def list_skills(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    category: str | None = None,
    is_published: bool | None = None,
) -> dict:
    total = await skill_repo.count_all(session, category, is_published)
    items = await skill_repo.find_all(session, page, page_size, category, is_published)
    latest_audit_map = await _latest_audit_map(session, items)
    return {
        "items": [_serialize(s, latest_audit_map) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_skill(session: AsyncSession, skill_id: int) -> dict:
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)
    latest_audit_map = await _latest_audit_map(session, [skill])
    return _serialize(skill, latest_audit_map)


async def create_skill(
    session: AsyncSession,
    name: str,
    icon: str = "📦",
    icon_url: str | None = None,
    description: str = "",
    category: str = "general",
    version: str = "1.0.0",
    tags: list | None = None,
    author: str = "",
    agent_install_prompt: str = "",
    usage_instructions: str = "",
    is_published: bool = False,
    requires_approval: bool = False,
    zip_content: bytes | None = None,
    zip_filename: str = "",
    created_by: int | None = None,
) -> dict:
    sid = str(uuid.uuid4())
    zip_path = ""
    zip_size = 0
    if zip_content:
        base_dir = _ensure_skills_dir()
        safe_filename = f"{sid}.zip"
        full_path = os.path.join(base_dir, safe_filename)
        with open(full_path, "wb") as f:
            f.write(zip_content)
        zip_path = full_path
        zip_size = len(zip_content)

    skill = Skill(
        skill_id=sid,
        name=name,
        icon=icon,
        icon_url=normalize_hosted_icon_path(icon_url),
        description=description,
        category=category,
        version=version,
        tags=tags or [],
        author=author,
        agent_install_prompt=agent_install_prompt,
        usage_instructions=usage_instructions,
        zip_path=zip_path,
        zip_size=zip_size,
        zip_filename=zip_filename,
        is_published=is_published,
        requires_approval=requires_approval,
        created_by=created_by,
    )
    skill = await skill_repo.create(session, skill)

    # 发布且不需要审批时，自动同步到所有主 Key
    if is_published and not requires_approval:
        from services import ai_key_service
        await ai_key_service.sync_public_resource_to_all_keys(session, "skills", skill.id)

    await session.commit()
    await session.refresh(skill)
    return _serialize(skill)


async def update_skill(
    session: AsyncSession,
    skill_id: int,
    zip_content: bytes | None = None,
    zip_filename: str | None = None,
    **kwargs,
) -> dict:
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)

    if "icon_url" in kwargs:
        kwargs["icon_url"] = normalize_hosted_icon_path(kwargs["icon_url"])
    elif "icon" in kwargs:
        skill.icon_url = None

    for key, value in kwargs.items():
        if hasattr(skill, key) and value is not None:
            setattr(skill, key, value)

    if zip_content:
        base_dir = _ensure_skills_dir()
        safe_filename = f"{skill.skill_id}.zip"
        full_path = os.path.join(base_dir, safe_filename)
        with open(full_path, "wb") as f:
            f.write(zip_content)
        skill.zip_path = full_path
        skill.zip_size = len(zip_content)
        skill.security_status = "not_scanned"
        skill.security_decision = ""
        skill.security_severity = ""
        skill.security_risk_score = 0
        skill.latest_ai_policies_audit_id = None
        if zip_filename:
            skill.zip_filename = zip_filename

    # 发布且不需要审批时，自动同步到所有主 Key
    if skill.is_published and not skill.requires_approval:
        from services import ai_key_service
        await ai_key_service.sync_public_resource_to_all_keys(session, "skills", skill.id)

    await session.commit()
    await session.refresh(skill)
    return _serialize(skill)


async def delete_skill(session: AsyncSession, skill_id: int) -> None:
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)
    if skill.zip_path and os.path.exists(skill.zip_path):
        try:
            os.remove(skill.zip_path)
        except OSError:
            logger.warning("failed to remove zip file: %s", skill.zip_path)
    await skill_repo.delete(session, skill_id)
    await session.commit()


async def get_skill_zip(session: AsyncSession, skill_id: int, require_published: bool = False) -> tuple[str, str, int]:
    """返回 (zip_path, zip_filename, zip_size)。同时增加下载计数。"""
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)
    if require_published and not skill.is_published:
        raise NotFoundError("skill", skill_id)
    if not skill.zip_path or not os.path.exists(skill.zip_path):
        raise NotFoundError("skill_zip", skill_id)

    skill.install_count = (skill.install_count or 0) + 1
    await session.commit()

    download_name = skill.zip_filename or f"{skill.name}.zip"
    return skill.zip_path, download_name, skill.zip_size


async def get_install_info(
    session: AsyncSession, skill_id: int, user_id: int | None = None
) -> dict:
    """返回 Skill 安装信息：介绍 / agent prompt / 使用说明。
    agent_prompt 由后端按 platform_public_url 拼接的下载 URL 自动生成。
    若提供 user_id，会查找用户主 Key 并在 URL 中嵌入 token。
    """
    skill = await skill_repo.find_by_id(session, skill_id)
    if not skill:
        raise NotFoundError("skill", skill_id)

    base_url = settings.platform_public_url.rstrip("/")
    download_url = f"{base_url}/api/v1/skills/{skill.id}/zip"

    if user_id:
        from repositories import ai_key_repo
        main_key = await ai_key_repo.find_personal_main(session, user_id)
        if main_key and main_key.litellm_key_id:
            download_url = f"{download_url}?token={main_key.litellm_key_id}"

    agent_prompt = f"请帮我下载{download_url} 并安装 {skill.name} 这个skill"

    return {
        "name": skill.name,
        "description": skill.description or "",
        "author": skill.author or "",
        "agent_prompt": agent_prompt,
        "download_url": download_url,
        "usage_instructions": skill.usage_instructions or "",
    }


# ─── Categories ──────────────────────────────────────────────────────────────


async def list_categories(session: AsyncSession) -> list[dict]:
    cats = await skill_repo.list_categories(session)
    return [
        {"id": c.id, "name": c.name, "description": c.description, "sort_order": c.sort_order}
        for c in cats
    ]


async def create_category(
    session: AsyncSession, name: str, description: str = "", sort_order: int = 0
) -> dict:
    existing = await skill_repo.find_category_by_name(session, name)
    if existing:
        raise ConflictError(f"分类 '{name}' 已存在")
    cat = SkillCategory(name=name, description=description, sort_order=sort_order)
    cat = await skill_repo.create_category(session, cat)
    await session.commit()
    return {"id": cat.id, "name": cat.name, "description": cat.description, "sort_order": cat.sort_order}


async def delete_category(session: AsyncSession, category_id: int) -> None:
    cat = await skill_repo.find_category_by_id(session, category_id)
    if not cat:
        raise NotFoundError("skill_category", category_id)
    await skill_repo.delete_category(session, category_id)
    await session.commit()


# ─── Serializer ──────────────────────────────────────────────────────────────


async def _latest_audit_map(
    session: AsyncSession, skills: list[Skill]
) -> dict[int, str]:
    audit_ids = [
        skill.latest_ai_policies_audit_id
        for skill in skills
        if skill.latest_ai_policies_audit_id
    ]
    audits = await ai_policies_repo.find_by_ids(session, audit_ids)
    return {audit.id: audit.audit_id for audit in audits}


def _serialize(skill: Skill, latest_audit_map: dict[int, str] | None = None) -> dict:
    latest_audit_map = latest_audit_map or {}
    latest_audit_code = (
        latest_audit_map.get(skill.latest_ai_policies_audit_id)
        if skill.latest_ai_policies_audit_id
        else None
    )
    return {
        "id": skill.id,
        "skill_id": skill.skill_id,
        "name": skill.name,
        "icon": skill.icon,
        "icon_url": resolve_icon_url(skill.icon_url or skill.icon),
        "description": skill.description,
        "category": skill.category,
        "version": skill.version,
        "tags": skill.tags,
        "author": skill.author,
        "agent_install_prompt": skill.agent_install_prompt,
        "usage_instructions": skill.usage_instructions,
        "zip_path": skill.zip_path,
        "zip_size": skill.zip_size,
        "zip_filename": skill.zip_filename,
        "has_zip": bool(skill.zip_path),
        "is_active": skill.is_active,
        "is_published": skill.is_published,
        "requires_approval": skill.requires_approval,
        "install_count": skill.install_count,
        "security_status": skill.security_status,
        "security_decision": skill.security_decision,
        "security_severity": skill.security_severity,
        "security_risk_score": skill.security_risk_score,
        "latest_ai_policies_audit_id": skill.latest_ai_policies_audit_id,
        "latest_ai_policies_audit_code": latest_audit_code,
        "created_by": skill.created_by,
        "created_at": fmt_local_time(skill.created_at),
        "updated_at": fmt_local_time(skill.updated_at),
    }
