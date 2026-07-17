import calendar
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import efficiency_repo


def _risk_level(rate: float) -> str:
    if rate > 100:
        return "danger"
    if rate >= 80:
        return "warning"
    return "safe"


def _parse_budget_month(month: str | None) -> tuple[date, date, date, int, int, bool, str]:
    today = date.today()
    if month:
        year, month_num = map(int, month.split("-"))
    else:
        year, month_num = today.year, today.month
    days_in_month = calendar.monthrange(year, month_num)[1]
    month_start = date(year, month_num, 1)
    month_end = date(year, month_num, days_in_month)
    is_current_month = month_start <= today <= month_end
    if is_current_month:
        usage_end = today
        days_passed = (today - month_start).days + 1
    elif month_end < today:
        usage_end = month_end
        days_passed = days_in_month
    else:
        usage_end = month_end
        days_passed = 0
    return month_start, month_end, usage_end, days_in_month, days_passed, is_current_month, f"{year:04d}-{month_num:02d}"


async def get_budget(
    session: AsyncSession,
    month: str | None = None,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> dict:
    month_start, month_end, usage_end, days_in_month, days_passed, is_current_month, month_key = _parse_budget_month(month)

    keys = await efficiency_repo.get_all_keys_with_budget(session)
    selected_key_ids = await efficiency_repo.get_scope_budget_key_ids(
        session, department_ids, project_ids
    )
    if selected_key_ids is not None:
        keys = [key for key in keys if int(key.id) in selected_key_ids]
    total_budget = sum(float(k.budget_limit) for k in keys)
    key_ids = [int(key.id) for key in keys] if selected_key_ids is not None else None
    has_scope_filter = bool(department_ids or project_ids)
    total_used = await efficiency_repo.get_total_cost(
        session, month_start, usage_end, department_ids, project_ids
    )
    execution_rate = (
        round(total_used / total_budget * 100, 1) if total_budget > 0 else 0
    )
    remaining = round(total_budget - total_used, 2)
    predicted = (
        round(total_used / days_passed * days_in_month, 2)
        if is_current_month and days_passed > 0
        else total_used
    )

    if has_scope_filter:
        daily_usage = await efficiency_repo.get_daily_cost_and_users(
            session,
            month_start,
            usage_end,
            "day",
            department_ids,
            project_ids,
        )
        cumulative_raw = []
        cumulative_cost = 0.0
        for item in daily_usage:
            cumulative_cost += float(item["cost"])
            cumulative_raw.append(
                {"date": item["date"], "actual": round(cumulative_cost, 2)}
            )
    else:
        cumulative_raw = await efficiency_repo.get_cumulative_cost_by_date(
            session, month_start, usage_end
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

    dept_rows = await efficiency_repo.get_dept_budget_usage(
        session, month_start, usage_end, department_ids, project_ids
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
                "user_key_budget": row.get("user_key_budget", 0),
                "user_key_used": row.get("user_key_used", 0),
                "user_key_count": row.get("user_key_count", 0),
                "scope_key_budget": row.get("scope_key_budget", 0),
                "scope_key_used": row.get("scope_key_used", 0),
                "scope_key_count": row.get("scope_key_count", 0),
                "execution_rate": rate,
                "predicted_end": (
                    round(u / days_passed * days_in_month, 2)
                    if is_current_month and days_passed > 0
                    else u
                ),
                "risk": _risk_level(rate),
                "trend": [],
            }
        )

    project_rows = await efficiency_repo.get_project_budget_usage(
        session, month_start, usage_end, project_ids, department_ids
    )
    projects = []
    for row in project_rows:
        b, u = row["budget"], row["used"]
        rate = round(u / b * 100, 1) if b > 0 else 0
        projects.append(
            {
                "project": row["name"],
                "monthly_budget": b,
                "used": u,
                "user_key_budget": row.get("user_key_budget", 0),
                "user_key_used": row.get("user_key_used", 0),
                "user_key_count": row.get("user_key_count", 0),
                "scope_key_budget": row.get("scope_key_budget", 0),
                "scope_key_used": row.get("scope_key_used", 0),
                "scope_key_count": row.get("scope_key_count", 0),
                "execution_rate": rate,
                "predicted_end": (
                    round(u / days_passed * days_in_month, 2)
                    if is_current_month and days_passed > 0
                    else u
                ),
                "risk": _risk_level(rate),
            }
        )

    key_raw = await efficiency_repo.get_key_top10_budget(
        session, month_start, usage_end, key_ids
    )
    keys_list = [
        {
            "key_name": i["name"],
            "owner": i["owner"],
            "owner_type": i.get("owner_type", ""),
            "key_type": i["key_type"],
            "budget": i["budget"],
            "used": i["used"],
            "execution_rate": i["rate"],
        }
        for i in key_raw
    ]

    return {
        "period": {
            "month": month_key,
            "start_date": month_start.isoformat(),
            "end_date": month_end.isoformat(),
            "usage_end_date": usage_end.isoformat(),
            "is_current_month": is_current_month,
        },
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


async def get_budget_alerts(
    session: AsyncSession,
    month: str | None = None,
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    month_start, _month_end, usage_end, days_in_month, days_passed, is_current_month, _month_key = _parse_budget_month(month)

    selected_key_ids = await efficiency_repo.get_scope_budget_key_ids(
        session, department_ids, project_ids
    )
    keys = await efficiency_repo.get_all_keys_with_budget(session)
    if selected_key_ids is not None:
        keys = [key for key in keys if int(key.id) in selected_key_ids]
    usage_by_key = await efficiency_repo.get_budget_usage_by_key(
        session,
        [int(key.id) for key in keys],
        month_start,
        usage_end,
    )
    alerts = []
    for k in keys:
        budget = float(k.budget_limit)
        used = usage_by_key.get(int(k.id), 0.0)
        if budget <= 0:
            continue
        rate = round(used / budget * 100, 1)
        pred = (
            round(used / days_passed * days_in_month, 2)
            if is_current_month and days_passed > 0
            else used
        )
        if rate >= 80 or pred > budget:
            alerts.append(
                {
                    "target": k.name,
                    "type": k.key_type or "",
                    "execution_rate": rate,
                    "predicted_overspend": (
                        round(pred - budget, 2) if pred > budget else 0
                    ),
                }
            )
    return alerts
