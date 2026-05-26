"""AI 效能 Service 层。"""

import calendar
import logging
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from models.db import EfficiencyReport
from repositories import efficiency_repo

logger = logging.getLogger(__name__)


def _calc_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _risk_level(rate: float) -> str:
    if rate > 100:
        return "danger"
    if rate >= 80:
        return "warning"
    return "safe"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def _prev_period(start_date: date, end_date: date) -> tuple[date, date]:
    days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    return prev_end - timedelta(days=days - 1), prev_end


async def get_overview(session: AsyncSession, start_date: date, end_date: date) -> dict:
    total_users = await efficiency_repo.get_total_user_count(session)
    active_ids = await efficiency_repo.get_active_user_ids(
        session, start_date, end_date
    )
    active_count = len(active_ids)
    total_cost = await efficiency_repo.get_total_cost(session, start_date, end_date)
    coverage_rate = round(active_count / total_users * 100, 1) if total_users > 0 else 0
    per_capita = round(total_cost / active_count, 2) if active_count > 0 else 0

    prev_start, prev_end = _prev_period(start_date, end_date)
    prev_active_ids = await efficiency_repo.get_active_user_ids(
        session, prev_start, prev_end
    )
    prev_cost = await efficiency_repo.get_total_cost(session, prev_start, prev_end)
    prev_coverage = (
        round(len(prev_active_ids) / total_users * 100, 1) if total_users > 0 else 0
    )
    prev_per_capita = (
        round(prev_cost / len(prev_active_ids), 2) if len(prev_active_ids) > 0 else 0
    )

    trend = await efficiency_repo.get_daily_cost_and_users(
        session, start_date, end_date
    )
    dept_ranking = await efficiency_repo.get_dept_ranking(session, start_date, end_date)

    ranking_items, table_items = [], []
    for dept in dept_ranking:
        t, a = dept["total_users"], dept["active_users"]
        cov = round(a / t * 100, 1) if t > 0 else 0
        pc = round(dept["total_cost"] / a, 2) if a > 0 else 0
        ranking_items.append(
            {"name": dept["name"], "coverage_rate": cov, "per_capita_cost": pc}
        )
        table_items.append(
            {
                "name": dept["name"],
                "total_members": t,
                "active_members": a,
                "coverage_rate": cov,
                "total_cost": dept["total_cost"],
                "per_capita_cost": pc,
                "change": 0,
            }
        )

    conclusion = (
        f"AI 覆盖 {coverage_rate}% 员工，"
        f"总投入 ¥{total_cost:,.0f}，人均 ¥{per_capita:,.0f}/月"
    )
    warnings = [
        f"{d['name']}人均成本偏高（¥{d['per_capita_cost']:,.0f}）"
        for d in ranking_items
        if d["per_capita_cost"] > per_capita * 1.5 and per_capita > 0
    ]

    return {
        "conclusion": conclusion,
        "warnings": warnings,
        "kpi": {
            "coverage_rate": coverage_rate,
            "total_cost": total_cost,
            "per_capita_cost": per_capita,
            "coverage_change": _calc_change(coverage_rate, prev_coverage),
            "cost_change": _calc_change(total_cost, prev_cost),
            "per_capita_change": _calc_change(per_capita, prev_per_capita),
        },
        "trend": {
            "dates": [t["date"] for t in trend],
            "active_users": [t["active_users"] for t in trend],
            "cost": [t["cost"] for t in trend],
        },
        "department_ranking": ranking_items,
        "department_table": table_items,
        "alerts": [],
    }


# ---------------------------------------------------------------------------
# Adoption
# ---------------------------------------------------------------------------


