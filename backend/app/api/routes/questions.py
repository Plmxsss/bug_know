"""Task-scoped agricultural follow-up questions using a bounded Agent."""

from hashlib import sha256
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Request, status
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.cache import RedisGateway
from app.core.config import Settings
from app.core.exceptions import AppError
from app.llm import LLMProvider
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.schemas import KnowledgeQuestionRequest, KnowledgeQuestionResponse
from app.services import FixedWindowRateLimiter, KnowledgeQuestionService
from app.services.knowledge_question import QueryPlanner

router = APIRouter(prefix="/detections", tags=["knowledge questions"])


@router.post(
    "/{task_id}/questions",
    response_model=KnowledgeQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a bounded Agent question about one detection task",
)
async def ask_detection_question(
    request: Request,
    task_id: Annotated[int, Path(ge=1)],
    payload: KnowledgeQuestionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeQuestionResponse:
    """Use Agent-planned retrieval but discard the Agent's free-form answer."""

    settings = cast(Settings, request.app.state.settings)
    embedder = cast(TextEmbedder | None, request.app.state.embedder)
    llm_provider = cast(LLMProvider | None, request.app.state.llm_provider)
    if not settings.agent_enabled:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AGENT_DISABLED",
            message="The bounded LangChain Agent is not enabled.",
        )

    client_host = request.client.host if request.client is not None else "unknown"
    client_digest = sha256(client_host.encode("utf-8")).hexdigest()[:24]
    rate_limit = await FixedWindowRateLimiter(
        cast(RedisGateway, request.app.state.redis)
    ).check(
        key=f"rate:agent-question:{task_id}:{client_digest}",
        limit=settings.agent_rate_limit_requests,
        window_seconds=settings.agent_rate_limit_window_seconds,
    )
    if not rate_limit.allowed:
        raise AppError(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="AGENT_RATE_LIMITED",
            message="Too many Agent questions for this task. Try again later.",
            details={
                "limit": rate_limit.limit,
                "window_seconds": rate_limit.window_seconds,
            },
        )
    if embedder is None:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="EMBEDDING_MODEL_DISABLED",
            message="The embedding model is not enabled.",
        )
    if llm_provider is None:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_PROVIDER_DISABLED",
            message="The language-model provider is not enabled.",
        )

    try:
        from langchain_openai import ChatOpenAI

        from app.agent import QueryPlanningAgent
    except ImportError as exc:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="AGENT_DEPENDENCIES_MISSING",
            message="Install the backend agent optional dependencies.",
        ) from exc

    api_key = (
        settings.llm_api_key
        if settings.llm_api_key.get_secret_value()
        else SecretStr("ollama-local")
    )
    planner = QueryPlanningAgent(
        ChatOpenAI(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=api_key,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    )
    result = await KnowledgeQuestionService(
        session=session,
        settings=settings,
        vector_database=cast(
            VectorDatabaseGateway,
            request.app.state.vector_database,
        ),
        embedder=embedder,
        llm_provider=llm_provider,
        query_planner=cast(QueryPlanner, planner),
    ).answer(task_id=task_id, question=payload.question)
    return KnowledgeQuestionResponse(
        task_id=result.task_id,
        question=result.question,
        planned_queries=list(result.planned_queries),
        answer=result.answer,
        uncertainty=result.uncertainty,
        references=list(result.references),
    )
