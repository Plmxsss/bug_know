"""Tests for diagnosis generation and persisted-report API routes."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.llm import LLMUsage
from app.main import create_app
from app.schemas import DiagnosisReportContent
from app.services import StoredDiagnosisReport


def _stored_report() -> StoredDiagnosisReport:
    """Return one complete service value used by both endpoints."""

    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    content = DiagnosisReportContent.model_validate(
        {
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
                "识别结果仅供农业生产参考，"
                "不能替代当地农业技术人员的现场诊断。"
            ),
        }
    )
    return StoredDiagnosisReport(
        id=8,
        task_id=7,
        status="completed",
        llm_provider="ollama",
        llm_model="qwen3:4b",
        prompt_version="diagnosis-v1",
        report=content,
        usage=LLMUsage(10, 20, 30),
        created_at=now,
        completed_at=now,
    )


def _client() -> tuple[TestClient, AsyncMock]:
    """Create an application whose database dependency cannot touch MySQL."""

    application = create_app()
    session = AsyncMock(spec=AsyncSession)

    async def override_session() -> AsyncIterator[AsyncSession]:
        yield session

    application.dependency_overrides[get_db_session] = override_session
    return TestClient(application), session


def test_post_diagnosis_returns_generated_report() -> None:
    """POST should serialize the report and never expose internal error fields."""

    client, _session = _client()
    generate = AsyncMock(return_value=_stored_report())
    with (
        client,
        patch(
            "app.api.routes.detections.DiagnosisReportService.generate",
            new=generate,
        ),
    ):
        response = client.post("/api/v1/detections/7/diagnosis")

    assert response.status_code == 200
    assert response.json()["task_id"] == 7
    assert response.json()["status"] == "completed"
    assert response.json()["report"]["detected_entities"][0]["entity_id"] == 1
    assert "error_message" not in response.json()
    generate.assert_awaited_once_with(7)


def test_get_report_reads_persisted_report() -> None:
    """GET should return stored JSON without invoking retrieval or generation."""

    client, _session = _client()
    get_completed = AsyncMock(return_value=_stored_report())
    with (
        client,
        patch(
            "app.api.routes.reports.DiagnosisReportService.get_completed",
            new=get_completed,
        ),
    ):
        response = client.get("/api/v1/reports/7")

    assert response.status_code == 200
    assert response.json()["usage"]["total_tokens"] == 30
    assert response.json()["report"]["references"][0]["document_id"] == 1
    get_completed.assert_awaited_once_with(7)
