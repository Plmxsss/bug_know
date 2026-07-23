"""Routes for inspecting entity-filtered RAG retrieval."""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import Settings
from app.core.exceptions import AppError
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.schemas import (
    KnowledgeSearchHitResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services import KnowledgeSearchService

router = APIRouter(prefix="/knowledge", tags=["knowledge retrieval"])


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    summary="Test entity-filtered semantic retrieval",
)
async def search_knowledge(
    request: Request,
    body: KnowledgeSearchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeSearchResponse:
    """Search indexed chunks without asking an LLM to generate an answer."""

    settings = cast(Settings, request.app.state.settings)
    embedder = cast(TextEmbedder | None, request.app.state.embedder)
    if embedder is None:
        raise AppError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="EMBEDDING_MODEL_DISABLED",
            message="The embedding model is not enabled on this API instance.",
        )
    vector_database = cast(
        VectorDatabaseGateway,
        request.app.state.vector_database,
    )
    result = await KnowledgeSearchService(
        session=session,
        settings=settings,
        embedder=embedder,
        vector_database=vector_database,
    ).search(
        entity_id=body.entity_id,
        query=body.query,
        top_k=body.top_k,
    )
    return KnowledgeSearchResponse(
        entity_id=result.entity_id,
        common_name=result.common_name,
        knowledge_status=result.knowledge_status,
        hits=[
            KnowledgeSearchHitResponse(
                point_id=hit.point_id,
                score=hit.score,
                document_id=hit.document_id,
                heading=hit.heading,
                locator=hit.locator,
                content=hit.content,
                title=hit.title,
                source_organization=hit.source_organization,
                source_url=hit.source_url,
                publication_date=hit.publication_date,
                region=hit.region,
            )
            for hit in result.hits
        ],
    )
