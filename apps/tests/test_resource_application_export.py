from datetime import date, datetime, time
from types import SimpleNamespace

import pytest

import celery_app  # noqa: F401
from api.v1.resource_applications import _date_end, _date_start
from repositories import resource_application_repo
from services import (
    export_task_builders,
    export_task_service,
    resource_application_service,
)


class FakeScalars:
    def all(self) -> list:
        return []


class FakeResult:
    def scalars(self) -> FakeScalars:
        return FakeScalars()


class FakeSession:
    async def execute(self, statement) -> FakeResult:
        self.statement = statement
        return FakeResult()


def test_date_boundaries_are_naive_and_cover_whole_day() -> None:
    value = date(2026, 8, 14)

    assert _date_start(value) == datetime.combine(value, time.min)
    assert _date_end(value) == datetime.combine(value, time.max)
    assert _date_start(value).tzinfo is None
    assert _date_end(value).tzinfo is None


def test_export_datetime_parses_date_and_datetime_structurally() -> None:
    params = {
        "date_only": "2026-08-14",
        "with_time": "2026-08-14T12:34:56",
    }

    assert export_task_builders._datetime(
        params, "date_only", date_only_time=time.max
    ) == datetime.combine(date(2026, 8, 14), time.max)
    assert export_task_builders._datetime(params, "with_time") == datetime(
        2026, 8, 14, 12, 34, 56
    )


def test_application_domain_values_provide_export_labels() -> None:
    assert resource_application_service.ResourceType.label_for("model") == "模型"
    assert (
        resource_application_service.ApplicationStatus.label_for("pending")
        == "待审批"
    )
    assert resource_application_service.ResourceType.label_for("unknown") == "unknown"


@pytest.mark.asyncio
async def test_find_all_builds_query_without_loader_errors() -> None:
    session = FakeSession()

    result = await resource_application_repo.find_all(session)

    assert result == []
    assert session.statement is not None


@pytest.mark.asyncio
async def test_approval_export_uses_end_of_day_and_bulk_resource_queries(
    monkeypatch,
) -> None:
    user = SimpleNamespace(
        display_name="申请人",
        username="applicant",
        departments=[
            SimpleNamespace(department=SimpleNamespace(name="研发部"))
        ],
    )
    application = SimpleNamespace(
        user=user,
        reviewer=None,
        resource_type="model",
        resource_id=7,
        reason="测试",
        status="pending",
        created_at=datetime(2026, 8, 14, 9, 30),
        reviewed_at=None,
        review_notes="",
    )
    captured_filters = {}
    model_calls = []

    async def fake_list_applications_for_export(session, **kwargs):
        captured_filters.update(kwargs)
        return [application, application]

    async def fake_find_models(session, ids):
        model_calls.append(ids)
        return [SimpleNamespace(id=7, name="测试模型")]

    async def fake_empty(session, ids):
        return []

    monkeypatch.setattr(
        export_task_builders.resource_application_service,
        "list_applications_for_export",
        fake_list_applications_for_export,
    )
    monkeypatch.setattr(
        export_task_builders.model_repo, "find_by_ids", fake_find_models
    )
    monkeypatch.setattr(
        export_task_builders.mcp_repo, "find_servers_by_ids", fake_empty
    )
    monkeypatch.setattr(export_task_builders.skill_repo, "find_by_ids", fake_empty)
    monkeypatch.setattr(export_task_builders.agent_repo, "find_by_ids", fake_empty)

    header, rows = await export_task_builders._build_resource_application_rows(
        object(),
        "applications",
        {"created_before": "2026-08-14"},
    )

    assert captured_filters["created_before"] == datetime.combine(
        date(2026, 8, 14), time.max
    )
    assert model_calls == [[7]]
    assert header[3] == "资源名称"
    assert [row[3] for row in rows] == ["测试模型", "测试模型"]


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-2+3", "@SUM(A1:A2)"])
def test_csv_formula_values_are_escaped(value: str) -> None:
    assert export_task_service._sanitize_csv_cell(value) == f"'{value}"


def test_csv_regular_values_are_unchanged() -> None:
    assert export_task_service._sanitize_csv_cell("正常备注") == "正常备注"
    assert export_task_service._sanitize_csv_cell(123) == 123
