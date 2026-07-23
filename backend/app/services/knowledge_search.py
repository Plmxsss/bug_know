"""Retrieve entity-filtered, citation-backed knowledge chunks."""

from dataclasses import dataclass
from datetime import date

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.exceptions import AppError
from app.rag.embeddings import TextEmbedder
from app.rag.vector_database import VectorDatabaseGateway
from app.repositories.knowledge_search import (
    KnowledgeSearchRepository,
    KnowledgeStatus,
)


@dataclass(frozen=True, slots=True)
class RetrievedKnowledge:
    """One vector-ranked chunk backed by an indexed MySQL source."""

    point_id: str
    score: float
    document_id: int
    heading: str | None
    locator: str
    content: str
    title: str
    source_organization: str
    source_url: str | None
    publication_date: date | None
    region: str | None


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResult:
    """Entity scope plus its trustworthy search candidates."""

    entity_id: int
    common_name: str
    knowledge_status: KnowledgeStatus
    hits: tuple[RetrievedKnowledge, ...]


class KnowledgeSearchService:
    """Embed a query, enforce entity filtering, and reconstruct citations."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        embedder: TextEmbedder,
        vector_database: VectorDatabaseGateway,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._vector_database = vector_database
        self._repository = KnowledgeSearchRepository(session)

    async def search(
        self,
        *,
        entity_id: int,
        query: str,
        top_k: int,
    ) -> KnowledgeSearchResult:
        """Return only MySQL-validated hits for one existing entity."""

        scope = await self._repository.get_scope(entity_id)
        if scope is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code="PEST_ENTITY_NOT_FOUND",
                message=f"Pest entity {entity_id} does not exist.",
            )
        if scope.knowledge_status == "missing":
            return KnowledgeSearchResult(
                entity_id=scope.id,
                common_name=scope.common_name,
                knowledge_status=scope.knowledge_status,
                hits=(),
            )

        query_vector = await run_in_threadpool(
            self._embedder.embed_query,
            query,
        )
        candidates = await self._vector_database.search_by_entity(
            collection_name=self._settings.qdrant_collection,
            query_vector=query_vector,
            pest_entity_id=entity_id,
            limit=top_k,
        )
        chunks = await self._repository.get_chunks_by_point_ids(
            entity_id=entity_id,
            point_ids=[candidate.point_id for candidate in candidates],
        )
        hits = tuple(
            RetrievedKnowledge(
                point_id=candidate.point_id,
                score=candidate.score,
                document_id=chunk.document_id,
                heading=chunk.heading,
                locator=chunk.locator,
                content=chunk.content,
                title=chunk.title,
                source_organization=chunk.source_organization,
                source_url=chunk.source_url,
                publication_date=chunk.publication_date,
                region=chunk.region,
            )
            for candidate in candidates
            if (chunk := chunks.get(candidate.point_id)) is not None
        )
        return KnowledgeSearchResult(
            entity_id=scope.id,
            common_name=scope.common_name,
            knowledge_status=scope.knowledge_status,
            hits=hits,
        )
