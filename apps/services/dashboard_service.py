"""Dashboard 数据聚合 Service。"""

import asyncio
from datetime import date, datetime, timedelta, timezone
import os
import subprocess

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repositories import dashboard_repo

from models.db import (
    AdminAuditLog,
    Agent,
    AiKey,
    CostSummaryDaily,
    Department,
    McpServer,
    Model,
    ModelDeployment,
    Project,
    ResourceApplication,
    Skill,
    User,
)


def _prev_period(start_date: date, end_date: date) -> tuple[date, date]:
    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    return prev_end - timedelta(days=days - 1), prev_end


async def get_dashboard(session: AsyncSession, start_date: date, end_date: date) -> dict:
    """聚合 Dashboard 所有板块数据。"""
    prev_start, prev_end = _prev_period(start_date, end_date)
    status = await _get_status(session, start_date, end_date, prev_start, prev_end)
    trend = await _get_request_trend(session, start_date, end_date)
    resources = await _get_resources(session)
    recent_activities = await _get_recent_activities(session)
    pending_approvals, pending_total = await _get_latest_pending_approvals(session)
    service_status = await _get_service_status(session)
    last_updated_at = await _get_last_updated_at(session)
    cost_leaderboard = await dashboard_repo.get_cost_leaderboard(
        session, start_date, end_date
    )

    status["pendingCount"] = pending_total
    status["pendingApprovals"] = pending_total
    status["pendingAlerts"] = 0

    return {
        "period": {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "label": _period_label(start_date, end_date),
        },
        "lastUpdatedAt": last_updated_at.isoformat() if last_updated_at else None,
        "lastUpdatedLabel": _time_ago(last_updated_at),
        "status": status,
        "requestTrend": trend,
        "hourlyTrend": trend,
        "resources": resources,
        "recentActivities": recent_activities,
        "pendingApprovalsList": pending_approvals,
        "pendingItems": pending_approvals,
        "serviceStatus": service_status,
        "costLeaderboard": cost_leaderboard,
    }


async def request_refresh() -> dict:
    """提交共享效能数据更新任务。"""
    from services import efficiency_service

    data = await efficiency_service.request_refresh("dashboard")
    return {
        "status": data.get("update_status"),
        "taskId": data.get("task_id"),
        "reason": data.get("reason", ""),
    }


def get_refresh_status(task_id: str) -> dict:
    from services import efficiency_service

    status = efficiency_service.get_refresh_status(task_id)
    return {"status": status["state"], "taskId": task_id, **status}


async def _get_status(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    prev_start: date,
    prev_end: date,
) -> dict:
    current = await _range_status(session, start_date, end_date)
    previous = await _range_status(session, prev_start, prev_end)
    token_stats = await dashboard_repo.get_token_stats(session, start_date, end_date)
    cost_change_percent = _calc_change(current["internalCost"], previous["internalCost"])

    return {
        "activeUsers": current["activeUsers"],
        "activeUsersChange": current["activeUsers"] - previous["activeUsers"],
        "todayRequests": current["totalRequests"],
        "totalRequests": current["totalRequests"],
        "llmRequests": current["llmRequests"],
        "mcpRequests": current["mcpRequests"],
        "todayCost": current["internalCost"],
        "internalCost": current["internalCost"],
        "externalCost": current["externalCost"],
        "costDiff": round(current["internalCost"] - current["externalCost"], 2),
        "costChangePercent": cost_change_percent,
        "totalTokens": token_stats["total"],
        "inputTokens": token_stats["input"],
        "outputTokens": token_stats["output"],
        "cacheReadTokens": token_stats["cache_read"],
        "cacheCreationTokens": token_stats["cache_creation"],
        "pendingCount": 0,
        "pendingApprovals": 0,
        "pendingAlerts": 0,
    }


async def _range_status(session: AsyncSession, start_date: date, end_date: date) -> dict:
    return await dashboard_repo.get_range_status(session, start_date, end_date)

async def _get_request_trend(session: AsyncSession, start_date: date, end_date: date) -> list[dict]:
    return await dashboard_repo.get_request_trend(session, start_date, end_date)

async def _get_latest_pending_approvals(session: AsyncSession) -> tuple[list[dict], int]:
    total_result = await session.execute(
        select(func.count(ResourceApplication.id)).where(ResourceApplication.status == "pending")
    )
    total = int(total_result.scalar() or 0)
    result = await session.execute(
        select(ResourceApplication)
        .where(ResourceApplication.status == "pending")
        .order_by(ResourceApplication.created_at.desc())
        .limit(5)
    )
    rows = []
    for app in result.scalars().all():
        applicant = app.user.display_name or app.user.username if app.user else "未知用户"
        rows.append({
            "id": app.id,
            "type": "approval",
            "applicant": applicant,
            "resourceType": app.resource_type,
            "resourceTypeLabel": _resource_type_label(app.resource_type),
            "resourceName": _build_resource_title(app.resource_type, app.reason),
            "reason": app.reason or "",
            "createdAt": app.created_at.isoformat() if app.created_at else None,
            "timeAgo": _time_ago(app.created_at),
            "linkUrl": f"/resource-approval?status=pending&keyword={app.id}",
        })
    return rows, total


