"""Structured chat through any OpenAI-compatible HTTP endpoint."""

import asyncio
import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.llm.types import (
    ChatMessage,
    LLMProviderError,
    LLMUsage,
    ResponseModelT,
    StructuredLLMResult,
)

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
logger = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    """Call local Ollama or a configured cloud-compatible endpoint."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._provider = settings.llm_provider
        self._model = settings.llm_model
        self._structured_mode = settings.llm_structured_mode
        self._max_retries = settings.llm_max_retries
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        api_key = settings.llm_api_key.get_secret_value()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.AsyncClient(
            base_url=f"{settings.llm_base_url.rstrip('/')}/",
            headers=headers,
            timeout=httpx.Timeout(settings.llm_timeout_seconds),
        )

    async def generate_structured(
        self,
        *,
        messages: tuple[ChatMessage, ...],
        response_model: type[ResponseModelT],
    ) -> StructuredLLMResult[ResponseModelT]:
        """Request deterministic JSON and reject responses outside the schema."""

        payload = self._build_payload(
            messages=messages,
            response_model=response_model,
        )
        response = await self._post_with_retry(payload)
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise TypeError("Assistant content is empty or not text.")
            value = response_model.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise LLMProviderError(
                code="LLM_INVALID_RESPONSE",
                message="The language model returned invalid structured output.",
                retryable=False,
            ) from exc

        usage_data = body.get("usage", {})
        return StructuredLLMResult(
            value=value,
            provider=self._provider,
            model=self._model,
            usage=LLMUsage(
                prompt_tokens=self._optional_int(
                    usage_data.get("prompt_tokens")
                ),
                completion_tokens=self._optional_int(
                    usage_data.get("completion_tokens")
                ),
                total_tokens=self._optional_int(usage_data.get("total_tokens")),
            ),
        )

    async def close(self) -> None:
        """Close the shared asynchronous HTTP client."""

        await self._client.aclose()

    def _build_payload(
        self,
        *,
        messages: tuple[ChatMessage, ...],
        response_model: type[BaseModel],
    ) -> dict[str, object]:
        """Build one request while keeping provider quirks configurable."""

        request_messages = [
            {"role": message.role, "content": message.content}
            for message in messages
        ]
        schema = response_model.model_json_schema()
        provider_schema = (
            self._ollama_compatible_schema(schema)
            if self._provider == "ollama"
            else schema
        )
        if self._structured_mode == "prompt_only":
            request_messages.append(
                {
                    "role": "system",
                    "content": (
                        "Return only JSON matching this schema: "
                        f"{provider_schema}"
                    ),
                }
            )
        payload: dict[str, object] = {
            "model": self._model,
            "messages": request_messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
            "stream": False,
        }
        response_format = self._response_format(
            mode=self._structured_mode,
            response_model=response_model,
            schema=provider_schema,
        )
        if response_format is not None:
            payload["response_format"] = response_format
        return payload

    async def _post_with_retry(
        self,
        payload: dict[str, object],
    ) -> httpx.Response:
        """Retry only transport and explicitly transient HTTP failures."""

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    "chat/completions",
                    json=payload,
                )
                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response
                last_error = httpx.HTTPStatusError(
                    "Transient language-model HTTP status.",
                    request=response.request,
                    response=response,
                )
            except httpx.TransportError as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "language_model_request_rejected status_code=%s response=%s",
                    exc.response.status_code,
                    exc.response.text[:1000],
                )
                raise LLMProviderError(
                    code="LLM_REQUEST_REJECTED",
                    message=(
                        "The language-model endpoint rejected the request "
                        f"with HTTP {exc.response.status_code}."
                    ),
                    retryable=False,
                ) from exc

            if attempt < self._max_retries:
                await asyncio.sleep(min(0.25 * (2**attempt), 2.0))

        raise LLMProviderError(
            code="LLM_TEMPORARILY_UNAVAILABLE",
            message="The language-model endpoint is temporarily unavailable.",
            retryable=True,
        ) from last_error

    @staticmethod
    def _response_format(
        *,
        mode: Literal["json_schema", "json_object", "prompt_only"],
        response_model: type[BaseModel],
        schema: dict[str, Any],
    ) -> dict[str, object] | None:
        """Select the structured-output dialect supported by a deployment."""

        if mode == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": schema,
                },
            }
        if mode == "json_object":
            return {"type": "json_object"}
        return None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        """Keep missing usage fields optional and reject booleans."""

        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return None

    @classmethod
    def _ollama_compatible_schema(cls, value: Any) -> Any:
        """Remove string-length keywords unsupported by Ollama's grammar parser.

        Pydantic still validates the model response against the original schema.
        """

        if isinstance(value, dict):
            return {
                key: cls._ollama_compatible_schema(item)
                for key, item in value.items()
                if key not in {"minLength", "maxLength"}
            }
        if isinstance(value, list):
            return [cls._ollama_compatible_schema(item) for item in value]
        return value
