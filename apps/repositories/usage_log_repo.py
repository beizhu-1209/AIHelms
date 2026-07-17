"""使用日志查询 Repository（LLM / MCP / Skill / Agent 4 类）。

仅查询；写入由对应同步任务或埋点处理。
"""

from datetime import datetime

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import (
    Agent,
    AgentUsageLog,
    AiKey,
    Credential,
    Department,
    LlmCallLog,
    McpCallLog,
    McpServer,
    Model,
    ModelDeployment,
    Skill,
    SkillUsageLog,
    User,
    UserDepartment,
)

# ────────────── LLM ──────────────

_ANTHROPIC_MODEL_SUFFIX = "(Anthropic)"


def _llm_model_lookup_names(model_name: str) -> set[str]:
    names = {model_name}
    if model_name.endswith(_ANTHROPIC_MODEL_SUFFIX):
        names.add(model_name[: -len(_ANTHROPIC_MODEL_SUFFIX)])
    for name in list(names):
        if "/" in name:
            names.add(name.split("/", 1)[1])
    return {name for name in names if name}


def _normalized_llm_model_names(model_names: set[str]) -> set[str]:
    names: set[str] = set()
    for model_name in model_names:
        lookup_names = _llm_model_lookup_names(str(model_name).strip())
        names.update(name.lower() for name in lookup_names)
    return names


def _is_current_llm_model(model_name: str, current_model_names: set[str]) -> bool:
    return bool(
        _normalized_llm_model_names({model_name})
        & _normalized_llm_model_names(current_model_names)
    )


def _routable_deployment_condition():
    return (
        Model.is_active.is_(True),
        ModelDeployment.is_active.is_(True),
        or_(
            ModelDeployment.credential_id.is_(None),
            Credential.is_active.is_(True),
        ),
    )


def _current_llm_model_names(
    model_rows: list[tuple[str | None, str | None, dict | None]],
) -> set[str]:
    names: set[str] = set()
    for model_id, model_name, litellm_params in model_rows:
        if model_id:
            names.add(model_id)
        if model_name:
            names.add(model_name)
        if isinstance(litellm_params, dict):
            litellm_model = litellm_params.get("model")
            if litellm_model:
                names.add(str(litellm_model))
    return names


def _is_active_llm_model_option(
    model_name: str, id_active_model_names: set[str], current_model_names: set[str]
) -> bool:
    if model_name in id_active_model_names:
        return True
    return _is_current_llm_model(model_name, current_model_names)