async def get_adoption(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    metric: str = "dau",
) -> dict:
    total_users = await efficiency_repo.get_total_user_count(session)
    active_ids = await efficiency_repo.get_active_user_ids(
        session, start_date, end_date
    )
    active_count = len(active_ids)
    coverage_rate = round(active_count / total_users * 100, 1) if total_users > 0 else 0
    days = (end_date - start_date).days + 1

    prev_start, prev_end = _prev_period(start_date, end_date)
    prev_active_ids = await efficiency_repo.get_active_user_ids(
        session, prev_start, prev_end
    )
    new_active = len(active_ids - prev_active_ids)

    user_calls = await efficiency_repo.get_user_call_counts(
        session, start_date, end_date
    )
    daily_avg_frequency = 0.0
    heavy_user_count = 0
    if user_calls and days > 0:
        total_calls = sum(u["calls"] for u in user_calls)
        daily_avg_frequency = (
            round(total_calls / active_count / days, 1) if active_count > 0 else 0
        )
        heavy_user_count = sum(1 for u in user_calls if u["calls"] >= 10 * days)
    heavy_user_ratio = (
        round(heavy_user_count / active_count * 100, 1) if active_count > 0 else 0
    )

    light_t, heavy_t = 3 * days, 10 * days
    light = sum(1 for u in user_calls if u["calls"] < light_t)
    medium = sum(1 for u in user_calls if light_t <= u["calls"] < heavy_t)
    heavy = sum(1 for u in user_calls if u["calls"] >= heavy_t)

    active_trend_raw = await efficiency_repo.get_daily_active_users(
        session, start_date, end_date
    )

    if dimension == "project":
        raw_table = await efficiency_repo.get_project_adoption_table(
            session, start_date, end_date
        )
    else:
        raw_table = await efficiency_repo.get_dept_adoption_table(
            session, start_date, end_date
        )

    department_table = [
        {
            "name": row["name"],
            "total_members": row["total"],
            "active_members": row["active"],
            "coverage_rate": row["coverage"],
            "daily_avg_calls": row["daily_calls"],
            "heavy_user_ratio": 0,
            "change": 0,
        }
        for row in raw_table
    ]

    return {
        "kpi": {
            "coverage_rate": coverage_rate,
            "new_active": new_active,
            "daily_avg_frequency": daily_avg_frequency,
            "heavy_user_ratio": heavy_user_ratio,
        },
        "active_trend": {
            "dates": [item["date"] for item in active_trend_raw],
            "values": [item["dau"] for item in active_trend_raw],
        },
        "depth_distribution": {"light": light, "medium": medium, "heavy": heavy},
        "heavy_trend": {"dates": [], "ratios": []},
        "department_table": department_table,
    }


