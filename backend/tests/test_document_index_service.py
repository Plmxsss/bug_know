"""Tests for deterministic document index point preparation."""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.rag.chunking import TextChunk
from app.services.document_index import DocumentIndexService, DocumentSnapshot


class FakeEmbedder:
    """Minimal embedding dependency used only for service construction."""

    dimension = 2

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def _service(tmp_path: Path) -> DocumentIndexService:
    return DocumentIndexService(
        session=AsyncMock(spec=AsyncSession),
        settings=Settings(
            _env_file=None,
            storage_dir=tmp_path,
            embedding_dimension=2,
        ),
        embedder=FakeEmbedder(),
        vector_database=AsyncMock(),
    )


def _snapshot() -> DocumentSnapshot:
    return DocumentSnapshot(
        id=3,
        title="Guide",
        source_organization="Institute",
        source_url="https://example.org/guide",
        publication_date=date(2025, 7, 14),
        region="Region",
        file_path="uploads/documents/guide.md",
        file_type="md",
        checksum_sha256="a" * 64,
        entity_ids=(1, 2),
    )


def test_prepared_point_ids_are_deterministic_and_entity_scoped(
    tmp_path: Path,
) -> None:
    """Retries should overwrite the same points, while entities remain separate."""

    service = _service(tmp_path)
    chunks = (
        TextChunk(
            chunk_index=0,
            heading="Damage",
            locator="heading:Damage",
            content="Leaf damage.",
            content_sha256="b" * 64,
        ),
    )

    first_points, first_inserts = service._prepare_points(
        snapshot=_snapshot(),
        chunks=chunks,
        vectors=[[1.0, 0.0]],
    )
    second_points, _second_inserts = service._prepare_points(
        snapshot=_snapshot(),
        chunks=chunks,
        vectors=[[1.0, 0.0]],
    )

    assert len(first_points) == 2
    assert first_points == second_points
    assert first_points[0].point_id != first_points[1].point_id
    assert first_points[0].payload["locator"] == "heading:Damage"
    assert [insert.locator for insert in first_inserts] == [
        "heading:Damage",
        "heading:Damage",
    ]


def test_source_path_cannot_escape_storage_root(tmp_path: Path) -> None:
    """A tampered database key must not read arbitrary local files."""

    service = _service(tmp_path)

    try:
        service._resolve_source_path("../outside.md")
    except FileNotFoundError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("Directory traversal should have been rejected.")
