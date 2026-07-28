import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.time_utils import fmt_local_time
from exceptions import NotFoundError, ConflictError
from models.db import KeyScenario
from repositories import key_scenario_repo

logger = logging.getLogger(__name__)


async def list_scenarios(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    keyword: str | None = None,
) -> dict:
    total = await key_scenario_repo.count_all(session, keyword)
    items = await key_scenario_repo.find_all(session, page, page_size, keyword)
    return {
        "items": [_serialize(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_all_active(session: AsyncSession) -> list[dict]:
    items = await key_scenario_repo.find_all_active(session)
    return [_serialize(s) for s in items]


async def get_scenario_by_id(session: AsyncSession, scenario_id: int) -> dict:
    scenario = await key_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("scenario", scenario_id)
    return _serialize(scenario)


async def create_scenario(
    session: AsyncSession,
    name: str,
    description: str = "",
) -> dict:
    existing = await key_scenario_repo.find_by_name(session, name)
    if existing:
        raise ConflictError(f"场景名称 '{name}' 已存在")

    scenario = KeyScenario(name=name, description=description)
    scenario = await key_scenario_repo.create(session, scenario)
    await session.commit()
    return _serialize(scenario)


async def update_scenario(
    session: AsyncSession,
    scenario_id: int,
    name: str | None = None,
    description: str | None = None,
) -> dict:
    scenario = await key_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("scenario", scenario_id)

    if name is not None:
        if name != scenario.name:
            existing = await key_scenario_repo.find_by_name(session, name)
            if existing:
                raise ConflictError(f"场景名称 '{name}' 已存在")
        scenario.name = name
    if description is not None:
        scenario.description = description

    await session.commit()
    await session.refresh(scenario)
    return _serialize(scenario)


async def delete_scenario(session: AsyncSession, scenario_id: int) -> None:
    scenario = await key_scenario_repo.find_by_id(session, scenario_id)
    if not scenario:
        raise NotFoundError("scenario", scenario_id)

    scenario.is_active = False
    await session.commit()


def _serialize(scenario: KeyScenario) -> dict:
    return {
        "id": scenario.id,
        "name": scenario.name,
        "description": scenario.description,
        "is_active": scenario.is_active,
        "created_at": fmt_local_time(scenario.created_at),
        "updated_at": fmt_local_time(scenario.updated_at),
    }
