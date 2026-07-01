import pytest
from pydantic import ValidationError as PydanticValidationError

from api.v1.resource_applications import BatchApproveRequest, BatchRejectRequest
from exceptions import ConflictError, NotFoundError
from services import resource_application_service


class FakeSession:
    def __init__(self) -> None:
        self.rollback_count = 0

    async def rollback(self) -> None:
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_batch_approve_all_pending_returns_success(monkeypatch) -> None:
    reviewed_ids: list[int] = []

    async def fake_approve_application(
        session,
        app_id: int,
        reviewer_id: int,
        approval_config: dict | None = None,
        review_notes: str = "",
    ) -> dict:
        reviewed_ids.append(app_id)
        return {"id": app_id}

    monkeypatch.setattr(
        resource_application_service,
        "approve_application",
        fake_approve_application,
    )
    session = FakeSession()

    result = await resource_application_service.batch_approve_applications(
        session, [1, 2], 9, {"scope": "all"}, "ok"
    )

    assert result == {"success": [1, 2], "failed": []}
    assert reviewed_ids == [1, 2]
    assert session.rollback_count == 0


@pytest.mark.asyncio
async def test_batch_approve_mixed_status_returns_partial_failures(monkeypatch) -> None:
    async def fake_approve_application(
        session,
        app_id: int,
        reviewer_id: int,
        approval_config: dict | None = None,
        review_notes: str = "",
    ) -> dict:
        if app_id == 2:
            raise ConflictError("该申请已处理")
        if app_id == 3:
            raise NotFoundError("resource_application", app_id)
        return {"id": app_id}

    monkeypatch.setattr(
        resource_application_service,
        "approve_application",
        fake_approve_application,
    )
    session = FakeSession()

    result = await resource_application_service.batch_approve_applications(
        session, [1, 2, 3], 9, None, "ok"
    )

    assert result == {
        "success": [1],
        "failed": [
            {"id": 2, "reason": "该申请已处理"},
            {"id": 3, "reason": "申请不存在"},
        ],
    }
    assert session.rollback_count == 2


@pytest.mark.asyncio
async def test_batch_reject_mixed_status_returns_partial_failures(monkeypatch) -> None:
    async def fake_reject_application(
        session,
        app_id: int,
        reviewer_id: int,
        review_notes: str = "",
    ) -> dict:
        if app_id == 7:
            raise ConflictError("该申请已处理")
        return {"id": app_id}

    monkeypatch.setattr(
        resource_application_service,
        "reject_application",
        fake_reject_application,
    )
    session = FakeSession()

    result = await resource_application_service.batch_reject_applications(
        session, [6, 7], 9, "no"
    )

    assert result == {
        "success": [6],
        "failed": [{"id": 7, "reason": "该申请已处理"}],
    }
    assert session.rollback_count == 1


def test_batch_approve_empty_app_ids_fails_validation() -> None:
    with pytest.raises(PydanticValidationError):
        BatchApproveRequest(app_ids=[])


def test_batch_reject_too_many_app_ids_fails_validation() -> None:
    with pytest.raises(PydanticValidationError):
        BatchRejectRequest(app_ids=list(range(201)))
