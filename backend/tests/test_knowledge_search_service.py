"""Tests for entity-scoped and citation-backed retrieval."""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.rag.vector_database import VectorSearchHit
from app.repositories.knowledge_search import (
    PestKnowledgeScope,
    StoredKnowledgeChunk,
)
from app.services.knowledge_search import KnowledgeSearchService


class FakeEmbedder:
    """Return a stable query vector without loading a real model."""

    dimension = 2

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def _service(tmp_path: Path) -> tuple[KnowledgeSearchService, AsyncMock]:
    vector_database = AsyncMock()
    service = KnowledgeSearchService(
        session=AsyncMock(spec=AsyncSession),
        settings=Settings(
            _env_file=None,
            storage_dir=tmp_path,
            embedding_dimension=2,
        ),
        embedder=FakeEmbedder(),
        vector_database=vector_database,
    )
    service._repository = AsyncMock()
    return service, vector_database


async def test_missing_knowledge_returns_empty_without_vector_search(
    tmp_path: Path,
) -> None:
    """Entities without indexed knowledge should avoid meaningless search."""

    service, vector_database = _service(tmp_path)
    service._repository.get_scope.return_value = PestKnowledgeScope(
        id=9,
        common_name="Pest",
        knowledge_status="missing",
    )

    result = await service.search(entity_id=9, query="damage", top_k=3)

    assert result.hits == ()
    vector_database.search_by_entity.assert_not_awaited()


async def test_search_drops_orphan_vector_points_and_rebuilds_citations(
    tmp_path: Path,
) -> None:
    """Qdrant ranks candidates, while MySQL remains the source of returned text."""

    service, vector_database = _service(tmp_path)
    service._repository.get_scope.return_value = PestKnowledgeScope(
        id=1,
        common_name="Rice leaf folder",
        knowledge_status="draft",
    )
    vector_database.search_by_entity.return_value = [
        VectorSearchHit(point_id="trusted", score=0.91),
        VectorSearchHit(point_id="orphan", score=0.87),
    ]
    service._repository.get_chunks_by_point_ids.return_value = {
        "trusted": StoredKnowledgeChunk(
            point_id="trusted",
            document_id=3,
            heading="Damage",
            locator="heading:Damage",
            content="Larvae damage rice leaves.",
            title="Pest guide",
            source_organization="Agriculture Institute",
            source_url="https://example.org/guide",
            publication_date=date(2025, 7, 14),
            region="China",
        )
    }

    result = await service.search(entity_id=1, query="leaf damage", top_k=5)

    vector_database.search_by_entity.assert_awaited_once_with(
        collection_name="agriguard_knowledge",
        query_vector=[1.0, 0.0],
        pest_entity_id=1,
        limit=5,
    )
    assert [hit.point_id for hit in result.hits] == ["trusted"]
    assert result.hits[0].locator == "heading:Damage"
    assert result.hits[0].content == "Larvae damage rice leaves."
