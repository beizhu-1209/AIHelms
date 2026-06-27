from sqlalchemy.ext.asyncio import AsyncSession

from models.db import AiKey, Model, ModelDeployment
from repositories import ai_key_repo, model_repo
from services import ai_key_service
from services.access_test_error_mapper import build_error_detail


async def resolve_test_identity(session: AsyncSession, user_id: int) -> AiKey | None:
    key = await ai_key_repo.find_personal_main(session, user_id)
    if not key or not key.is_active or not key.litellm_key_id:
        return None
    return key


async def precheck_access_test(
    session: AsyncSession,
    user_id: int,
    model: Model | None,
    test_model: str,
    is_admin: bool,
) -> tuple[AiKey | None, dict[str, object] | None]:
    key = await resolve_test_identity(session, user_id)
    if not key:
        return None, build_error_detail("no_identity")

    if not model:
        return key, None

    if is_admin:
        if not model.is_active:
            return key, build_error_detail("no_active_deployment")

        deployments = await model_repo.find_deployments_by_model(session, model.id)
        if not any(_deployment_available(deployment) for deployment in deployments):
            return key, build_error_detail("no_active_deployment")

        await _ensure_admin_authorized(session, key, model)
        return key, None

    if not _model_authorized(key, test_model):
        return key, build_error_detail("model_not_authorized")

    if not model.is_active or not model.is_published:
        return key, build_error_detail("model_not_published")

    deployments = await model_repo.find_deployments_by_model(session, model.id)
    if not any(_deployment_available(deployment) for deployment in deployments):
        return key, build_error_detail("no_active_deployment")

    return key, None


async def _ensure_admin_authorized(
    session: AsyncSession,
    key: AiKey,
    model: Model,
) -> None:
    existing = key.models or []
    if "*" in existing or model.model_id in existing:
        return

    await ai_key_service.update_key(
        session,
        key_id=key.id,
        models=[*existing, model.model_id],
        update_rate_limit=False,
    )


def _model_authorized(key: AiKey, model_id: str) -> bool:
    model_ids = key.models or []
    return "*" in model_ids or model_id in model_ids


def _deployment_available(deployment: ModelDeployment) -> bool:
    credential = deployment.credential
    return deployment.is_active and (credential is None or credential.is_active)
