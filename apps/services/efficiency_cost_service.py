"""Efficiency cost service."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import efficiency_repo


def _calc_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _prev_period(start_date: date, end_date: date) -> tuple[date, date]:
    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    return prev_end - timedelta(days=days - 1), prev_end


async def get_cost(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    cost_type: str = "all",
    department_id: int | None = None,
    dimension: str = "department",
    project_id: int | None = None,
) -> dict:
    days = (end_date - start_date).days + 1
    prev_start, prev_end = _prev_period(start_date, end_date)
    cost_filters = None if cost_type == "all" else cost_type

    trend_raw = await efficiency_repo.get_cost_trend(
        session, start_date, end_date, cost_filters, department_id, project_id
    )
    prev_trend_raw = await efficiency_repo.get_cost_trend(
        session, prev_start, prev_end, cost_filters, department_id, project_id
    )
    total_cost = sum(r["internal_cost"] for r in trend_raw)
    external_cost = sum(r["external_cost"] for r in trend_raw)
    prev_total = sum(r["internal_cost"] for r in prev_trend_raw)

    date_map: dict[str, dict] = {}
    for i in range(max(days, 0)):
        d = (start_date + timedelta(days=i)).isoformat()
        date_map[d] = {
            "date": d,
            "llm_cost": 0,
            "mcp_cost": 0,
            "llm_external_cost": 0,
            "mcp_external_cost": 0,
            "is_anomaly": False,
        }
    for r in trend_raw:
        d = r["date"]
        if d not in date_map:
            date_map[d] = {
                "date": d,
                "llm_cost": 0,
                "mcp_cost": 0,
                "llm_external_cost": 0,
                "mcp_external_cost": 0,
                "is_anomaly": False,
            }
        if r["cost_type"] == "llm":
            date_map[d]["llm_cost"] = r["internal_cost"]
            date_map[d]["llm_external_cost"] = r["external_cost"]
        elif r["cost_type"] == "mcp":
            date_map[d]["mcp_cost"] = r["internal_cost"]
            date_map[d]["mcp_external_cost"] = r["external_cost"]

    by_type = await efficiency_repo.get_cost_by_type(
        session, start_date, end_date, department_id, cost_filters, project_id
    )
    by_scope = await efficiency_repo.get_cost_by_dimension(
        session, start_date, end_date, dimension, cost_filters, department_id, project_id
    )
    raw_pc = await efficiency_repo.get_per_capita_cost_by_dimension(
        session, start_date, end_date, dimension, cost_filters, department_id, project_id
    )

    return {
        "kpi": {
            "total_cost": round(total_cost, 4),
            "external_cost": round(external_cost, 4),
            "cost_diff": round(total_cost - external_cost, 4),
            "daily_avg_cost": round(total_cost / days, 4) if days > 0 else 0,
            "cost_change": _calc_change(total_cost, prev_total),
        },
        "trend": sorted(date_map.values(), key=lambda x: x["date"]),
        "composition": {"by_resource_type": by_type, "by_scope": by_scope},
        "per_capita": [
            {"name": i["name"], "per_capita_cost": i["value"]} for i in raw_pc
        ],
    }


async def get_cost_detail(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    tab: str = "department",
    cost_type: str = "all",
    department_id: int | None = None,
    dimension: str = "department",
    project_id: int | None = None,
) -> dict:
    ct = None if cost_type == "all" else cost_type
    if tab == "model":
        raw = await efficiency_repo.get_cost_detail_by_model(
            session, start_date, end_date, ct, department_id, project_id
        )
        grouped: dict[str, dict] = {}
        for item in raw:
            key = item["platform_model_key"]
            row = grouped.setdefault(
                key,
                {
                    "model": item["platform_model_name"],
                    "model_id": item["platform_model_id"],
                    "requests": 0,
                    "tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cost": 0.0,
                    "internal_cost": 0.0,
                    "external_cost": 0.0,
                    "cost_diff": 0.0,
                    "ratio": 0.0,
                    "avg_cost": 0.0,
                    "credentials": [],
                },
            )
            tokens = item["input_tokens"] + item["output_tokens"]
            row["requests"] += item["requests"]
            row["tokens"] += tokens
            row["cache_read_tokens"] += item["cache_read_tokens"]
            row["cache_creation_tokens"] += item["cache_creation_tokens"]
            row["cost"] += item["internal_cost"]
            row["internal_cost"] += item["internal_cost"]
            row["external_cost"] += item["external_cost"]
            row["credentials"].append(
                {
                    "credential_id": item["credential_id"],
                    "credential_name": item["credential_name"],
                    "provider_name": item["provider_name"],
                    "provider_type": item["provider_type"],
                    "deployment_id": item["deployment_id"],
                    "deployment_name": item["deployment_name"],
                    "route_model": item["route_model"],
                    "requests": item["requests"],
                    "tokens": tokens,
                    "cache_read_tokens": item["cache_read_tokens"],
                    "cache_creation_tokens": item["cache_creation_tokens"],
                    "internal_cost": item["internal_cost"],
                    "external_cost": item["external_cost"],
                    "cost_diff": round(item["internal_cost"] - item["external_cost"], 4),
                    "avg_cost": (
                        round(item["internal_cost"] / item["requests"], 4)
                        if item["requests"] > 0
                        else 0
                    ),
                }
            )
        items = list(grouped.values())
        total_cost = sum(item["internal_cost"] for item in items)
        for item in items:
            item["internal_cost"] = round(item["internal_cost"], 6)
            item["external_cost"] = round(item["external_cost"], 6)
            item["cost"] = item["internal_cost"]
            item["cost_diff"] = round(item["internal_cost"] - item["external_cost"], 4)
            item["ratio"] = round(item["internal_cost"] / total_cost, 4) if total_cost > 0 else 0
            item["avg_cost"] = (
                round(item["internal_cost"] / item["requests"], 4)
                if item["requests"] > 0
                else 0
            )
            item["credentials"].sort(key=lambda c: c["internal_cost"], reverse=True)
        items.sort(key=lambda item: item["internal_cost"], reverse=True)
        return {"model": items}
    if tab == "mcp":
        raw = await efficiency_repo.get_cost_detail_by_mcp(
            session, start_date, end_date, ct, department_id, project_id
        )
        grouped: dict[str, dict] = {}
        for item in raw:
            key = item["server_key"]
            row = grouped.setdefault(
                key,
                {
                    "server": item["server_name"],
                    "server_id": item["server_id"],
                    "server_code": item["server_code"],
                    "requests": 0,
                    "tool_count": 0,
                    "cost": 0.0,
                    "internal_cost": 0.0,
                    "external_cost": 0.0,
                    "cost_diff": 0.0,
                    "ratio": 0.0,
                    "avg_cost": 0.0,
                    "tools": [],
                },
            )
            row["requests"] += item["requests"]
            row["cost"] += item["internal_cost"]
            row["internal_cost"] += item["internal_cost"]
            row["external_cost"] += item["external_cost"]
            row["tools"].append(
                {
                    "tool_name": item["tool_name"],
                    "namespaced_tool_name": item["namespaced_tool_name"],
                    "requests": item["requests"],
                    "internal_cost": item["internal_cost"],
                    "external_cost": item["external_cost"],
                    "cost_diff": round(item["internal_cost"] - item["external_cost"], 4),
                    "avg_cost": (
                        round(item["internal_cost"] / item["requests"], 4)
                        if item["requests"] > 0
                        else 0
                    ),
                }
            )
        items = list(grouped.values())
        total_cost = sum(item["internal_cost"] for item in items)
        for item in items:
            item["tool_count"] = len({t["namespaced_tool_name"] or t["tool_name"] for t in item["tools"]})
            item["internal_cost"] = round(item["internal_cost"], 6)
            item["external_cost"] = round(item["external_cost"], 6)
            item["cost"] = item["internal_cost"]
            item["cost_diff"] = round(item["internal_cost"] - item["external_cost"], 4)
            item["ratio"] = round(item["internal_cost"] / total_cost, 4) if total_cost > 0 else 0
            item["avg_cost"] = (
                round(item["internal_cost"] / item["requests"], 4)
                if item["requests"] > 0
                else 0
            )
            item["tools"].sort(key=lambda t: t["internal_cost"], reverse=True)
        items.sort(key=lambda item: item["internal_cost"], reverse=True)
        return {"mcp": items}
    if tab == "date":
        raw = await efficiency_repo.get_cost_detail_by_date(
            session, start_date, end_date, ct, department_id, project_id
        )
        items = [
            {
                "date": item["date"],
                "llm_cost": item["llm_cost"],
                "mcp_cost": item["mcp_cost"],
                "total_cost": item["internal_cost"],
                "external_cost": item["external_cost"],
                "cost_diff": round(item["internal_cost"] - item["external_cost"], 4),
                "requests": item["requests"],
                "active_users": item["users"],
            }
            for item in raw
        ]
        return {"date": items}
    if tab == "attribution":
        return {
            "attribution": await efficiency_repo.get_cost_attribution_detail(
                session, start_date, end_date, dimension, ct, department_id, project_id
            )
        }

    raw = await efficiency_repo.get_cost_detail_by_dimension(
        session, start_date, end_date, dimension, ct, department_id, project_id
    )
    prev_raw = await efficiency_repo.get_cost_detail_by_dimension(
        session, *_prev_period(start_date, end_date), dimension, ct, department_id, project_id
    )
    prev_by_name = {item["name"]: item["internal_cost"] for item in prev_raw}
    items = [
        {
            "department": item["name"],
            "scope_name": item["name"],
            "scope_id": item["scope_id"],
            "llm_cost": item["llm_cost"],
            "mcp_cost": item["mcp_cost"],
            "total_cost": item["internal_cost"],
            "external_cost": item["external_cost"],
            "cost_diff": round(item["internal_cost"] - item["external_cost"], 4),
            "requests": item["requests"],
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "cache_read_tokens": item["cache_read_tokens"],
            "cache_creation_tokens": item["cache_creation_tokens"],
            "per_capita_cost": item["per_capita"],
            "active_per_capita_cost": item["active_per_capita"],
            "cost_change": _calc_change(item["internal_cost"], prev_by_name.get(item["name"], 0)),
        }
        for item in raw
    ]
    return {"department": items}


async def get_cost_detail_scope_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    scope_id: int,
    cost_type: str = "all",
) -> list[dict]:
    ct = None if cost_type == "all" else cost_type
    return await efficiency_repo.get_cost_detail_scope_users(
        session, start_date, end_date, dimension, scope_id, ct
    )


async def get_top_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    metric: str = "cost",
    cost_type: str = "all",
    department_id=None,
    project_id=None,
) -> list[dict]:
    selected_cost_type = None if cost_type == "all" else cost_type
    rows = await efficiency_repo.get_user_top10(
        session,
        start_date,
        end_date,
        selected_cost_type,
        department_id,
        project_id,
        metric,
    )
    return [{"rank": index + 1, **row} for index, row in enumerate(rows)]
