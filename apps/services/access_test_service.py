import json
import logging
from collections.abc import AsyncGenerator

import httpx
from openai import AsyncOpenAI

from core.config import settings
from services.access_test_error_mapper import build_failure, map_error

logger = logging.getLogger(__name__)


def _get_client(api_key: str) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=api_key,
        base_url=f"{settings.litellm_url}/v1",
    )


async def test_error_stream(
    error_detail: dict[str, object],
) -> AsyncGenerator[str, None]:
    yield f"data: [ERROR] {json.dumps(error_detail, ensure_ascii=False)}\n\n"


async def test_model_stream(
    model: str,
    messages: list[dict],
    max_tokens: int = 100,
    api_key: str = "",
) -> AsyncGenerator[str, None]:
    """Stream chat completion from LiteLLM, yield SSE-formatted chunks."""
    client = _get_client(api_key)
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta:
                text = delta.content or ""
                if (
                    not text
                    and hasattr(delta, "reasoning_content")
                    and delta.reasoning_content
                ):
                    text = delta.reasoning_content
                if text:
                    yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error("access test stream error: %s", str(e))
        error_detail = map_error(e)
        yield f"data: [ERROR] {json.dumps(error_detail, ensure_ascii=False)}\n\n"


async def test_model_sync(
    model: str,
    messages: list[dict],
    max_tokens: int = 100,
    api_key: str = "",
) -> dict:
    """Non-streaming chat completion from LiteLLM."""
    client = _get_client(api_key)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            max_tokens=max_tokens,
        )
        msg = response.choices[0].message if response.choices else None
        content = (msg.content if msg else "") or ""
        if (
            not content
            and msg
            and hasattr(msg, "reasoning_content")
            and msg.reasoning_content
        ):
            content = f"[思考] {msg.reasoning_content}"
        return {
            "success": True,
            "content": content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }
    except Exception as e:
        logger.error("access test sync error: %s", str(e))
        result = build_failure(map_error(e))
        result["content"] = ""
        return result


async def test_embedding(model: str, text: str, api_key: str = "") -> dict:
    """Test embedding model via LiteLLM."""
    client = _get_client(api_key)
    try:
        response = await client.embeddings.create(
            model=model,
            input=text,
        )
        embedding = response.data[0].embedding if response.data else []
        return {
            "success": True,
            "dimensions": len(embedding),
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }
    except Exception as e:
        logger.error("embedding test error: %s", str(e))
        return build_failure(map_error(e))


async def test_rerank(
    model: str,
    query: str,
    documents: list[str],
    api_key: str = "",
) -> dict:
    """Test rerank model via LiteLLM /rerank endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30) as http_client:
            response = await http_client.post(
                f"{settings.litellm_url}/rerank",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "query": query,
                    "documents": documents,
                },
            )
            if response.status_code != 200:
                return build_failure(
                    map_error(
                        status_code=response.status_code,
                        response_text=response.text,
                    )
                )
            data = response.json()
            results = data.get("results", [])
            return {
                "success": True,
                "results": [
                    {
                        "index": r.get("index"),
                        "relevance_score": r.get("relevance_score"),
                    }
                    for r in results[:5]
                ],
                "model": model,
            }
    except Exception as e:
        logger.error("rerank test error: %s", str(e))
        return build_failure(map_error(e))
