import logging

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import NotFoundError, ConflictError
from models.db import BusinessScenario
from repositories import business_scenario_repo

logger = logging.getLogger(__name__)


async def list_scenarios(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    keyword: str | None = None,
    include_inactive: bool = False,
) -> dict:
    total = await business_scenario_repo.count_all(session, keyword, include_inactive)
    items = await business_scenario_repo.find_all(
        session, page, page_size, keyword, include_inactive
    )
    return {
        "items": [_serialize(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_all_active(session: AsyncSession) -> list[dict]:
    items = await business_scenario_repo.find_all_active(session)
    return [_serialize(s) for s in items]


async def get_scenario_by_id(session: AsyncSession, scenario_id: int) -> dict:
    scenario = await business_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("business_scenario", scenario_id)
    return _serialize(scenario)


async def create_scenario(
    session: AsyncSession,
    code: str,
    name: str,
    description: str = "",
    icon: str = "Target",
    sort_order: int = 0,
) -> dict:
    existing = await business_scenario_repo.find_by_code(session, code)
    if existing:
        raise ConflictError(f"业务场景编码 '{code}' 已存在")

    scenario = BusinessScenario(
        code=code,
        name=name,
        description=description,
        icon=icon,
        sort_order=sort_order,
    )
    scenario = await business_scenario_repo.create(session, scenario)
    await session.commit()
    return _serialize(scenario)


async def update_scenario(
    session: AsyncSession,
    scenario_id: int,
    name: str | None = None,
    description: str | None = None,
    icon: str | None = None,
    sort_order: int | None = None,
    is_active: bool | None = None,
) -> dict:
    scenario = await business_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("business_scenario", scenario_id)

    if name is not None:
        scenario.name = name
    if description is not None:
        scenario.description = description
    if icon is not None:
        scenario.icon = icon
    if sort_order is not None:
        scenario.sort_order = sort_order
    if is_active is not None:
        scenario.is_active = is_active

    await session.commit()
    await session.refresh(scenario)
    return _serialize(scenario)


async def delete_scenario(session: AsyncSession, scenario_id: int) -> None:
    scenario = await business_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("business_scenario", scenario_id)

    scenario.is_active = False
    await session.commit()


def _serialize(scenario: BusinessScenario) -> dict:
    return {
        "id": scenario.id,
        "code": scenario.code,
        "name": scenario.name,
        "description": scenario.description,
        "icon": scenario.icon,
        "sort_order": scenario.sort_order,
        "is_active": scenario.is_active,
        "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
        "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None,
    }
