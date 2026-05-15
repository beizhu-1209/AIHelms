import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

LITELLM_TIMEOUT = 10.0


async def _request(
    method: str,
    path: str,
    json_data: dict | None = None,
    params: dict | None = None,
) -> dict:
    url = f"{settings.litellm_url}{path}"
    headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
    try:
        async with httpx.AsyncClient(timeout=LITELLM_TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
            )
            if response.status_code >= 400:
                logger.error(
                    "litellm request failed",
                    extra={
                        "method": method,
                        "path": path,
                        "status": response.status_code,
                        "body": response.text,
                    },
                )
                raise LiteLLMError(
                    f"LiteLLM {method} {path} failed: {response.status_code}"
                )
            return response.json()
    except httpx.HTTPError as e:
        logger.error("litellm connection error: %s %s - %s", method, path, str(e))
        raise LiteLLMError(f"LiteLLM {method} {path} connection error: {e}") from e


class LiteLLMError(Exception):
    pass


async def create_user(user_id: str, user_email: str) -> dict:
    data = {
        "user_id": user_id,
        "user_email": user_email,
        "user_role": "internal_user",
    }
    return await _request("POST", "/user/new", json_data=data)


async def delete_user(user_id: str) -> None:
    await _request("POST", "/user/delete", json_data={"user_ids": [user_id]})


async def create_team(team_alias: str, metadata: dict | None = None) -> dict:
    data: dict = {"team_alias": team_alias}
    if metadata:
        data["metadata"] = metadata
    return await _request("POST", "/team/new", json_data=data)


async def update_team(team_id: str, team_alias: str) -> dict:
    data = {"team_id": team_id, "team_alias": team_alias}
    return await _request("POST", "/team/update", json_data=data)


async def block_team(team_id: str) -> dict:
    data = {"team_id": team_id, "blocked": True}
    return await _request("POST", "/team/update", json_data=data)


async def unblock_team(team_id: str) -> dict:
    data = {"team_id": team_id, "blocked": False}
    return await _request("POST", "/team/update", json_data=data)


async def delete_team(team_id: str) -> None:
    await _request("POST", "/team/delete", json_data={"team_ids": [team_id]})


async def add_team_member(team_id: str, user_id: str) -> dict:
    data = {
        "team_id": team_id,
        "member": {"role": "user", "user_id": user_id},
    }
    return await _request("POST", "/team/member_add", json_data=data)


async def remove_team_member(team_id: str, user_id: str) -> None:
    data = {"team_id": team_id, "user_id": user_id}
    await _request("POST", "/team/member_delete", json_data=data)


# --- Key Management ---


async def create_key(
    key_alias: str,
    user_id: str | None = None,
    team_id: str | None = None,
    models: list[str] | None = None,
    max_budget: float | None = None,
    metadata: dict | None = None,
    duration: str | None = None,
) -> dict:
    data: dict = {"key_alias": key_alias}
    if user_id:
        data["user_id"] = user_id
    if team_id:
        data["team_id"] = team_id
    if models:
        data["models"] = models
    if max_budget is not None:
        data["max_budget"] = max_budget
    if metadata:
        data["metadata"] = metadata
    if duration:
        data["duration"] = duration
    return await _request("POST", "/key/generate", json_data=data)


async def delete_key(key_id: str) -> None:
    await _request("POST", "/key/delete", json_data={"keys": [key_id]})


async def update_key(
    key_id: str,
    models: list[str] | None = None,
    max_budget: float | None = None,
    metadata: dict | None = None,
    model_max_budget: dict[str, float] | None = None,
) -> dict:
    data: dict = {"key": key_id}
    if models is not None:
        data["models"] = models
    if max_budget is not None:
        data["max_budget"] = max_budget
    if metadata is not None:
        data["metadata"] = metadata
    if model_max_budget is not None:
        data["model_max_budget"] = model_max_budget
    return await _request("POST", "/key/update", json_data=data)


async def update_key_budget(key_id: str, max_budget: float | None) -> dict:
    data: dict = {"key": key_id, "max_budget": max_budget}
    return await _request("POST", "/key/update", json_data=data)


async def get_key_info(key_id: str) -> dict:
    return await _request("GET", "/key/info", params={"key": key_id})


async def list_models() -> list[dict]:
    result = await _request("GET", "/model/info")
    if isinstance(result, dict) and "data" in result:
        return result["data"]
    if isinstance(result, list):
        return result
    return []


async def add_model(
    model_name: str,
    litellm_params: dict,
    model_info: dict | None = None,
) -> dict:
    data: dict = {
        "model_name": model_name,
        "litellm_params": litellm_params,
    }
    if model_info:
        data["model_info"] = model_info
    return await _request("POST", "/model/new", json_data=data)


async def delete_model(litellm_model_id: str) -> None:
    await _request("POST", "/model/delete", json_data={"id": litellm_model_id})


async def update_model(
    litellm_model_id: str,
    model_name: str,
    litellm_params: dict,
    model_info: dict | None = None,
) -> dict:
    data: dict = {
        "id": litellm_model_id,
        "model_name": model_name,
        "litellm_params": litellm_params,
        "model_info": model_info or {},
    }
    return await _request("POST", "/model/update", json_data=data)


# --- Credential Management ---


async def create_credential(
    credential_name: str,
    credential_values: dict,
    credential_info: dict | None = None,
) -> dict:
    data: dict = {
        "credential_name": credential_name,
        "credential_values": credential_values,
        "credential_info": credential_info or {},
    }
    return await _request("POST", "/credentials", json_data=data)


async def update_credential(
    credential_name: str,
    credential_values: dict | None = None,
    credential_info: dict | None = None,
) -> dict:
    data: dict = {"credential_name": credential_name}
    if credential_values:
        data["credential_values"] = credential_values
    if credential_info:
        data["credential_info"] = credential_info
    return await _request("PATCH", f"/credentials/{credential_name}", json_data=data)


async def delete_credential(credential_name: str) -> None:
    await _request("DELETE", f"/credentials/{credential_name}")


async def list_credentials() -> list[dict]:
    result = await _request("GET", "/credentials")
    if isinstance(result, dict) and "credentials" in result:
        return result["credentials"]
    return []


async def get_provider_fields() -> list[dict]:
    url = f"{settings.litellm_url}/public/providers/fields"
    try:
        async with httpx.AsyncClient(timeout=LITELLM_TIMEOUT) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                logger.error(
                    "litellm get_provider_fields failed: %s", response.status_code
                )
                return []
            return response.json()
    except httpx.HTTPError as e:
        logger.error("litellm get_provider_fields connection error: %s", str(e))
        return []


# --- Router Settings ---


async def get_router_settings() -> dict:
    return await _request("GET", "/router/settings")


async def update_router_settings(settings: dict) -> dict:
    return await _request("POST", "/router/settings", json_data=settings)
