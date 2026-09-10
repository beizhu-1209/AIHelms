"""Model publication rules with synthetic users; no real DB or LiteLLM calls."""

from dataclasses import dataclass
from hashlib import sha256
from unittest.mock import AsyncMock

import pytest

from exceptions import ConflictError
from models.db import AiKey, Model, ModelUserVisibility, User
from repositories import ai_key_repo, model_repo, resource_application_repo
from services import ai_key_service, model_service, resource_application_service

MODEL_NAME = "qa-publish-model"
OTHER_MODEL = "qa-unrelated-model"


@dataclass
class Population:
    users: dict[int, User]
    keys: list[AiKey]
    department_a: list[int]
    department_b: list[int]


def make_population() -> Population:
    users: dict[int, User] = {}
    keys: list[AiKey] = []
    department_a: list[int] = []
    department_b: list[int] = []
    for number in range(1, 1346):
        user = User(
            id=number,
            username=f"qa_publish_20260909_{number:04d}",
            email=f"publish-{number}@example.invalid",
            is_active=not 1321 <= number <= 1340,
            is_admin=number > 1343,
        )
        users[number] = user
        keys.append(
            AiKey(
                id=number,
                name=f"测试主 Key {number}",
                owner_type="user",
                owner_id=number,
                key_type="personal_main",
                models=[OTHER_MODEL],
                is_active=not 1301 <= number <= 1320,
                litellm_key_id=f"sk-qa-fake-publish-{number:04d}",
                litellm_key_alias="duplicate-test-alias" if number % 2 else None,
            )
        )
        if number <= 700 or 1301 <= number <= 1320 or 1341 <= number <= 1343:
            department_a.append(number)
        if 701 <= number <= 1300 or 1321 <= number <= 1343:
            department_b.append(number)
    _append_out_of_scope_keys(keys)
    return Population(users, keys, department_a, department_b)


def _append_out_of_scope_keys(keys: list[AiKey]) -> None:
    for number, (key_type, owner_type) in enumerate(
        [
            ("dept_main", "department"),
            ("project_main", "project"),
            ("personal_scene", "user"),
        ],
        start=1346,
    ):
        keys.append(
            AiKey(
                id=number,
                name=f"测试范围外 Key {number}",
                owner_id=1,
                owner_type=owner_type,
                key_type=key_type,
                is_active=True,
                models=[OTHER_MODEL],
                litellm_key_id=f"sk-qa-fake-extra-{number}",
            )
        )


def token_hash(key: AiKey) -> str:
    assert key.litellm_key_id is not None
    return sha256(key.litellm_key_id.encode()).hexdigest()


@dataclass
class PublicationCase:
    population: Population
    litellm_models: dict[str, set[str]]
    session: AsyncMock

    def ordinary_keys(self) -> list[AiKey]:
        return [key for key in self.population.keys if key.id <= 1343]

    def holders(self) -> set[int]:
        return {key.id for key in self.ordinary_keys() if MODEL_NAME in key.models}

    async def publish(self, user_ids: list[int] | None) -> int:
        return await ai_key_service.sync_model_access_to_personal_main_keys(
            self.session,
            MODEL_NAME,
            user_ids,
        )

    async def find_keys(
        self,
        session: AsyncMock,
        user_ids: list[int] | None = None,
        include_inactive: bool = False,
    ) -> list[AiKey]:
        return [
            key
            for key in self.ordinary_keys()
            if (user_ids is None or key.owner_id in user_ids)
            and (
                include_inactive
                or (key.is_active and self.population.users[key.owner_id].is_active)
            )
        ]


@pytest.fixture
def publication_case(monkeypatch: pytest.MonkeyPatch) -> PublicationCase:
    population = make_population()
    case = PublicationCase(
        population,
        {token_hash(key): set(key.models) for key in population.keys},
        AsyncMock(),
    )

    async def update_remote(
        session: AsyncMock,
        model_id: str | list[str],
        add_tokens: list[str],
        remove_tokens: list[str],
        remove_model_ids: list[str] | None = None,
    ) -> None:
        model_ids = [model_id] if isinstance(model_id, str) else model_id
        for token in add_tokens:
            if token in case.litellm_models:
                case.litellm_models[token].discard("no-default-models")
                case.litellm_models[token].update(model_ids)
        for token in remove_tokens:
            if token in case.litellm_models:
                case.litellm_models[token].difference_update(remove_model_ids or model_ids)
                if not case.litellm_models[token]:
                    case.litellm_models[token].add("no-default-models")

    async def read_remote(session: AsyncMock, tokens: list[str]) -> dict[str, set[str]]:
        return {
            token: set(case.litellm_models[token])
            for token in tokens
            if token in case.litellm_models
        }

    monkeypatch.setattr(
        ai_key_repo, "find_personal_main_keys_for_model_sync", case.find_keys
    )
    monkeypatch.setattr(ai_key_repo, "sync_litellm_model_access", update_remote)
    monkeypatch.setattr(ai_key_repo, "get_litellm_model_access", read_remote)
    monkeypatch.setattr(
        model_repo, "find_model_ids_with_anthropic_deployments", AsyncMock(return_value=set())
    )
    monkeypatch.setattr(
        ai_key_service,
        "_sync_key_to_litellm",
        AsyncMock(side_effect=AssertionError("模型发布不能逐 Key 调用 LiteLLM HTTP")),
    )
    return case


