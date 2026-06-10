"""使用日志查询 Service。

为 4 个 Tab 提供分页列表 + 详情 + 筛选下拉数据。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from exceptions import NotFoundError
from models.db import Agent, AgentUsageLog, LlmCallLog, McpCallLog, SkillUsageLog
from repositories import usage_log_repo

# ────────────── LLM ──────────────

async def list_llm_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    model: str | None = None,
    models: list[str] | None = None,
    provider: str | None = None,
    status: str | None = None,
) -> dict:
    total = await usage_log_repo.count_llm_logs(
        session, start_time, end_time, user_id, ai_key_id, model, models, provider, status
    )
    logs = await usage_log_repo.find_llm_logs(
        session,
        page,
        page_size,
        start_time,
        end_time,
        user_id,
        ai_key_id,
        model,
        models,
        provider,
        status,
    )
    users = await usage_log_repo.load_users(session, [log.user_id for log in logs])
    keys = await usage_log_repo.load_ai_keys(session, [log.ai_key_id for log in logs])
    return {
        "items": [_serialize_llm(log, users, keys) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_llm_log(session: AsyncSession, log_id: int) -> dict:
    log = await usage_log_repo.find_llm_log_by_id(session, log_id)
    if not log:
        raise NotFoundError("llm_log", log_id)
    users = await usage_log_repo.load_users(session, [log.user_id])
    keys = await usage_log_repo.load_ai_keys(session, [log.ai_key_id])
    deployments = await usage_log_repo.load_deployments(session, [log.deployment_id])
    item = _serialize_llm(log, users, keys)
    item["deployment"] = (
        deployments.get(log.deployment_id) if log.deployment_id else None
    )
    item["metadata"] = log.metadata_
    item["messages"] = log.messages
    item["response"] = log.response
    return item


async def llm_filters(session: AsyncSession) -> dict:
    raw = await usage_log_repo.llm_log_filters(session)
    users = await usage_log_repo.load_users(session, raw["user_ids"])
    keys = await usage_log_repo.load_ai_keys(session, raw["ai_key_ids"])
    return {
        "users": [users[u] for u in raw["user_ids"] if u in users],
        "ai_keys": [keys[k] for k in raw["ai_key_ids"] if k in keys],
        "models": raw["models"],
        "providers": raw["providers"],
    }


_LOCAL_TZ = ZoneInfo(settings.timezone)


def _fmt_time(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def _serialize_llm(log: LlmCallLog, users: dict, keys: dict) -> dict:
    user = users.get(log.user_id) if log.user_id else None
    key = keys.get(log.ai_key_id) if log.ai_key_id else None
    return {
        "id": log.id,
        "request_id": log.request_id,
        "user": user,
        "ai_key": key,
        "model": log.model,
        "provider": log.provider,
        "call_type": log.call_type,
        "status": log.status,
        "prompt_tokens": log.prompt_tokens,
        "completion_tokens": log.completion_tokens,
        "total_tokens": log.total_tokens,
        "cache_read_tokens": log.cache_read_tokens,
        "cache_creation_tokens": log.cache_creation_tokens,
        "external_cost": str(log.external_cost),
        "internal_cost": str(log.internal_cost),
        "duration_ms": log.duration_ms,
        "ttft_ms": log.ttft_ms,
        "started_at": _fmt_time(log.started_at),
        "ended_at": _fmt_time(log.ended_at),
        "session_id": log.session_id,
        "error_message": log.error_message,
    }


# ────────────── MCP ──────────────

async def list_mcp_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    ai_key_id: int | None = None,
    server_id: int | None = None,
    tool_name: str | None = None,
    status: str | None = None,
) -> dict:
    total = await usage_log_repo.count_mcp_logs(
        session, start_time, end_time, user_id, ai_key_id, server_id, tool_name, status
    )
    logs = await usage_log_repo.find_mcp_logs(
        session,
        page,
        page_size,
        start_time,
        end_time,
        user_id,
        ai_key_id,
        server_id,
        tool_name,
        status,
    )
    users = await usage_log_repo.load_users(session, [log.user_id for log in logs])
    keys = await usage_log_repo.load_ai_keys(session, [log.ai_key_id for log in logs])
    servers = await usage_log_repo.load_mcp_servers(
        session, [log.server_id for log in logs]
    )
    return {
        "items": [_serialize_mcp(log, users, keys, servers) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_mcp_log(session: AsyncSession, log_id: int) -> dict:
    log = await usage_log_repo.find_mcp_log_by_id(session, log_id)
    if not log:
        raise NotFoundError("mcp_log", log_id)
    users = await usage_log_repo.load_users(session, [log.user_id])
    keys = await usage_log_repo.load_ai_keys(session, [log.ai_key_id])
    servers = await usage_log_repo.load_mcp_servers(session, [log.server_id])
    item = _serialize_mcp(log, users, keys, servers)
    item["request_args"] = log.request_args
    item["response_full"] = log.response_full
    return item


async def mcp_filters(session: AsyncSession) -> dict:
    raw = await usage_log_repo.mcp_log_filters(session)
    users = await usage_log_repo.load_users(session, raw["user_ids"])
    servers = await usage_log_repo.load_mcp_servers(session, raw["server_ids"])
    keys = await usage_log_repo.load_ai_keys(session, raw["ai_key_ids"])
    return {
        "users": [users[u] for u in raw["user_ids"] if u in users],
        "servers": [servers[s] for s in raw["server_ids"] if s in servers],
        "ai_keys": [keys[k] for k in raw["ai_key_ids"] if k in keys],
        "tool_names": raw["tool_names"],
    }


def _serialize_mcp(log: McpCallLog, users: dict, keys: dict, servers: dict) -> dict:
    user = users.get(log.user_id) if log.user_id else None
    key = keys.get(log.ai_key_id) if log.ai_key_id else None
    server = servers.get(log.server_id) if log.server_id else None
    return {
        "id": log.id,
        "user": user,
        "ai_key": key,
        "server": server,
        "tool_name": log.tool_name,
        "namespaced_tool_name": log.namespaced_tool_name,
        "status": log.status,
        "duration_ms": log.duration_ms,
        "internal_cost": str(log.internal_cost),
        "external_cost": str(log.external_cost),
        "response_summary": log.response_summary,
        "error_message": log.error_message,
        "called_at": _fmt_time(log.called_at),
    }


# ────────────── Skill ──────────────

async def list_skill_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    skill_id: int | None = None,
    action: str | None = None,
) -> dict:
    total = await usage_log_repo.count_skill_logs(
        session, start_time, end_time, user_id, skill_id, action
    )
    logs = await usage_log_repo.find_skill_logs(
        session, page, page_size, start_time, end_time, user_id, skill_id, action
    )
    users = await usage_log_repo.load_users(session, [log.user_id for log in logs])
    skills = await usage_log_repo.load_skills(session, [log.skill_id for log in logs])
    return {
        "items": [_serialize_skill(log, users, skills) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def skill_filters(session: AsyncSession) -> dict:
    raw = await usage_log_repo.skill_log_filters(session)
    users = await usage_log_repo.load_users(session, raw["user_ids"])
    skills = await usage_log_repo.load_skills(session, raw["skill_ids"])
    return {
        "users": [users[u] for u in raw["user_ids"] if u in users],
        "skills": [skills[s] for s in raw["skill_ids"] if s in skills],
        "actions": raw["actions"],
    }


def _serialize_skill(log: SkillUsageLog, users: dict, skills: dict) -> dict:
    return {
        "id": log.id,
        "user": users.get(log.user_id),
        "skill": skills.get(log.skill_id),
        "action": log.action,
        "created_at": _fmt_time(log.created_at),
    }


# ────────────── Agent ──────────────

async def list_agent_logs(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user_id: int | None = None,
    agent_id: int | None = None,
    platform: str | None = None,
) -> dict:
    total = await usage_log_repo.count_agent_logs(
        session, start_time, end_time, user_id, agent_id, platform
    )
    pairs = await usage_log_repo.find_agent_logs(
        session, page, page_size, start_time, end_time, user_id, agent_id, platform
    )
    users = await usage_log_repo.load_users(
        session, [log.user_id for log, _ in pairs]
    )
    return {
        "items": [_serialize_agent(log, agent, users) for log, agent in pairs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def agent_filters(session: AsyncSession) -> dict:
    raw = await usage_log_repo.agent_log_filters(session)
    users = await usage_log_repo.load_users(session, raw["user_ids"])
    # 加载 agent
    from sqlalchemy import select
    agents = (await session.execute(
        select(Agent).where(Agent.id.in_(raw["agent_ids"]))
    )).scalars().all() if raw["agent_ids"] else []
    return {
        "users": [users[u] for u in raw["user_ids"] if u in users],
        "agents": [
            {"id": a.id, "name": a.name, "icon": a.icon, "platform": a.platform}
            for a in agents
        ],
        "platforms": raw["platforms"],
    }


def _serialize_agent(
    log: AgentUsageLog, agent: Agent | None, users: dict
) -> dict:
    return {
        "id": log.id,
        "user": users.get(log.user_id),
        "agent": (
            {
                "id": agent.id,
                "name": agent.name,
                "icon": agent.icon,
                "platform": agent.platform,
            }
            if agent
            else None
        ),
        "platform": agent.platform if agent else None,
        "session_id": log.session_id,
        "created_at": _fmt_time(log.created_at),
    }
