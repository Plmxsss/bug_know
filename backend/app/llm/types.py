"""Provider-independent language-model request and result types."""

from dataclasses import dataclass
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import BaseModel

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One text message in a provider-neutral chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LLMUsage:
    """Optional provider-reported token counts."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True, slots=True)
class StructuredLLMResult(Generic[ResponseModelT]):
    """Validated structured content plus reproducibility metadata."""

    value: ResponseModelT
    provider: str
    model: str
    usage: LLMUsage


class LLMProviderError(RuntimeError):
    """A classified provider failure safe for service-level handling."""

    def __init__(self, *, code: str, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class LLMProvider(Protocol):
    """Behavior required by diagnosis code regardless of model host."""

    async def generate_structured(
        self,
        *,
        messages: tuple[ChatMessage, ...],
        response_model: type[ResponseModelT],
    ) -> StructuredLLMResult[ResponseModelT]:
        """Generate JSON and validate it against a Pydantic model."""

    async def close(self) -> None:
        """Release network resources owned by the provider."""
