"""Tests for the OpenAI-compatible structured language-model provider."""

import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.llm import (
    ChatMessage,
    LLMProviderError,
    OpenAICompatibleProvider,
)


class ExampleOutput(BaseModel):
    """Small schema used to verify request and response handling."""

    summary: str
    count: int


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "llm_enabled": True,
        "llm_base_url": "http://llm.test/v1",
        "llm_api_key": "test-secret",
        "llm_model": "test-model",
        "llm_max_retries": 0,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


async def test_provider_sends_schema_and_validates_result() -> None:
    """Provider-specific JSON must become one validated project result."""

    seen_request: httpx.Request | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"ok","count":2}'
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                    "total_tokens": 18,
                },
            },
        )

    client = httpx.AsyncClient(
        base_url="http://llm.test/v1/",
        transport=httpx.MockTransport(handler),
    )
    provider = OpenAICompatibleProvider(_settings(), client=client)
    result = await provider.generate_structured(
        messages=(ChatMessage(role="user", content="Create a result."),),
        response_model=ExampleOutput,
    )
    await provider.close()

    assert result.value == ExampleOutput(summary="ok", count=2)
    assert result.usage.total_tokens == 18
    assert seen_request is not None
    payload = json.loads(seen_request.content)
    assert payload["model"] == "test-model"
    assert payload["response_format"]["type"] == "json_schema"
    assert (
        payload["response_format"]["json_schema"]["schema"]["properties"]
        == ExampleOutput.model_json_schema()["properties"]
    )


async def test_provider_retries_transient_status() -> None:
    """A temporary server error may be retried without changing providers."""

    attempts = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"summary":"ok","count":1}'}}
                ]
            },
        )

    client = httpx.AsyncClient(
        base_url="http://llm.test/v1/",
        transport=httpx.MockTransport(handler),
    )
    provider = OpenAICompatibleProvider(
        _settings(llm_max_retries=1),
        client=client,
    )

    result = await provider.generate_structured(
        messages=(ChatMessage(role="user", content="Create a result."),),
        response_model=ExampleOutput,
    )
    await provider.close()

    assert result.value.count == 1
    assert attempts == 2


async def test_provider_rejects_schema_invalid_content() -> None:
    """A successful HTTP response is not success until Pydantic accepts it."""

    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"summary":"missing"}'}}]},
        )

    client = httpx.AsyncClient(
        base_url="http://llm.test/v1/",
        transport=httpx.MockTransport(handler),
    )
    provider = OpenAICompatibleProvider(_settings(), client=client)

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_structured(
            messages=(ChatMessage(role="user", content="Create a result."),),
            response_model=ExampleOutput,
        )
    await provider.close()

    assert exc_info.value.code == "LLM_INVALID_RESPONSE"
    assert exc_info.value.retryable is False
