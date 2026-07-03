import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class AiPoliciesScannerError(Exception):
    pass


async def scan_skill_zip(target: str) -> dict:
    url = f"{settings.ai_policies_scanner_url.rstrip('/')}/scan"
    payload = {"target": target, "output_format": "json"}
    timeout = httpx.Timeout(settings.ai_policies_timeout_seconds + 10)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("AI Policies scanner request failed: %s", exc)
        raise AiPoliciesScannerError("安全审查引擎连接失败") from exc

    if response.status_code >= 400:
        logger.warning(
            "AI Policies scanner returned error: status=%s body=%s",
            response.status_code,
            response.text[:1000],
        )
        raise AiPoliciesScannerError("安全审查引擎执行失败")

    data = response.json()
    if not isinstance(data, dict) or data.get("code") != 200:
        raise AiPoliciesScannerError("安全审查引擎返回格式异常")
    return data
