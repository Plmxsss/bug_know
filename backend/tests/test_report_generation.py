"""Tests for evidence-bound structured diagnosis generation."""

from datetime import date

import pytest

from app.llm import LLMProviderError, LLMUsage, StructuredLLMResult
from app.schemas.diagnosis import EntityKnowledgeSynthesis
from app.services.knowledge_search import RetrievedKnowledge
from app.services.report_generation import (
    DetectedEntityContext,
    ReportGenerator,
)


class FakeProvider:
    """Return a configured synthesis without any external model call."""

    def __init__(self, synthesis: EntityKnowledgeSynthesis) -> None:
        self.synthesis = synthesis
        self.messages = ()

    async def generate_structured(self, *, messages, response_model):
        self.messages = messages
        return StructuredLLMResult(
            value=self.synthesis,
            provider="mock",
            model="mock-model",
            usage=LLMUsage(10, 20, 30),
        )

    async def close(self) -> None:
        return None


def _hit(point_id: str = "point-1") -> RetrievedKnowledge:
    return RetrievedKnowledge(
        point_id=point_id,
        score=0.9,
        document_id=7,
        heading="Damage",
        locator="heading:Damage",
        content="幼虫卷叶并取食叶肉，受害叶片出现白色条斑。",
        title="Rice pest guide",
        source_organization="Agriculture Institute",
        source_url="https://example.org/guide",
        publication_date=date(2026, 5, 26),
        region="Test region",
    )


def _context() -> DetectedEntityContext:
    return DetectedEntityContext(
        entity_id=1,
        name="稻纵卷叶螟",
        confidence=0.91,
        count=2,
        knowledge_status="reviewed",
        hits=(_hit(),),
    )


def _synthesis(**overrides) -> EntityKnowledgeSynthesis:
    values = {
        "introduction": "水稻害虫。",
        "typical_features": "幼虫会卷叶取食。",
        "host_plants": ["水稻"],
        "damage": "受害叶片出现白色条斑。",
        "environmental_conditions": "资料具有地区属性。",
        "prevention": ["结合当地监测开展综合防控。"],
        "control_methods": ["咨询当地植保人员。"],
        "uncertainty": "图片识别与地区差异会带来不确定性。",
        "citation_point_ids": ["point-1"],
    }
    values.update(overrides)
    return EntityKnowledgeSynthesis(**values)


async def test_report_keeps_detection_facts_and_rebuilds_references() -> None:
    """The model writes prose, while code owns identity, count, and citation data."""

    provider = FakeProvider(_synthesis())
    report = await ReportGenerator(provider).generate((_context(),))

    entity = report.content.detected_entities[0]
    assert entity.entity_id == 1
    assert entity.confidence == pytest.approx(0.91)
    assert entity.count == 2
    assert report.content.references[0].document_id == 7
    assert report.content.references[0].title == "Rice pest guide"
    assert report.content.disclaimer.startswith("识别结果仅供")
    assert "point-1" in provider.messages[1].content


async def test_report_rejects_citation_not_in_current_retrieval() -> None:
    """A plausible-looking but unavailable point ID is still hallucinated."""

    provider = FakeProvider(_synthesis(citation_point_ids=["invented"]))

    with pytest.raises(LLMProviderError) as exc_info:
        await ReportGenerator(provider).generate((_context(),))

    assert exc_info.value.code == "LLM_INVALID_CITATIONS"


async def test_report_rejects_universal_pesticide_dosage() -> None:
    """Post-generation safety checks should backstop the prompt instruction."""

    provider = FakeProvider(
        _synthesis(control_methods=["统一使用某药剂 30 克/亩。"])
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await ReportGenerator(provider).generate((_context(),))

    assert exc_info.value.code == "LLM_UNSAFE_DOSAGE"