async def _get_service_status(session: AsyncSession) -> list[dict]:
    mcp_total = await _count(session, McpServer, McpServer.is_published.is_(True))
    mcp_healthy = await _count(
        session,
        McpServer,
        McpServer.is_published.is_(True),
        McpServer.status.in_(["healthy", "success", "online", "ok"]),
    )
    model_health = await _get_model_health_summary(session)
    model_total = model_health["total"]
    model_healthy = model_health["healthy"]
    latest = await _get_last_updated_at(session)
    update_minutes = _minutes_since(latest)
    update_healthy = latest is not None and update_minutes <= 30

    docker_status = await _get_docker_status()
    return [
        {
            "key": "mcp",
            "label": "MCP上游健康",
            "healthy": mcp_healthy,
            "total": mcp_total,
            "state": _health_state(mcp_healthy, mcp_total),
            "description": f"可用 {mcp_healthy} / 共 {mcp_total}",
        },
        {
            "key": "model",
            "label": "模型健康",
            "healthy": model_healthy,
            "total": model_total,
            "state": _health_state(model_healthy, model_total),
            "description": f"启用部署 {model_healthy} / 共 {model_total}",
        },
        {
            "key": "docker",
            "label": "Docker环境",
            "healthy": docker_status["healthy"],
            "total": docker_status["total"],
            "state": docker_status["state"],
            "description": docker_status["description"],
        },
        {
            "key": "efficiency",
            "label": "效能数据更新",
            "healthy": 1 if update_healthy else 0,
            "total": 1,
            "state": "healthy" if update_healthy else "warning",
            "description": f"最后更新时间：{_time_ago(latest)}",
        },
    ]


async def _get_model_health_summary(session: AsyncSession) -> dict:
    return await dashboard_repo.get_model_health_summary(session)

async def _get_docker_status() -> dict:
    checks = [
        os.path.exists("/.dockerenv"),
        os.path.exists("/var/run/docker.sock"),
    ]
    total = len(checks)
    healthy = sum(1 for item in checks if item)
    if checks[1]:
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            total += 1
            if proc.stdout.strip():
                healthy += 1
        except Exception:
            total += 1
    return {
        "healthy": healthy,
        "total": total,
        "state": _health_state(healthy, total),
        "description": f"检测通过 {healthy} / 共 {total}",
    }


async def _get_last_updated_at(session: AsyncSession) -> datetime | None:
    return await dashboard_repo.get_last_updated_at(session)

async def _get_resources(session: AsyncSession) -> list[dict]:
    models_total = await _count(session, Model)
    models_published = await _count(session, Model, Model.is_published.is_(True))
    mcp_total = await _count(session, McpServer)
    mcp_published = await _count(session, McpServer, McpServer.is_published.is_(True))
    skills_total = await _count(session, Skill)
    skills_published = await _count(session, Skill, Skill.is_published.is_(True))
    agents_total = await _count(session, Agent)
    agents_published = await _count(session, Agent, Agent.is_published.is_(True))
    ai_keys_total = await _count(session, AiKey)
    ai_keys_active = await _count(session, AiKey, AiKey.is_active.is_(True))
    users_total = await _count(session, User)
    users_active = await _count(session, User, User.is_active.is_(True))
    departments_total = await _count(session, Department)
    projects_total = await _count(session, Project)

    return [
        {"name": "模型", "icon": "model", "total": models_total, "active": models_published, "activeLabel": "已发布", "linkPath": "/models"},
        {"name": "MCP", "icon": "mcp", "total": mcp_total, "active": mcp_published, "activeLabel": "已发布", "linkPath": "/mcp"},
        {"name": "Skill", "icon": "skill", "total": skills_total, "active": skills_published, "activeLabel": "已发布", "linkPath": "/skills"},
        {"name": "智能体", "icon": "agent", "total": agents_total, "active": agents_published, "activeLabel": "已发布", "linkPath": "/agents"},
        {"name": "AI Key", "icon": "ai_key", "total": ai_keys_total, "active": ai_keys_active, "activeLabel": "启用", "linkPath": "/ai-keys"},
        {"name": "用户", "icon": "user", "total": users_total, "active": users_active, "activeLabel": "启用", "linkPath": "/users"},
        {"name": "部门", "icon": "department", "total": departments_total, "active": None, "activeLabel": "", "linkPath": "/departments"},
        {"name": "项目", "icon": "project", "total": projects_total, "active": None, "activeLabel": "", "linkPath": "/projects"},
    ]


async def _get_recent_activities(session: AsyncSession) -> list[dict]:
    result = await session.execute(select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(5))
    return [
        {"actor": log.username or "系统", "action": log.action or log.path, "timeAgo": _time_ago(log.created_at)}
        for log in result.scalars().all()
    ]


async def _count(session: AsyncSession, model: type, *filters) -> int:
    stmt = select(func.count()).select_from(model)
    for f in filters:
        stmt = stmt.where(f)
    result = await session.execute(stmt)
    return int(result.scalar() or 0)


def _calc_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0
    return round((current - previous) / previous * 100, 1)


def _minutes_since(dt: datetime | None) -> int:
    if not dt:
        return 10**9
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(int((now - dt).total_seconds() // 60), 0)


def _time_ago(dt: datetime | None) -> str:
    if not dt:
        return "暂无更新"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = max(int((now - dt).total_seconds()), 0)
    if seconds < 60:
        return "刚刚"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}分钟前"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")


def _health_state(healthy: int, total: int) -> str:
    if total == 0:
        return "empty"
    if healthy == total:
        return "healthy"
    if healthy == 0:
        return "danger"
    return "warning"


def _resource_type_label(resource_type: str) -> str:
    labels = {"model": "模型", "mcp": "MCP", "skill": "Skill", "agent": "智能体"}
    return labels.get(resource_type, resource_type)


def _build_resource_title(resource_type: str, reason: str) -> str:
    if reason:
        return reason[:30]
    return _resource_type_label(resource_type)


def _period_label(start_date: date, end_date: date) -> str:
    if start_date == end_date:
        return start_date.isoformat()
    return f"{start_date.isoformat()} 至 {end_date.isoformat()}"
