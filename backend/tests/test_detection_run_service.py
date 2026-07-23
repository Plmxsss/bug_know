"""Tests for transaction boundaries in the complete detection workflow."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.ml.predictors import PredictionResult
from app.models import DetectionTask
from app.services import (
    AnnotatedImage,
    DetectionRunService,
    EntityNormalization,
    StoredImage,
)


async def test_normalization_transaction_finishes_before_task_completion(
    tmp_path: Path,
) -> None:
    """A SELECT transaction must not remain open when completion begins."""

    session = AsyncMock(spec=AsyncSession)
    predictor = Mock()
    prediction = PredictionResult(
        image_width=20,
        image_height=20,
        detections=(),
        elapsed_ms=1.0,
        device="cpu",
    )
    predictor.predict.return_value = prediction
    service = DetectionRunService(
        session=session,
        predictor=predictor,
        predictor_lock=asyncio.Lock(),
        settings=Settings(_env_file=None, storage_dir=tmp_path),
    )
    task = DetectionTask(id=5, model_version_id=1, status="pending")
    completed = DetectionTask(id=5, model_version_id=1, status="completed")
    service._create_pending_task = AsyncMock(return_value=task)
    service._task_service.start = AsyncMock(return_value=task)
    service._normalizer.normalize_many = AsyncMock(
        return_value={
            0: EntityNormalization(
                class_id=0,
                raw_class_name="pest",
                status="unmapped",
                entity_id=None,
                entity_code=None,
                common_name=None,
                knowledge_status=None,
            )
        }
    )
    service._renderer.render = Mock(
        return_value=AnnotatedImage(
            absolute_path=tmp_path / "annotated.jpg",
            relative_path="uploads/annotated/annotated.jpg",
        )
    )
    service._task_service.complete = AsyncMock(return_value=completed)
    stored = StoredImage(
        absolute_path=tmp_path / "original.jpg",
        relative_path="uploads/original/original.jpg",
        width=20,
        height=20,
        image_format="JPEG",
        size_bytes=100,
    )

    result = await service.run(stored)

    assert result.task is completed
    session.begin.assert_called_once_with()
    service._task_service.complete.assert_awaited_once()