async def get_adoption_agents(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    raw = await efficiency_repo.get_agent_hotness(session, start_date, end_date)
    result = []
    for i, agent in enumerate(raw):
        result.append(
            {
                "rank": i + 1,
                "name": agent["name"],
                "platform": agent["platform"],
                "department": agent["department"],
                "user_count": agent["user_count"],
                "monthly_calls": agent["monthly_calls"],
                "trend": [],
            }
        )
    return result


async def get_adoption_resources(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    resource_type: str = "mcp",
) -> list[dict]:
    if resource_type == "skill":
        raw = await efficiency_repo.get_skill_hotness(session, start_date, end_date)
        return [
            {
                "name": item["name"],
                "type": "skill",
                "user_count": item.get("install_count", 0),
                "monthly_calls": item.get("monthly_downloads", 0),
                "department": "",
            }
            for item in raw
        ]
    raw = await efficiency_repo.get_mcp_hotness(session, start_date, end_date)
    return [
        {
            "name": item["name"],
            "type": "mcp",
            "user_count": item["user_count"],
            "monthly_calls": item["monthly_calls"],
            "department": "",
        }
        for item in raw
    ]


async def get_unused_users(
    session: AsyncSession, start_date: date, end_date: date
) -> list[dict]:
    raw = await efficiency_repo.get_unused_users(session, start_date, end_date)
    return [
        {
            "name": item["display_name"],
            "department": item["department"],
            "position": item["position"] or "",
            "assigned_key": "有" if item["has_key"] else "无",
            "last_active": item["last_active"] or "",
        }
        for item in raw
    ]


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------


async def get_cost(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    cost_type: str = "all",
    department_id: int | None = None,
) -> dict:
    days = (end_date - start_date).days + 1
    prev_start, prev_end = _prev_period(start_date, end_date)
    cost_filters = None if cost_type == "all" else cost_type

    trend_raw = await efficiency_repo.get_cost_trend(
        session, start_date, end_date, cost_filters, department_id
    )
    prev_trend_raw = await efficiency_repo.get_cost_trend(
        session, prev_start, prev_end, cost_filters, department_id
    )
    total_cost = sum(r["cost"] for r in trend_raw)
    prev_total = sum(r["cost"] for r in prev_trend_raw)

    date_map: dict[str, dict] = {}
    for r in trend_raw:
        d = r["date"]
        if d not in date_map:
            date_map[d] = {"date": d, "llm_cost": 0, "mcp_cost": 0, "is_anomaly": False}
        if r["cost_type"] == "llm":
            date_map[d]["llm_cost"] = r["cost"]
        elif r["cost_type"] == "mcp":
            date_map[d]["mcp_cost"] = r["cost"]

    by_type = await efficiency_repo.get_cost_by_type(
        session, start_date, end_date, department_id
    )
    by_dept = await efficiency_repo.get_cost_by_dept(session, start_date, end_date)
    raw_pc = await efficiency_repo.get_dept_per_capita_cost(
        session, start_date, end_date
    )

    return {
        "kpi": {
            "total_cost": round(total_cost, 2),
            "daily_avg_cost": round(total_cost / days, 2) if days > 0 else 0,
            "cost_change": _calc_change(total_cost, prev_total),
        },
        "trend": sorted(date_map.values(), key=lambda x: x["date"]),
        "composition": {"by_resource_type": by_type, "by_department": by_dept},
        "per_capita": [
            {"department": i["name"], "per_capita_cost": i["value"]} for i in raw_pc
        ],
    }


async def get_cost_detail(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    tab: str = "department",
    cost_type: str = "all",
    department_id: int | None = None,
) -> dict:
    ct = None if cost_type == "all" else cost_type
    if tab == "model":
        raw = await efficiency_repo.get_cost_detail_by_model(
            session, start_date, end_date, ct, department_id
        )
        total_cost = sum(item["cost"] for item in raw)
        items = [
            {
                "model": item["model"],
                "requests": item["requests"],
                "tokens": item["input_tokens"] + item["output_tokens"],
                "cost": item["cost"],
                "ratio": round(item["cost"] / total_cost, 4) if total_cost > 0 else 0,
                "avg_cost": (
                    round(item["cost"] / item["requests"], 4)
                    if item["requests"] > 0
                    else 0
                ),
            }
            for item in raw
        ]
        return {"model": items}
    elif tab == "date":
        raw = await efficiency_repo.get_cost_detail_by_date(
            session, start_date, end_date, ct, department_id
        )
        items = [
            {
                "date": item["date"],
                "llm_cost": 0,
                "mcp_cost": 0,
                "total_cost": item["cost"],
                "requests": item["requests"],
                "active_users": item["users"],
            }
            for item in raw
        ]
        return {"date": items}
    else:
        raw = await efficiency_repo.get_cost_detail_by_department(
            session, start_date, end_date, ct, department_id
        )
        items = [
            {
                "department": item["name"],
                "llm_cost": 0,
                "mcp_cost": 0,
                "total_cost": item["cost"],
                "requests": item["requests"],
                "per_capita_cost": item["per_capita"],
                "cost_change": None,
            }
            for item in raw
        ]
        return {"department": items}


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


async def get_budget(session: AsyncSession) -> dict:
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = (today - month_start).days + 1

    keys = await efficiency_repo.get_all_keys_with_budget(session)
    total_budget = sum(float(k.budget_limit) for k in keys)
    total_used = sum(float(k.budget_used) for k in keys)
    execution_rate = (
        round(total_used / total_budget * 100, 1) if total_budget > 0 else 0
    )
    remaining = round(total_budget - total_used, 2)
    predicted = (
        round(total_used / days_passed * days_in_month, 2)
        if days_passed > 0
        else total_used
    )

    cumulative_raw = await efficiency_repo.get_cumulative_cost_by_date(
        session, month_start, today
    )
    daily_budget = round(total_budget / days_in_month, 2) if days_in_month > 0 else 0
    trend = [
        {
            "date": item["date"],
            "actual_cumulative": item["actual"],
            "predicted_cumulative": None,
            "budget_limit": round(daily_budget * (i + 1), 2),
        }
        for i, item in enumerate(cumulative_raw)
    ]

    month_end = today.replace(day=days_in_month)
    dept_rows = await efficiency_repo.get_dept_budget_usage(
        session, month_start, month_end
    )
    departments = []
    for row in dept_rows:
        b, u = row["budget"], row["used"]
        rate = round(u / b * 100, 1) if b > 0 else 0
        departments.append(
            {
                "department": row["name"],
                "monthly_budget": b,
                "used": u,
                "execution_rate": rate,
                "predicted_end": (
                    round(u / days_passed * days_in_month, 2) if days_passed > 0 else u
                ),
                "risk": _risk_level(rate),
                "trend": [],
            }
        )

    project_rows = await efficiency_repo.get_project_budget_usage(session)
    projects = []
    for row in project_rows:
        b, u = row["budget"], row["used"]
        rate = round(u / b * 100, 1) if b > 0 else 0
        projects.append(
            {
                "project": row["name"],
                "monthly_budget": b,
                "used": u,
                "execution_rate": rate,
                "predicted_end": (
                    round(u / days_passed * days_in_month, 2) if days_passed > 0 else u
                ),
                "risk": _risk_level(rate),
            }
        )

    key_raw = await efficiency_repo.get_key_top10_budget(session)
    keys_list = [
        {
            "key_name": i["name"],
            "owner": i["owner"],
            "key_type": i["key_type"],
            "budget": i["budget"],
            "used": i["used"],
            "execution_rate": i["rate"],
        }
        for i in key_raw
    ]

    return {
        "global": {
            "budget": total_budget,
            "used": total_used,
            "execution_rate": execution_rate,
            "remaining": remaining,
            "predicted": predicted,
            "risk": _risk_level(execution_rate),
        },
        "trend": trend,
        "departments": departments,
        "projects": projects,
        "keys": keys_list,
    }


async def get_budget_alerts(session: AsyncSession) -> list[dict]:
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = (today - month_start).days + 1

    alerts = []
    for k in await efficiency_repo.get_all_keys_with_budget(session):
        budget, used = float(k.budget_limit), float(k.budget_used)
        if budget <= 0:
            continue
        rate = round(used / budget * 100, 1)
        pred = round(used / days_passed * days_in_month, 2) if days_passed > 0 else used
        if rate >= 80 or pred > budget:
            alerts.append(
                {
                    "target": k.name,
                    "type": k.key_type or "",
                    "execution_rate": rate,
                    "predicted_overspend": (
                        round(pred - budget, 2) if pred > budget else 0
                    ),
                    "suggestion": (
                        "建议提升预算额度" if pred > budget else "关注使用趋势"
                    ),
                }
            )
    return alerts


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


async def list_reports(
    session: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list, int]:
    reports, total = await efficiency_repo.list_reports(session, page, page_size)
    items = [
        {
            "id": r.id,
            "report_type": r.report_type,
            "period_start": str(r.period_start),
            "period_end": str(r.period_end),
            "model_used": r.model_used,
            "summary": r.summary,
            "created_at": str(r.created_at),
        }
        for r in reports
    ]
    return items, total


async def get_report_detail(session: AsyncSession, report_id: int) -> dict | None:
    report = await efficiency_repo.get_report_by_id(session, report_id)
    if not report:
        return None
    suggestions = await efficiency_repo.list_suggestions_by_report(session, report_id)
    return {
        "id": report.id,
        "report_type": report.report_type,
        "period_start": str(report.period_start),
        "period_end": str(report.period_end),
        "filters": report.filters,
        "model_used": report.model_used,
        "summary": report.summary,
        "content_md": report.content_md,
        "created_at": str(report.created_at),
        "generation_cost": float(report.generation_cost),
        "generation_duration_ms": report.generation_duration_ms,
        "suggestions": [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "priority": s.priority,
                "expected_impact": s.expected_impact,
                "status": s.status,
                "status_note": s.status_note,
            }
            for s in suggestions
        ],
    }


async def create_report(
    session: AsyncSession,
    report_type: str,
    period_start: date,
    period_end: date,
    created_by: int,
    model_used: str | None = None,
    filters: dict | None = None,
) -> dict:
    report = EfficiencyReport(
        report_type=report_type,
        period_start=period_start,
        period_end=period_end,
        filters=filters or {},
        model_used=model_used,
        summary="报告生成中...",
        content_md="",
        created_by=created_by,
    )
    report = await efficiency_repo.create_report(session, report)
    await session.commit()
    return {"id": report.id, "status": "created"}


async def update_suggestion_status(
    session: AsyncSession,
    suggestion_id: int,
    status: str,
    note: str,
    updated_by: int,
) -> dict | None:
    suggestion = await efficiency_repo.update_suggestion_status(
        session, suggestion_id, status, note, updated_by
    )
    if not suggestion:
        return None
    await session.commit()
    return {"id": suggestion.id, "status": suggestion.status}
