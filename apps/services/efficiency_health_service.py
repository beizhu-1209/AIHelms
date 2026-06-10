import asyncio
import os
import subprocess
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import efficiency_health_repo


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


def _ratio_state(healthy: int, total: int) -> str:
    if total == 0:
        return "unknown"
    if healthy == total:
        return "healthy"
    if healthy == 0:
        return "danger"
    return "warning"


def _iso_or_none(value) -> str | None:
    return value.isoformat() if value else None


async def get_ai_health(session: AsyncSession) -> dict:
    mcp_rows = [
        {
            "id": r[0],
            "name": r[1],
            "server_name": r[2],
            "status": r[3] or "unknown",
            "last_check": _iso_or_none(r[4]),
            "error": r[5] or "",
            "is_published": bool(r[7]),
            "tool_count": int(r[8] or 0),
        }
        for r in await efficiency_health_repo.get_mcp_health_rows(session)
    ]
    mcp_total = len(mcp_rows)
    mcp_healthy = sum(1 for row in mcp_rows if row["status"] in {"healthy", "success", "online", "ok"})

    model_rows = []
    for r in await efficiency_health_repo.get_model_health_rows(session):
        active_deployments = int(r[5] or 0)
        total_deployments = int(r[6] or 0)
        if active_deployments > 0:
            status = "healthy"
        elif total_deployments > 0:
            status = "warning"
        else:
            status = "danger"
        model_rows.append(
            {
                "id": r[0],
                "name": r[1],
                "model_id": r[2],
                "category": r[3],
                "is_published": bool(r[4]),
                "active_deployments": active_deployments,
                "total_deployments": total_deployments,
                "status": status,
                "last_update": _iso_or_none(r[7]),
            }
        )
    model_total = len(model_rows)
    model_healthy = sum(1 for row in model_rows if row["status"] == "healthy")

    latest = await efficiency_health_repo.get_data_update_row(session)
    latest_at = latest[0] if latest else None
    latest_date = latest[1] if latest else None
    now = datetime.now(timezone.utc)
    if latest_at and latest_at.tzinfo is None:
        now_for_diff = now.replace(tzinfo=None)
    else:
        now_for_diff = now
    update_minutes = int((now_for_diff - latest_at).total_seconds() // 60) if latest_at else None
    data_state = "healthy" if update_minutes is not None and update_minutes <= 60 else "warning"

    docker_items = []
    in_container = os.path.exists("/.dockerenv")
    docker_socket = os.path.exists("/var/run/docker.sock")
    docker_items.append({"name": "容器运行环境", "status": "healthy" if in_container else "unknown", "value": "已检测" if in_container else "未检测"})
    docker_items.append({"name": "Docker Socket", "status": "healthy" if docker_socket else "unknown", "value": "可访问" if docker_socket else "未挂载"})
    docker_version = ""
    if docker_socket:
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            docker_version = proc.stdout.strip()
            docker_items.append({"name": "Docker Engine", "status": "healthy" if docker_version else "warning", "value": docker_version or "未返回版本"})
        except Exception:
            docker_items.append({"name": "Docker Engine", "status": "warning", "value": "未返回版本"})
    docker_healthy = sum(1 for item in docker_items if item["status"] == "healthy")
    docker_state = _ratio_state(docker_healthy, len(docker_items))

    cards = [
        {
            "key": "mcp",
            "label": "MCP上游健康",
            "healthy": mcp_healthy,
            "total": mcp_total,
            "state": _ratio_state(mcp_healthy, mcp_total),
            "description": f"可用 {mcp_healthy} / 共 {mcp_total}",
        },
        {
            "key": "model",
            "label": "模型健康",
            "healthy": model_healthy,
            "total": model_total,
            "state": _ratio_state(model_healthy, model_total),
            "description": f"有启用部署 {model_healthy} / 共 {model_total}",
        },
        {
            "key": "docker",
            "label": "Docker环境",
            "healthy": docker_healthy,
            "total": len(docker_items),
            "state": docker_state,
            "description": "运行环境检测",
        },
        {
            "key": "data_update",
            "label": "效能数据更新",
            "healthy": 1 if data_state == "healthy" else 0,
            "total": 1,
            "state": data_state,
            "description": "最近更新时间正常" if data_state == "healthy" else "最近更新时间超过1小时或暂无数据",
        },
    ]

    return {
        "cards": cards,
        "mcp_servers": mcp_rows,
        "models": model_rows,
        "docker": docker_items,
        "data_update": {
            "last_updated_at": _iso_or_none(latest_at),
            "latest_summary_date": str(latest_date.date() if hasattr(latest_date, "date") else latest_date) if latest_date else None,
            "minutes_since_update": update_minutes,
            "state": data_state,
        },
    }


