"""Tests for diagnosis report validation and idempotent reads."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models import DetectionObject, DetectionTask, DiagnosisReport
from app.services.diagnosis_report import DiagnosisReportService


def _report_content() -> dict[str, object]:
    """Return one minimal report JSON value accepted by Pydantic."""

    return {
        "summary": "检测到稻纵卷叶螟。",
        "detected_entities": [
            {
                "entity_id": 1,
                "name": "稻纵卷叶螟",
                "confidence": 0.91,
                "count": 1,
                "introduction": "水稻害虫。",
                "typical_features": "幼虫卷叶取食。",
                "host_plants": ["水稻"],
                "damage": "叶片形成白色条斑。",
                "environmental_conditions": "发生情况受地区和季节影响。",
                "prevention": ["加强田间监测。"],
                "control_methods": ["依据当地植保意见综合防治。"],
                "uncertainty": "图像识别存在不确定性。",
                "citation_point_ids": ["point-1"],
            }
        ],
        "references": [
            {
                "point_id": "point-1",
                "document_id": 1,
                "title": "水稻害虫资料",
                "source_organization": "农业机构",
                "source_url": "https://example.org/rice",
                "publication_date": "2026-05-26",
                "region": "测试地区",
                "locator": "heading:为害特征",
            }
        ],
        "disclaimer": (
            "识别结果仅供农业生产参考，不能替代当地农业技术人员的现场诊断。"
        ),
    }


def _service() -> DiagnosisReportService:
    """Construct the service with dependencies that cannot perform real I/O."""

    return DiagnosisReportService(
        session=AsyncMock(spec=AsyncSession),
        settings=Settings(_env_file=None),
        vector_database=Mock(),
        embedder=None,
        llm_provider=None,
    )


async def test_generate_returns_existing_completed_report_without_llm() -> None:
    """A repeated POST should read the stored report and do no model work."""

    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    report = DiagnosisReport(
        id=8,
        task_id=7,
        status="completed",
        llm_provider="ollama",
        llm_model="qwen3:4b",
        prompt_version="diagnosis-v1",
        report_json=_report_content(),
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        created_at=now,
        completed_at=now,
    )
    service = _service()
    service._reports.get_by_task_id = AsyncMock(return_value=report)
    service._tasks.get_by_id = AsyncMock()

    stored = await service.generate(7)

    assert stored.id == 8
    assert stored.report.detected_entities[0].name == "稻纵卷叶螟"
    service._tasks.get_by_id.assert_not_awaited()


async def test_generate_rejects_detection_without_verified_mapping() -> None:
    """An unreviewed class must stop before embedding retrieval or an LLM."""

    service = _service()
    service._reports.get_by_task_id = AsyncMock(return_value=None)
    service._tasks.get_by_id = AsyncMock(
        return_value=DetectionTask(id=7, status="completed")
    )
    service._objects.list_by_task_id = AsyncMock(
        return_value=[
            DetectionObject(
                id=1,
                task_id=7,
                class_id=22,
                raw_class_name="unreviewed pest",
                normalized_entity_id=None,
                confidence=0.8,
                bbox_x1=1,
                bbox_y1=2,
                bbox_x2=10,
                bbox_y2=12,
            )
        ]
    )
    service._entities.get_by_ids = AsyncMock()

    with pytest.raises(AppError) as exc_info:
        await service.generate(7)

    assert exc_info.value.code == "DETECTION_HAS_UNVERIFIED_ENTITIES"
    service._entities.get_by_ids.assert_not_awaited()