@pytest.mark.asyncio
async def test_publish_all_grants_1303_enabled_members(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    changed = await case.publish(None)
    assert changed == 1303
    assert len(case.holders()) == 1303
    assert all(MODEL_NAME not in key.models for key in case.population.keys[1300:1340])
    assert all(OTHER_MODEL in key.models for key in case.population.keys)


@pytest.mark.asyncio
async def test_publish_a_only_grants_703_members(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    await case.publish(case.population.department_a)
    assert case.holders() == set(range(1, 701)) | {1341, 1342, 1343}


@pytest.mark.asyncio
async def test_expand_a_to_ab_grants_600_additional_members(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    await case.publish(case.population.department_a)
    changed = await case.publish(None)
    assert changed == 600
    assert len(case.holders()) == 1303
    assert all(key.models.count(MODEL_NAME) <= 1 for key in case.population.keys)


@pytest.mark.asyncio
async def test_shrink_ab_to_a_revokes_600_b_only_members(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    await case.publish(None)
    changed = await case.publish(case.population.department_a)
    assert changed == 600
    assert case.holders() == set(range(1, 701)) | {1341, 1342, 1343}


@pytest.mark.asyncio
async def test_unpublish_revokes_1343_but_preserves_admins_and_other_keys(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    for key in case.population.keys:
        key.models = [OTHER_MODEL, MODEL_NAME]
        case.litellm_models[token_hash(key)].add(MODEL_NAME)
    changed = await case.publish([])
    assert changed == 1343
    assert case.holders() == set()
    for key in case.ordinary_keys():
        assert MODEL_NAME not in case.litellm_models[token_hash(key)]
    for key in case.population.keys[1343:]:
        assert MODEL_NAME in key.models
        assert MODEL_NAME in case.litellm_models[token_hash(key)]


@pytest.mark.asyncio
async def test_disabled_key_reenabled_after_unpublish_has_no_old_grant(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    key = case.population.keys[1300]
    key.models = [OTHER_MODEL, MODEL_NAME]
    case.litellm_models[token_hash(key)].add(MODEL_NAME)
    await case.publish([])
    key.is_active = True
    assert MODEL_NAME not in key.models
    assert MODEL_NAME not in case.litellm_models[token_hash(key)]


@pytest.mark.asyncio
async def test_repeated_publish_and_unpublish_are_idempotent(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    await case.publish(None)
    assert await case.publish(None) == 0
    await case.publish([])
    assert await case.publish([]) == 0
    assert case.holders() == set()


@pytest.mark.asyncio
async def test_remote_drift_repaired_when_platform_already_revoked(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    token = token_hash(case.population.keys[0])
    case.litellm_models[token].add(MODEL_NAME)
    assert await case.publish([]) == 0
    assert MODEL_NAME not in case.litellm_models[token]


@pytest.mark.asyncio
async def test_duplicate_or_missing_alias_does_not_affect_token_matching(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    await case.publish(case.population.department_a)
    for key in case.ordinary_keys():
        assert (MODEL_NAME in key.models) == (
            MODEL_NAME in case.litellm_models[token_hash(key)]
        )


@pytest.mark.asyncio
async def test_missing_platform_token_reports_error_without_commit(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    case.population.keys[0].litellm_key_id = None
    with pytest.raises(ConflictError, match="缺少 LiteLLM token"):
        await case.publish(None)
    case.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_remote_key_reports_error_without_commit(
    publication_case: PublicationCase,
) -> None:
    case = publication_case
    case.litellm_models.pop(token_hash(case.population.keys[0]))
    with pytest.raises(ConflictError, match="同步不完整"):
        await case.publish(None)
    case.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_uses_selected_department_members(
    publication_case: PublicationCase, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = publication_case
    model = Model(
        id=1,
        model_id=MODEL_NAME,
        is_published=True,
        visibility_type="selected",
        requires_approval=False,
    )
    monkeypatch.setattr(
        model_repo,
        "find_user_visibility_by_model",
        AsyncMock(
            return_value=[
                ModelUserVisibility(user_id=uid) for uid in case.population.department_a
            ]
        ),
    )
    await model_service._sync_published_model_to_main_keys(case.session, model)
    assert len(case.holders()) == 703


def test_invalidated_approval_has_user_facing_chinese_label() -> None:
    assert (
        resource_application_service.ApplicationStatus.label_for("invalidated")
        == "已失效"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("population_size", [1, 50, 100, 101])
async def test_small_publication_also_uses_bulk_path(
    publication_case: PublicationCase, population_size: int
) -> None:
    case = publication_case
    case.population.keys = case.population.keys[:population_size]
    assert await case.publish(None) == population_size
    assert len(case.holders()) == population_size


@pytest.mark.asyncio
async def test_identity_single_key_grant_keeps_litellm_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = make_population().keys[0]
    key.rate_limit_mode = "none"
    monkeypatch.setattr(ai_key_repo, "find_by_id", AsyncMock(return_value=key))
    monkeypatch.setattr(
        model_repo,
        "find_model_ids_with_anthropic_deployments",
        AsyncMock(return_value=set()),
    )
    api_update = AsyncMock()
    sql_update = AsyncMock()
    monkeypatch.setattr(ai_key_service.litellm_client, "update_key", api_update)
    monkeypatch.setattr(ai_key_repo, "sync_litellm_model_access", sql_update)
    await ai_key_service.update_key_resources(
        AsyncMock(), key.id, models=[OTHER_MODEL, MODEL_NAME]
    )
    api_update.assert_awaited_once()
    assert api_update.call_args.kwargs["models"] == [OTHER_MODEL, MODEL_NAME]
    sql_update.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["save_publish_settings", "deployment_sync"])
async def test_approved_grants_survive_published_model_changes(
    publication_case: PublicationCase,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    case = publication_case
    approved_ids = [1, 2, 701]
    await case.publish(approved_ids)
    model = Model(
        id=7,
        model_id=MODEL_NAME,
        is_published=True,
        requires_approval=True,
        visibility_type="all",
    )
    monkeypatch.setattr(
        resource_application_repo,
        "find_approved_user_ids_for_resource",
        AsyncMock(return_value=approved_ids),
    )
    invalidate = AsyncMock()
    monkeypatch.setattr(
        resource_application_repo, "invalidate_approved_for_resource", invalidate
    )
    if operation == "save_publish_settings":
        monkeypatch.setattr(model_repo, "find_by_id", AsyncMock(return_value=model))
        monkeypatch.setattr(
            model_service, "get_model_visibility", AsyncMock(return_value={})
        )
        await model_service.update_model_publish(
            case.session, model.id, requires_approval=True
        )
    else:
        await model_service._sync_model_key_access_after_deployment(case.session, model)
    assert case.holders() == set(approved_ids)
    for key in case.ordinary_keys():
        assert (MODEL_NAME in case.litellm_models[token_hash(key)]) == (
            key.id in approved_ids
        )
    invalidate.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabling_approval_keeps_approved_users_and_removes_public_grants(
    publication_case: PublicationCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = publication_case
    await case.publish(None)
    model = Model(
        id=7,
        model_id=MODEL_NAME,
        is_published=True,
        requires_approval=True,
        visibility_type="selected",
    )
    monkeypatch.setattr(
        resource_application_repo,
        "find_approved_user_ids_for_resource",
        AsyncMock(return_value=[1, 701]),
    )
    await model_service._sync_published_model_to_main_keys(case.session, model)
    assert case.holders() == {1, 701}


@pytest.mark.asyncio
async def test_unpublish_approval_model_revokes_grants_and_invalidates_applications(
    publication_case: PublicationCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = publication_case
    await case.publish([1, 701])
    model = Model(
        id=7,
        model_id=MODEL_NAME,
        is_published=True,
        requires_approval=True,
        visibility_type="all",
    )
    approved_lookup = AsyncMock(return_value=[1, 701])
    invalidate = AsyncMock(return_value=2)
    monkeypatch.setattr(
        resource_application_repo,
        "find_approved_user_ids_for_resource",
        approved_lookup,
    )
    monkeypatch.setattr(
        resource_application_repo, "invalidate_approved_for_resource", invalidate
    )
    monkeypatch.setattr(model_repo, "find_by_id", AsyncMock(return_value=model))
    monkeypatch.setattr(
        model_service, "get_model_visibility", AsyncMock(return_value={})
    )
    await model_service.update_model_publish(case.session, model.id, is_published=False)
    assert case.holders() == set()
    assert model.is_published is False
    invalidate.assert_awaited_once()
    assert invalidate.call_args.args[1:3] == ("model", model.id)
    approved_lookup.assert_not_awaited()
    case.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unpublish_removes_historical_anthropic_alias(publication_case):
    case = publication_case
    key = case.population.keys[0]
    key.models = [MODEL_NAME]
    alias = f"{MODEL_NAME}(Anthropic)"
    case.litellm_models[token_hash(key)] = {MODEL_NAME, alias}
    await case.publish([])
    assert key.models == []
    assert case.litellm_models[token_hash(key)] == {"no-default-models"}
    await case.publish([key.owner_id])
    assert case.litellm_models[token_hash(key)] == {MODEL_NAME}


@pytest.mark.asyncio
async def test_publish_grants_both_anthropic_routes(publication_case, monkeypatch):
    case = publication_case
    monkeypatch.setattr(model_repo, "find_model_ids_with_anthropic_deployments", AsyncMock(return_value={MODEL_NAME}))
    await case.publish([1])
    assert case.litellm_models[token_hash(case.population.keys[0])] == {
        OTHER_MODEL, MODEL_NAME, f"{MODEL_NAME}(Anthropic)"
    }
    await case.publish([])
    assert case.litellm_models[token_hash(case.population.keys[0])] == {OTHER_MODEL}


@pytest.mark.asyncio
async def test_final_state_rejects_unrestricted_remote_key(publication_case, monkeypatch):
    case = publication_case
    monkeypatch.setattr(ai_key_repo, "sync_litellm_model_access", AsyncMock())
    case.litellm_models[token_hash(case.population.keys[0])] = set()
    with pytest.raises(ConflictError, match="不受限"):
        await case.publish([])


@pytest.mark.asyncio
async def test_sql_revokes_historical_alias_without_active_deployment():
    session = AsyncMock()
    await ai_key_repo.sync_litellm_model_access(
        session, [MODEL_NAME], [], ["test-token"],
        remove_model_ids=[MODEL_NAME, f"{MODEL_NAME}(Anthropic)"],
    )
    assert {call.args[1]["model_id"] for call in session.execute.await_args_list} == {
        MODEL_NAME, f"{MODEL_NAME}(Anthropic)"
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("models,expected", [([], ["no-default-models"]), (["model-a"], ["model-a"])])
async def test_empty_models_are_deny_all_on_create_and_update(monkeypatch, models, expected):
    client = ai_key_service.litellm_client
    request = AsyncMock(return_value={})
    monkeypatch.setattr(client, "_request", request)
    await client.create_key(key_alias="test", models=models)
    assert request.call_args.kwargs["json_data"]["models"] == expected
    await client.update_key("sk-test", models=models)
    assert request.call_args.kwargs["json_data"]["models"] == expected


@pytest.mark.asyncio
async def test_default_create_denies_models_but_omitted_update_preserves(monkeypatch):
    client = ai_key_service.litellm_client
    request = AsyncMock(return_value={})
    monkeypatch.setattr(client, "_request", request)
    await client.create_key(key_alias="empty-test")
    assert request.call_args.kwargs["json_data"]["models"] == ["no-default-models"]
    await client.update_key("sk-test")
    assert "models" not in request.call_args.kwargs["json_data"]


@pytest.mark.asyncio
async def test_republish_without_departments_refreshes_saved_members(monkeypatch):
    from types import SimpleNamespace
    from repositories import department_repo
    model = Model(id=9, model_id=MODEL_NAME, is_published=False, visibility_type='selected', requires_approval=False)
    monkeypatch.setattr(model_repo, 'find_by_id', AsyncMock(return_value=model))
    monkeypatch.setattr(model_repo, 'find_visibility_by_model', AsyncMock(return_value=[SimpleNamespace(department_id=2)]))
    monkeypatch.setattr(department_repo, 'find_members', AsyncMock(return_value=[(SimpleNamespace(id=77), None)]))
    visibility = AsyncMock()
    monkeypatch.setattr(model_repo, 'set_visibility_users', visibility)
    monkeypatch.setattr(model_service, '_sync_published_model_to_main_keys', AsyncMock())
    monkeypatch.setattr(model_service, 'get_model_visibility', AsyncMock(return_value={}))
    session = AsyncMock()
    await model_service.update_model_publish(session, model.id, is_published=True)
    visibility.assert_awaited_once_with(session, model.id, [77])
