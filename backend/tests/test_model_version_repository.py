"""Tests for model version database operations."""

from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelVersion
from app.repositories import ModelVersionRepository


async def test_create_adds_and_flushes_model_version() -> None:
    """Creating a record should send one ORM object through the session."""

    session = AsyncMock(spec=AsyncSession)
    repository = ModelVersionRepository(session)

    result = await repository.create(
        name="ip102-yolo",
        version="1.0.0",
        weights_path="data/models/best.pt",
        checksum_sha256="a" * 64,
        class_count=102,
        is_active=True,
    )

    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(result)
    assert result.name == "ip102-yolo"
    assert result.class_count == 102


async def test_get_by_name_and_version_returns_session_result() -> None:
    """The repository should return the row selected by the database session."""

    existing = ModelVersion(
        name="ip102-yolo",
        version="1.0.0",
        weights_path="data/models/best.pt",
        checksum_sha256="a" * 64,
        class_count=102,
        is_active=True,
    )
    session = AsyncMock(spec=AsyncSession)
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = query_result
    repository = ModelVersionRepository(session)

    result = await repository.get_by_name_and_version(
        name="ip102-yolo",
        version="1.0.0",
    )

    session.execute.assert_awaited_once()
    assert result is existing


async def test_get_active_model_returns_session_result() -> None:
    """Inference lookup should return only the configured active row."""

    existing = ModelVersion(
        name="ip102-yolo",
        version="1.0.0",
        weights_path="data/models/best.pt",
        checksum_sha256="a" * 64,
        class_count=102,
        is_active=True,
    )
    session = AsyncMock(spec=AsyncSession)
    query_result = Mock()
    query_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = query_result
    repository = ModelVersionRepository(session)

    result = await repository.get_active_by_name_and_version(
        name="ip102-yolo",
        version="1.0.0",
    )

    session.execute.assert_awaited_once()
    assert result is existing
