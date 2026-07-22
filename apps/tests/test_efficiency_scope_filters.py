from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.v1 import efficiency as efficiency_api
from repositories.efficiency_cost_repo import (
    _build_cost_filters,
    _cost_dimension_config,
    _dimension_membership_join_filter,
)
from repositories.efficiency_scope_filter import build_scope_filter
from services import efficiency_budget_service


def test_scope_filter_multiple_departments_uses_bound_parameters():
    params = {}

    clause = build_scope_filter("c.user_id", [12, 34], None, params, "overview")

    assert "user_departments" in clause
    assert "IN (:overview_department_0, :overview_department_1)" in clause
    assert params == {"overview_department_0": 12, "overview_department_1": 34}


def test_scope_filter_without_ids_adds_no_query_condition():
    params = {}

    clause = build_scope_filter("c.user_id", None, None, params, "overview")

    assert clause == ""
    assert params == {}


def test_cost_filter_without_alias_correlates_outer_cost_user():
    filters, params = _build_cost_filters(
        date(2026, 7, 1), date(2026, 7, 17), None, [26]
    )

    assert "ud_filter.user_id = cost_summary_daily.user_id" in filters
    assert params["dept_id_0"] == 26


def test_project_dimension_join_only_attributes_selected_project():
    params = {}
    _name, join_sql, _label = _cost_dimension_config(
        "project", params, None, [8]
    )

    assert "up_dim.project_id IN (:dimension_project_0)" in join_sql
    assert params == {"dimension_project_0": 8}

    multiple_params = {}
    clause = _dimension_membership_join_filter(
        "project", multiple_params, None, [8, 10]
    )
    assert clause == (
        " AND up_dim.project_id IN "
        "(:dimension_project_0, :dimension_project_1)"
    )
    assert multiple_params == {
        "dimension_project_0": 8,
        "dimension_project_1": 10,
    }


@pytest.mark.asyncio
async def test_overview_department_scope_ids_forwards_selected_departments(monkeypatch):
    session = object()
    get_overview = AsyncMock(return_value={})
    get_freshness = AsyncMock(return_value={})
    monkeypatch.setattr(efficiency_api.efficiency_service, "get_overview", get_overview)
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_freshness", get_freshness
    )

    await efficiency_api.get_overview(
        None,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "day",
        "department",
        "12,34",
        None,
        session,
        {"id": 1},
    )

    get_overview.assert_awaited_once_with(
        session,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "day",
        "department",
        [12, 34],
        None,
    )


@pytest.mark.asyncio
async def test_adoption_project_scope_ids_forwards_selected_projects(monkeypatch):
    session = object()
    get_adoption = AsyncMock(return_value={})
    get_freshness = AsyncMock(return_value={})
    monkeypatch.setattr(efficiency_api.efficiency_service, "get_adoption", get_adoption)
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_freshness", get_freshness
    )

    await efficiency_api.get_adoption(
        None,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "project",
        "7,9",
        "dau",
        session,
        {"id": 1},
    )

    get_adoption.assert_awaited_once_with(
        session,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "project",
        "dau",
        None,
        [7, 9],
    )


@pytest.mark.asyncio
async def test_budget_without_scope_ids_keeps_unfiltered_behavior(monkeypatch):
    session = object()
    get_budget = AsyncMock(return_value={})
    get_freshness = AsyncMock(return_value={})
    monkeypatch.setattr(efficiency_api.efficiency_service, "get_budget", get_budget)
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_freshness", get_freshness
    )

    await efficiency_api.get_budget(
        "2026-07",
        "department",
        "",
        session,
        {"id": 1},
    )

    get_budget.assert_awaited_once_with(session, "2026-07", [], None)


@pytest.mark.asyncio
async def test_adoption_unused_users_forwards_selected_departments(monkeypatch):
    session = object()
    get_unused_users = AsyncMock(return_value=[])
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_unused_users", get_unused_users
    )

    await efficiency_api.get_unused_users(
        None,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "department",
        "26",
        session,
        {"id": 1},
    )

    get_unused_users.assert_awaited_once_with(
        session,
        date(2026, 7, 1),
        date(2026, 7, 17),
        "department",
        [26],
        None,
    )


