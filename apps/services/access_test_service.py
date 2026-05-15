import logging
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.litellm_master_key,
        base_url=f"{settings.litellm_url}/v1",
    )


async def test_model_stream(
    model: str,
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream chat completion from LiteLLM, yield SSE-formatted chunks."""
    client = _get_client()
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield f"data: {content}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error("access test stream error: %s", str(e))
        yield f"data: [ERROR] {str(e)}\n\n"


async def test_model_sync(
    model: str,
    messages: list[dict],
) -> dict:
    """Non-streaming chat completion from LiteLLM."""
    client = _get_client()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
        )
        content = response.choices[0].message.content if response.choices else ""
        return {
            "success": True,
            "content": content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }
    except Exception as e:
        logger.error("access test sync error: %s", str(e))
        return {
            "success": False,
            "content": "",
            "error": str(e),
        }
