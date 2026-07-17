"""Auxiliary adoption sections for AI efficiency."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import efficiency_repo


async def get_adoption_scope_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str,
    scope_id: int,
) -> list[dict]:
    return await efficiency_repo.get_adoption_scope_users(
        session, start_date, end_date, dimension, scope_id
    )


async def get_adoption_agents(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    raw = await efficiency_repo.get_agent_hotness(
        session, start_date, end_date, dimension, department_ids, project_ids
    )
    return [
        {
            "id": agent["id"],
            "rank": index + 1,
            "name": agent["name"],
            "platform": agent["platform"],
            "department": agent["department"],
            "user_count": agent["user_count"],
            "monthly_calls": agent["monthly_calls"],
            "trend": [],
        }
        for index, agent in enumerate(raw)
    ]


async def get_adoption_resources(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    resource_type: str = "mcp",
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    if resource_type == "skill":
        raw = await efficiency_repo.get_skill_hotness(
            session, start_date, end_date, dimension, department_ids, project_ids
        )
        return [
            {
                "id": item["id"],
                "name": item["name"],
                "type": "skill",
                "user_count": item.get("install_count", 0),
                "monthly_calls": item.get("monthly_downloads", 0),
                "department": item.get("scope_names", ""),
            }
            for item in raw
        ]
    raw = await efficiency_repo.get_mcp_hotness(
        session, start_date, end_date, dimension, department_ids, project_ids
    )
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "type": "mcp",
            "user_count": item["user_count"],
            "monthly_calls": item["monthly_calls"],
            "department": item.get("scope_names", ""),
        }
        for item in raw
    ]


async def get_unused_users(
    session: AsyncSession,
    start_date: date,
    end_date: date,
    dimension: str = "department",
    department_ids: list[int] | None = None,
    project_ids: list[int] | None = None,
) -> list[dict]:
    raw = await efficiency_repo.get_unused_users(
        session, start_date, end_date, dimension, department_ids, project_ids
    )
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