@pytest.mark.asyncio
async def test_budget_alerts_forwards_selected_projects(monkeypatch):
    session = object()
    get_budget_alerts = AsyncMock(return_value=[])
    monkeypatch.setattr(
        efficiency_api.efficiency_service, "get_budget_alerts", get_budget_alerts
    )

    await efficiency_api.get_budget_alerts(
        "2026-07",
        "project",
        "7,9",
        session,
        {"id": 1},
    )

    get_budget_alerts.assert_awaited_once_with(session, "2026-07", None, [7, 9])


@pytest.mark.asyncio
async def test_budget_scope_global_usage_matches_scope_cost(monkeypatch):
    session = object()
    monkeypatch.setattr(
        efficiency_budget_service,
        "_parse_budget_month",
        lambda _month: (
            date(2026, 7, 1),
            date(2026, 7, 31),
            date(2026, 7, 17),
            31,
            17,
            True,
            "2026-07",
        ),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_all_keys_with_budget",
        AsyncMock(return_value=[SimpleNamespace(id=1, budget_limit=3000)]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_scope_budget_key_ids",
        AsyncMock(return_value={1}),
    )
    get_total_cost = AsyncMock(return_value=125.0)
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_total_cost",
        get_total_cost,
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_daily_cost_and_users",
        AsyncMock(
            return_value=[
                {"date": "2026-07-01", "cost": 50.0, "active_users": 1},
                {"date": "2026-07-02", "cost": 75.0, "active_users": 1},
            ]
        ),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_dept_budget_usage",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_project_budget_usage",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_key_top10_budget",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_user_personal_key_budget",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_user_budget_top10",
        AsyncMock(return_value=[]),
    )

    result = await efficiency_budget_service.get_budget(
        session, "2026-07", [28], None
    )

    get_total_cost.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), [28], None
    )
    assert result["global"]["used"] == 125.0
    assert [item["actual_cumulative"] for item in result["trend"]] == [50.0, 125.0]


@pytest.mark.asyncio
async def test_budget_without_scope_counts_all_usage(monkeypatch):
    session = object()
    monkeypatch.setattr(
        efficiency_budget_service,
        "_parse_budget_month",
        lambda _month: (
            date(2026, 7, 1),
            date(2026, 7, 31),
            date(2026, 7, 17),
            31,
            17,
            True,
            "2026-07",
        ),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_all_keys_with_budget",
        AsyncMock(return_value=[SimpleNamespace(id=1, budget_limit=10000)]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_scope_budget_key_ids",
        AsyncMock(return_value=None),
    )
    get_total_cost = AsyncMock(return_value=11000.0)
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_total_cost",
        get_total_cost,
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_cumulative_cost_by_date",
        AsyncMock(return_value=[{"date": "2026-07-01", "actual": 11000.0}]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_dept_budget_usage",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_project_budget_usage",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_key_top10_budget",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_user_personal_key_budget",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_user_budget_top10",
        AsyncMock(return_value=[]),
    )

    result = await efficiency_budget_service.get_budget(session, "2026-07")

    get_total_cost.assert_awaited_once_with(
        session, date(2026, 7, 1), date(2026, 7, 17), None, None
    )
    assert result["global"]["budget"] == 10000.0
    assert result["global"]["used"] == 11000.0
    assert result["global"]["execution_rate"] == 110.0


@pytest.mark.asyncio
async def test_budget_alerts_loads_usage_in_one_batch(monkeypatch):
    session = object()
    monkeypatch.setattr(
        efficiency_budget_service,
        "_parse_budget_month",
        lambda _month: (
            date(2026, 7, 1),
            date(2026, 7, 31),
            date(2026, 7, 17),
            31,
            17,
            True,
            "2026-07",
        ),
    )
    keys = [
        SimpleNamespace(id=1, name="Key 1", key_type="personal", budget_limit=100),
        SimpleNamespace(id=2, name="Key 2", key_type="personal", budget_limit=200),
    ]
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_scope_budget_key_ids",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_all_keys_with_budget",
        AsyncMock(return_value=keys),
    )
    get_usage = AsyncMock(return_value={1: 90.0, 2: 50.0})
    monkeypatch.setattr(
        efficiency_budget_service.efficiency_repo,
        "get_budget_usage_by_key",
        get_usage,
    )

    alerts = await efficiency_budget_service.get_budget_alerts(session, "2026-07")

    get_usage.assert_awaited_once_with(
        session, [1, 2], date(2026, 7, 1), date(2026, 7, 17)
    )
    assert [alert["target"] for alert in alerts] == ["Key 1"]
