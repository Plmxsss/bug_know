"""Coordinate document parsing, embedding, Qdrant, and MySQL indexing state."""

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import PROJECT_ROOT, Settings
from app.core.exceptions import AppError
from app.models import KnowledgeDocument
from app.rag.chunking import TextChunk, TextChunker
from app.rag.embeddings import TextEmbedder
from app.rag.parsing import DocumentParser
from app.rag.vector_database import VectorDatabaseGateway, VectorPoint
from app.repositories.knowledge_document import (
    KnowledgeDocumentRepository,
    RagChunkInsert,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    """Plain values safe to use after the claim transaction is committed."""

    id: int
    title: str
    source_organization: str
    source_url: str | None
    publication_date: date | None
    region: str | None
    file_path: str
    file_type: str
    checksum_sha256: str
    entity_ids: tuple[int, ...]
    previous_point_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DocumentIndexResult:
    """Counts returned after both storage systems accept the index."""

    document_id: int
    entity_ids: tuple[int, ...]
    chunk_count: int
    point_count: int


class DocumentIndexService:
    """Build one reproducible vector index with explicit failure state."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        embedder: TextEmbedder,
        vector_database: VectorDatabaseGateway,
    ) -> None:
        self._session = session
        self._settings = settings
        self._embedder = embedder
        self._vector_database = vector_database
        self._repository = KnowledgeDocumentRepository(session)
        self._parser = DocumentParser()
        self._chunker = TextChunker(
            chunk_size=settings.rag_chunk_size,
            overlap=settings.rag_chunk_overlap,
        )

    async def index(
        self,
        document_id: int,
        *,
        allow_reindex: bool = False,
    ) -> DocumentIndexResult:
        """Index an eligible document, optionally replacing an existing index."""

        snapshot = await self._claim(
            document_id,
            allow_reindex=allow_reindex,
        )
        try:
            source_path = self._resolve_source_path(snapshot.file_path)
            sections = await run_in_threadpool(
                self._parser.parse,
                source_path,
                file_type=snapshot.file_type,
            )
            chunks = tuple(
                chunk
                for chunk in self._chunker.split(sections)
                if not self._is_provenance_only_heading(chunk.heading)
            )
            if not chunks:
                raise ValueError(
                    "The document contains no indexable knowledge sections."
                )
            vectors = await run_in_threadpool(
                self._embedder.embed_documents,
                [chunk.content for chunk in chunks],
            )
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding count does not match chunk count.")

            points, inserts = self._prepare_points(
                snapshot=snapshot,
                chunks=chunks,
                vectors=vectors,
            )
            await self._vector_database.ensure_collection(
                collection_name=self._settings.qdrant_collection,
                dimension=self._embedder.dimension,
            )
            await self._vector_database.upsert_points(
                collection_name=self._settings.qdrant_collection,
                points=points,
            )
            new_point_ids = {point.point_id for point in points}
            stale_point_ids = sorted(
                set(snapshot.previous_point_ids) - new_point_ids
            )
            await self._vector_database.delete_points(
                collection_name=self._settings.qdrant_collection,
                point_ids=stale_point_ids,
            )
            await self._complete(snapshot, inserts)
            return DocumentIndexResult(
                document_id=snapshot.id,
                entity_ids=snapshot.entity_ids,
                chunk_count=len(chunks),
                point_count=len(points),
            )
        except Exception as exc:
            await self._session.rollback()
            await self._record_failure(snapshot.id, exc)
            raise

    async def _claim(
        self,
        document_id: int,
        *,
        allow_reindex: bool,
    ) -> DocumentSnapshot:
        """Lock and move an eligible document to processing."""

        async with self._session.begin():
            document = await self._repository.get_by_id_for_update(document_id)
            if document is None:
                raise AppError(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code="KNOWLEDGE_DOCUMENT_NOT_FOUND",
                    message=f"Knowledge document {document_id} does not exist.",
                )
            eligible_statuses = {"uploaded", "failed"}
            if allow_reindex:
                eligible_statuses.add("indexed")
            if document.status not in eligible_statuses:
                raise AppError(
                    status_code=status.HTTP_409_CONFLICT,
                    code="DOCUMENT_NOT_INDEXABLE",
                    message=f"Document in status {document.status} cannot be indexed.",
                )
            entity_ids = tuple(await self._repository.list_entity_ids(document.id))
            if not entity_ids:
                raise RuntimeError("Document has no associated pest entities.")
            previous_point_ids = tuple(
                await self._repository.list_chunk_point_ids(document.id)
            )
            snapshot = self._snapshot(
                document,
                entity_ids,
                previous_point_ids,
            )
            document.status = "processing"
            document.error_message = None
            await self._session.flush()
            return snapshot

    def _resolve_source_path(self, relative_path: str) -> Path:
        """Resolve a database storage key without allowing directory escape."""

        storage_root = self._settings.storage_dir
        if not storage_root.is_absolute():
            storage_root = PROJECT_ROOT / storage_root
        storage_root = storage_root.resolve()
        source_path = (storage_root / relative_path).resolve()
        if not source_path.is_relative_to(storage_root) or not source_path.is_file():
            raise FileNotFoundError("The registered document file is unavailable.")
        return source_path

    def _prepare_points(
        self,
        *,
        snapshot: DocumentSnapshot,
        chunks: tuple[TextChunk, ...],
        vectors: list[list[float]],
    ) -> tuple[list[VectorPoint], list[RagChunkInsert]]:
        """Duplicate chunks per entity so Metadata Filter remains exact."""

        points: list[VectorPoint] = []
        inserts: list[RagChunkInsert] = []
        for entity_id in snapshot.entity_ids:
            for chunk, vector in zip(chunks, vectors, strict=True):
                point_id = str(
                    uuid5(
                        NAMESPACE_URL,
                        (
                            f"agriguard:{snapshot.checksum_sha256}:{entity_id}:"
                            f"{chunk.chunk_index}:{chunk.content_sha256}"
                        ),
                    )
                )
                payload: dict[str, object] = {
                    "document_id": snapshot.id,
                    "pest_entity_id": entity_id,
                    "chunk_index": chunk.chunk_index,
                    "locator": chunk.locator,
                    "source_title": snapshot.title,
                    "source_organization": snapshot.source_organization,
                    "content_sha256": chunk.content_sha256,
                }
                if chunk.heading:
                    payload["heading"] = chunk.heading
                if snapshot.source_url:
                    payload["source_url"] = snapshot.source_url
                if snapshot.publication_date:
                    payload["publication_date"] = snapshot.publication_date.isoformat()
                if snapshot.region:
                    payload["region"] = snapshot.region
                points.append(
                    VectorPoint(
                        point_id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )
                inserts.append(
                    RagChunkInsert(
                        pest_entity_id=entity_id,
                        chunk_index=chunk.chunk_index,
                        heading=chunk.heading,
                        locator=chunk.locator,
                        content=chunk.content,
                        content_sha256=chunk.content_sha256,
                        qdrant_point_id=point_id,
                    )
                )
        return points, inserts

    async def _complete(
        self,
        snapshot: DocumentSnapshot,
        inserts: list[RagChunkInsert],
    ) -> None:
        """Atomically replace MySQL chunks and publish indexed status."""

        async with self._session.begin():
            document = await self._repository.get_by_id_for_update(snapshot.id)
            if document is None or document.status != "processing":
                raise RuntimeError("Document indexing state changed unexpectedly.")
            await self._repository.replace_chunks(
                document_id=snapshot.id,
                chunks=inserts,
            )
            await self._repository.mark_entities_draft(snapshot.entity_ids)
            document.status = "indexed"
            document.error_message = None
            await self._session.flush()

    async def _record_failure(self, document_id: int, exc: Exception) -> None:
        """Best-effort failure recording without hiding the original error."""

        try:
            async with self._session.begin():
                document = await self._repository.get_by_id_for_update(document_id)
                if document is not None and document.status == "processing":
                    document.status = "failed"
                    document.error_message = f"{type(exc).__name__}: {exc}"[:2000]
                    await self._session.flush()
        except Exception:
            logger.exception(
                "Could not mark knowledge document %s as failed",
                document_id,
            )

    @staticmethod
    def _snapshot(
        document: KnowledgeDocument,
        entity_ids: tuple[int, ...],
        previous_point_ids: tuple[str, ...],
    ) -> DocumentSnapshot:
        """Copy ORM fields needed after commit into an immutable value."""

        return DocumentSnapshot(
            id=document.id,
            title=document.title,
            source_organization=document.source_organization,
            source_url=document.source_url,
            publication_date=document.publication_date,
            region=document.region,
            file_path=document.file_path,
            file_type=document.file_type,
            checksum_sha256=document.checksum_sha256,
            entity_ids=entity_ids,
            previous_point_ids=previous_point_ids,
        )

    @staticmethod
    def _is_provenance_only_heading(heading: str | None) -> bool:
        """Exclude structured source headers already stored as metadata."""

        if heading is None:
            return False
        return heading.strip().casefold() in {
            "来源信息",
            "source information",
            "provenance",
        }
