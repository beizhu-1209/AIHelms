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
