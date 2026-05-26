"""Dashboard 数据聚合 Service。"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.db import (
    AdminAuditLog,
    Agent,
    AiKey,
    CostSummaryDaily,
    Department,
    McpServer,
    Model,
    Project,
    ResourceApplication,
    Skill,
    User,
)


async def get_dashboard(session: AsyncSession) -> dict:
    """聚合 Dashboard 所有板块数据。"""
    today = date.today()
    yesterday = today - timedelta(days=1)

    pending_items = await _get_pending_items(session)
    status = await _get_status(session, today, yesterday, pending_items)
    hourly_trend = await _get_hourly_trend(session, today)
    resources = await _get_resources(session)
    recent_activities = await _get_recent_activities(session)

    return {
        "status": status,
        "pendingItems": pending_items,
        "hourlyTrend": hourly_trend,
        "resources": resources,
        "recentActivities": recent_activities,
    }


async def _get_status(
    session: AsyncSession,
    today: date,
    yesterday: date,
    pending_items: list[dict],
) -> dict:
    """今日核心指标 + 昨日对比值。"""
    today_result = await session.execute(
        select(
            func.count(func.distinct(CostSummaryDaily.user_id)).label("active_users"),
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0).label("requests"),
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0).label("cost"),
        ).where(
            CostSummaryDaily.summary_date == today,
            CostSummaryDaily.user_id.isnot(None),
        )
    )
    today_row = today_result.one()

    yesterday_result = await session.execute(
        select(
            func.count(func.distinct(CostSummaryDaily.user_id)).label("active_users"),
            func.coalesce(func.sum(CostSummaryDaily.internal_cost), 0).label("cost"),
        ).where(
            CostSummaryDaily.summary_date == yesterday,
            CostSummaryDaily.user_id.isnot(None),
        )
    )
    yesterday_row = yesterday_result.one()

    llm_result = await session.execute(
        select(
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0),
        ).where(
            CostSummaryDaily.summary_date == today,
            CostSummaryDaily.cost_type == "llm",
        )
    )
    llm_requests = int(llm_result.scalar() or 0)

    mcp_result = await session.execute(
        select(
            func.coalesce(func.sum(CostSummaryDaily.total_requests), 0),
        ).where(
            CostSummaryDaily.summary_date == today,
            CostSummaryDaily.cost_type == "mcp",
        )
    )
    mcp_requests = int(mcp_result.scalar() or 0)

    cost_today = float(today_row.cost)
    cost_yesterday = float(yesterday_row.cost)
    cost_change_percent = (
        round((cost_today - cost_yesterday) / cost_yesterday * 100)
        if cost_yesterday > 0
        else 0
    )

    pending_approvals = sum(1 for i in pending_items if i["type"] == "approval")
    pending_alerts = sum(1 for i in pending_items if i["type"] == "budget_alert")

    return {
        "activeUsers": int(today_row.active_users),
        "activeUsersChange": int(today_row.active_users) - int(yesterday_row.active_users),
        "todayRequests": int(today_row.requests),
        "llmRequests": llm_requests,
        "mcpRequests": mcp_requests,
        "todayCost": cost_today,
        "costChangePercent": cost_change_percent,
        "pendingCount": len(pending_items),
        "pendingApprovals": pending_approvals,
        "pendingAlerts": pending_alerts,
    }


async def _get_pending_items(session: AsyncSession) -> list[dict]:
    """待处理事项：待审批 + 预算预警。"""
    items: list[dict] = []

    applications = await session.execute(
        select(ResourceApplication)
        .where(ResourceApplication.status == "pending")
        .order_by(ResourceApplication.created_at.desc())
        .limit(20)
    )
    for app in applications.scalars().all():
        user_display = (
            app.user.display_name or app.user.username if app.user else "未知用户"
        )
        resource_name = _build_resource_title(app.resource_type, app.reason)
        type_label = _resource_type_label(app.resource_type)
        description = f"{user_display} 申请使用「{resource_name}」{type_label}"
        items.append({
            "type": "approval",
            "description": description,
            "timeAgo": _time_ago(app.created_at),
            "linkUrl": "/resource-approval",
        })

    budget_alerts = await session.execute(
        select(AiKey).where(
            AiKey.budget_limit.isnot(None),
            AiKey.budget_limit > 0,
            AiKey.is_active.is_(True),
            (AiKey.budget_used / AiKey.budget_limit) > Decimal("0.9"),
        ).limit(10)
    )
    for key in budget_alerts.scalars().all():
        usage_rate = (
            int(key.budget_used / key.budget_limit * 100) if key.budget_limit else 0
        )
        description = f"「{key.name}」预算执行率 {usage_rate}%"
        items.append({
            "type": "budget_alert",
            "description": description,
            "timeAgo": _time_ago(key.updated_at),
            "linkUrl": "/ai-identity",
        })

    return items


async def _get_hourly_trend(session: AsyncSession, today: date) -> list[dict]:
    """今日逐小时调用量（LLM + MCP 合并）。"""
    llm_sql = text("""
        SELECT EXTRACT(HOUR FROM started_at)::int AS hour,
               COUNT(*) AS cnt
        FROM aihelms.llm_call_logs
        WHERE started_at::date = :today
        GROUP BY 1
    """)
    mcp_sql = text("""
        SELECT EXTRACT(HOUR FROM called_at)::int AS hour,
               COUNT(*) AS cnt
        FROM aihelms.mcp_call_logs
        WHERE called_at::date = :today
        GROUP BY 1
    """)

    llm_result = await session.execute(llm_sql, {"today": today})
    mcp_result = await session.execute(mcp_sql, {"today": today})

    hourly: dict[int, int] = {h: 0 for h in range(24)}
    for row in llm_result.fetchall():
        hourly[int(row[0])] += int(row[1])
    for row in mcp_result.fetchall():
        hourly[int(row[0])] += int(row[1])

    return [{"hour": h, "requests": c} for h, c in sorted(hourly.items())]


async def _get_resources(session: AsyncSession) -> list[dict]:
    """平台资源数量汇总，返回前端期望的数组格式。"""
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
        {"name": "AI Key", "icon": "ai_key", "total": ai_keys_total, "active": ai_keys_active, "activeLabel": "启用", "linkPath": "/ai-identity"},
        {"name": "用户", "icon": "user", "total": users_total, "active": users_active, "activeLabel": "活跃", "linkPath": "/users"},
        {"name": "部门", "icon": "department", "total": departments_total, "active": None, "activeLabel": "", "linkPath": "/departments"},
        {"name": "项目", "icon": "project", "total": projects_total, "active": None, "activeLabel": "", "linkPath": "/projects"},
    ]


async def _get_recent_activities(session: AsyncSession) -> list[dict]:
    """最新 5 条管理员操作日志。"""
    result = await session.execute(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(5)
    )
    logs = result.scalars().all()
    return [
        {
            "actor": log.username or "系统",
            "action": log.action or log.path,
            "timeAgo": _time_ago(log.created_at),
        }
        for log in logs
    ]


async def _count(session: AsyncSession, model: type, *filters) -> int:
    """通用计数辅助。"""
    stmt = select(func.count()).select_from(model)
    for f in filters:
        stmt = stmt.where(f)
    result = await session.execute(stmt)
    return result.scalar() or 0


def _time_ago(dt: datetime | None) -> str:
    """将时间转为相对描述（如 '5分钟前'）。"""
    if not dt:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "刚刚"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}分钟前"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}小时前"
    days = hours // 24
    if days < 30:
        return f"{days}天前"
    return dt.strftime("%m-%d")


def _resource_type_label(resource_type: str) -> str:
    """资源类型中文标签。"""
    labels = {
        "model": "模型",
        "mcp": "MCP",
        "skill": "Skill",
        "agent": "智能体",
    }
    return labels.get(resource_type, resource_type)


def _build_resource_title(resource_type: str, reason: str) -> str:
    """从申请信息中提取资源名称。"""
    if reason:
        return reason[:20]
    return _resource_type_label(resource_type)