def _apply_llm_filters(
    stmt,
    start_time,
    end_time,
    user_id,
    ai_key_id,
    model,
    models,
    provider,
    status,
):
    if start_time is not None:
        stmt = stmt.where(LlmCallLog.started_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(LlmCallLog.started_at <= end_time)
    if user_id is not None:
        stmt = stmt.where(LlmCallLog.user_id == user_id)
    if ai_key_id is not None:
        stmt = stmt.where(LlmCallLog.ai_key_id == ai_key_id)
    if models:
        stmt = stmt.where(LlmCallLog.model.in_(models))
    elif model:
        stmt = stmt.where(LlmCallLog.model == model)
    if provider:
        stmt = stmt.where(LlmCallLog.provider == provider)
    if status == "success":
        stmt = stmt.where(LlmCallLog.status == "success")
    elif status == "failure":
        stmt = stmt.where(LlmCallLog.status != "success")
    return stmt


async def find_llm_logs(
    session: AsyncSession,
    page: int,
    page_size: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    model: str | None = None,
    models: list[str] | None = None,
    provider: str | None = None,
    status: str | None = None,
) -> list[LlmCallLog]:
    stmt = select(LlmCallLog).order_by(LlmCallLog.started_at.desc())
    stmt = _apply_llm_filters(
        stmt, start_time, end_time, user_id, ai_key_id, model, models, provider, status
    )
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_llm_logs(
    session: AsyncSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    model: str | None = None,
    models: list[str] | None = None,
    provider: str | None = None,
    status: str | None = None,
) -> int:
    stmt = select(func.count(LlmCallLog.id))
    stmt = _apply_llm_filters(
        stmt, start_time, end_time, user_id, ai_key_id, model, models, provider, status
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_llm_log_by_id(session: AsyncSession, log_id: int) -> LlmCallLog | None:
    result = await session.execute(select(LlmCallLog).where(LlmCallLog.id == log_id))
    return result.scalar_one_or_none()


async def llm_log_filters(session: AsyncSession) -> dict:
    actors = (await session.execute(
        select(distinct(LlmCallLog.user_id)).where(LlmCallLog.user_id.isnot(None))
    )).scalars().all()
    keys = (await session.execute(
        select(distinct(LlmCallLog.ai_key_id)).where(LlmCallLog.ai_key_id.isnot(None))
    )).scalars().all()
    models = (await session.execute(
        select(distinct(LlmCallLog.model)).order_by(LlmCallLog.model)
    )).scalars().all()
    providers = (await session.execute(
        select(distinct(LlmCallLog.provider))
        .where(LlmCallLog.provider.isnot(None))
        .order_by(LlmCallLog.provider)
    )).scalars().all()
    user_key_pairs = (
        await session.execute(
            select(LlmCallLog.user_id, LlmCallLog.ai_key_id)
            .where(
                LlmCallLog.user_id.isnot(None),
                LlmCallLog.ai_key_id.isnot(None),
            )
            .distinct()
        )
    ).all()
    routable_conditions = _routable_deployment_condition()
    id_active_model_names = set((await session.execute(
        select(distinct(LlmCallLog.model))
        .join(ModelDeployment, LlmCallLog.deployment_id == ModelDeployment.id)
        .join(Model, Model.id == ModelDeployment.model_id)
        .outerjoin(Credential, Credential.id == ModelDeployment.credential_id)
        .where(*routable_conditions)
    )).scalars().all())
    current_model_rows = (await session.execute(
        select(Model.model_id, Model.name, ModelDeployment.litellm_params)
        .join(ModelDeployment, ModelDeployment.model_id == Model.id)
        .outerjoin(Credential, Credential.id == ModelDeployment.credential_id)
        .where(*routable_conditions)
    )).all()
    current_model_names = _current_llm_model_names(current_model_rows)
    return {
        "user_ids": [u for u in actors if u],
        "ai_key_ids": [k for k in keys if k],
        "models": [
            {
                "value": m,
                "active": _is_active_llm_model_option(
                    m, id_active_model_names, current_model_names
                ),
            }
            for m in models
            if m
        ],
        "providers": [p for p in providers if p],
        "user_key_pairs": [
            (int(user_id), int(ai_key_id))
            for user_id, ai_key_id in user_key_pairs
        ],
    }


# ────────────── MCP ──────────────

def _apply_mcp_filters(
    stmt,
    start_time,
    end_time,
    user_id,
    ai_key_id,
    server_id,
    tool_name,
    status,
):
    if start_time is not None:
        stmt = stmt.where(McpCallLog.called_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(McpCallLog.called_at <= end_time)
    if user_id is not None:
        stmt = stmt.where(McpCallLog.user_id == user_id)
    if ai_key_id is not None:
        stmt = stmt.where(McpCallLog.ai_key_id == ai_key_id)
    if server_id is not None:
        stmt = stmt.where(McpCallLog.server_id == server_id)
    if tool_name:
        stmt = stmt.where(McpCallLog.tool_name == tool_name)
    if status:
        stmt = stmt.where(McpCallLog.status == status)
    return stmt


async def find_mcp_logs(
    session: AsyncSession,
    page: int,
    page_size: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    server_id: int | None = None,
    tool_name: str | None = None,
    status: str | None = None,
) -> list[McpCallLog]:
    stmt = select(McpCallLog).order_by(McpCallLog.called_at.desc())
    stmt = _apply_mcp_filters(
        stmt, start_time, end_time, user_id, ai_key_id, server_id, tool_name, status
    )
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_mcp_logs(
    session: AsyncSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    server_id: int | None = None,
    tool_name: str | None = None,
    status: str | None = None,
) -> int:
    stmt = select(func.count(McpCallLog.id))
    stmt = _apply_mcp_filters(
        stmt, start_time, end_time, user_id, ai_key_id, server_id, tool_name, status
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def find_mcp_log_by_id(session: AsyncSession, log_id: int) -> McpCallLog | None:
    result = await session.execute(select(McpCallLog).where(McpCallLog.id == log_id))
    return result.scalar_one_or_none()


async def mcp_log_filters(session: AsyncSession) -> dict:
    user_ids = (await session.execute(
        select(distinct(McpCallLog.user_id)).where(McpCallLog.user_id > 0)
    )).scalars().all()
    server_ids = (await session.execute(
        select(distinct(McpCallLog.server_id))
    )).scalars().all()
    ai_key_ids = (await session.execute(
        select(distinct(McpCallLog.ai_key_id)).where(McpCallLog.ai_key_id.isnot(None))
    )).scalars().all()
    tool_names = (await session.execute(
        select(distinct(McpCallLog.tool_name)).order_by(McpCallLog.tool_name)
    )).scalars().all()
    user_key_pairs = (
        await session.execute(
            select(McpCallLog.user_id, McpCallLog.ai_key_id)
            .where(
                McpCallLog.user_id.isnot(None),
                McpCallLog.ai_key_id.isnot(None),
            )
            .distinct()
        )
    ).all()
    return {
        "user_ids": [u for u in user_ids if u],
        "server_ids": [s for s in server_ids if s],
        "ai_key_ids": [k for k in ai_key_ids if k],
        "tool_names": [t for t in tool_names if t],
        "user_key_pairs": [
            (int(user_id), int(ai_key_id))
            for user_id, ai_key_id in user_key_pairs
        ],
    }


# ────────────── Skill ──────────────

def _apply_skill_filters(stmt, start_time, end_time, user_id, skill_id, action):
    if start_time is not None:
        stmt = stmt.where(SkillUsageLog.created_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(SkillUsageLog.created_at <= end_time)
    if user_id is not None:
        stmt = stmt.where(SkillUsageLog.user_id == user_id)
    if skill_id is not None:
        stmt = stmt.where(SkillUsageLog.skill_id == skill_id)
    if action:
        stmt = stmt.where(SkillUsageLog.action == action)
    return stmt


async def find_skill_logs(
    session: AsyncSession,
    page: int,
    page_size: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    skill_id: int | None = None,
    action: str | None = None,
) -> list[SkillUsageLog]:
    stmt = select(SkillUsageLog).order_by(SkillUsageLog.created_at.desc())
    stmt = _apply_skill_filters(stmt, start_time, end_time, user_id, skill_id, action)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_skill_logs(
    session: AsyncSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    skill_id: int | None = None,
    action: str | None = None,
) -> int:
    stmt = select(func.count(SkillUsageLog.id))
    stmt = _apply_skill_filters(stmt, start_time, end_time, user_id, skill_id, action)
    result = await session.execute(stmt)
    return result.scalar_one()


async def skill_log_filters(session: AsyncSession) -> dict:
    user_ids = (await session.execute(
        select(distinct(SkillUsageLog.user_id))
    )).scalars().all()
    skill_ids = (await session.execute(
        select(distinct(SkillUsageLog.skill_id))
    )).scalars().all()
    actions = (await session.execute(
        select(distinct(SkillUsageLog.action))
    )).scalars().all()
    return {
        "user_ids": [u for u in user_ids if u],
        "skill_ids": [s for s in skill_ids if s],
        "actions": [a for a in actions if a],
    }


# ────────────── Agent ──────────────

def _apply_agent_filters(stmt, start_time, end_time, user_id, agent_id, platform):
    if start_time is not None:
        stmt = stmt.where(AgentUsageLog.created_at >= start_time)
    if end_time is not None:
        stmt = stmt.where(AgentUsageLog.created_at <= end_time)
    if user_id is not None:
        stmt = stmt.where(AgentUsageLog.user_id == user_id)
    if agent_id is not None:
        stmt = stmt.where(AgentUsageLog.agent_id == agent_id)
    if platform:
        stmt = stmt.where(Agent.platform == platform)
    return stmt


async def find_agent_logs(
    session: AsyncSession,
    page: int,
    page_size: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    agent_id: int | None = None,
    platform: str | None = None,
) -> list[tuple[AgentUsageLog, Agent | None]]:
    stmt = (
        select(AgentUsageLog, Agent)
        .join(Agent, Agent.id == AgentUsageLog.agent_id, isouter=True)
        .order_by(AgentUsageLog.created_at.desc())
    )
    stmt = _apply_agent_filters(stmt, start_time, end_time, user_id, agent_id, platform)
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def count_agent_logs(
    session: AsyncSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    agent_id: int | None = None,
    platform: str | None = None,
) -> int:
    stmt = (
        select(func.count(AgentUsageLog.id))
        .join(Agent, Agent.id == AgentUsageLog.agent_id, isouter=True)
    )
    stmt = _apply_agent_filters(stmt, start_time, end_time, user_id, agent_id, platform)
    result = await session.execute(stmt)
    return result.scalar_one()


async def agent_log_filters(session: AsyncSession) -> dict:
    user_ids = (await session.execute(
        select(distinct(AgentUsageLog.user_id))
    )).scalars().all()
    agent_ids = (await session.execute(
        select(distinct(AgentUsageLog.agent_id))
    )).scalars().all()
    platforms = (await session.execute(
        select(distinct(Agent.platform)).order_by(Agent.platform)
    )).scalars().all()
    return {
        "user_ids": [u for u in user_ids if u],
        "agent_ids": [a for a in agent_ids if a],
        "platforms": [p for p in platforms if p],
    }


# ────────────── 关联资源批量加载（避免 N+1） ──────────────

async def load_users(session: AsyncSession, user_ids: list[int]) -> dict[int, dict]:
    """批量加载用户 + 部门信息。

    返回 {user_id: {username, display_name, department_name}}。
    """
    ids = list({i for i in user_ids if i})
    if not ids:
        return {}
    result = await session.execute(
        select(User, Department)
        .join(UserDepartment, UserDepartment.user_id == User.id, isouter=True)
        .join(
            Department,
            Department.id == UserDepartment.department_id,
            isouter=True,
        )
        .where(User.id.in_(ids))
    )
    out: dict[int, dict] = {}
    for user, dept in result.all():
        if user.id not in out:
            out[user.id] = {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "department_name": dept.name if dept else "",
            }
    return out


async def load_ai_keys(session: AsyncSession, key_ids: list[int]) -> dict[int, dict]:
    ids = list({i for i in key_ids if i})
    if not ids:
        return {}
    result = await session.execute(
        select(AiKey).where(AiKey.id.in_(ids))
    )
    return {
        k.id: {"id": k.id, "name": k.name, "key_token": _mask_key(k.litellm_key_id)}
        for k in result.scalars().all()
    }


def _mask_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "****"
    return key[:4] + "****" + key[-4:]


async def load_skills(session: AsyncSession, skill_ids: list[int]) -> dict[int, dict]:
    ids = list({i for i in skill_ids if i})
    if not ids:
        return {}
    result = await session.execute(select(Skill).where(Skill.id.in_(ids)))
    return {
        s.id: {"id": s.id, "name": s.name, "icon": s.icon, "version": s.version}
        for s in result.scalars().all()
    }


async def load_mcp_servers(
    session: AsyncSession, server_ids: list[int]
) -> dict[int, dict]:
    ids = list({i for i in server_ids if i})
    if not ids:
        return {}
    result = await session.execute(select(McpServer).where(McpServer.id.in_(ids)))
    return {
        s.id: {"id": s.id, "name": s.name, "server_name": s.server_name}
        for s in result.scalars().all()
    }


async def load_deployments(
    session: AsyncSession, deployment_ids: list[int]
) -> dict[int, dict]:
    ids = list({i for i in deployment_ids if i})
    if not ids:
        return {}
    result = await session.execute(
        select(ModelDeployment).where(ModelDeployment.id.in_(ids))
    )
    return {
        d.id: {
            "id": d.id,
            "deploy_name": d.deploy_name,
            "billing_type": d.billing_type,
            "cost_per_call": str(d.cost_per_call) if d.cost_per_call is not None else None,
            "model_info": d.model_info or {},
        }
        for d in result.scalars().all()
    }
