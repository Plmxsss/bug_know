"""Persistence operations for idempotent diagnosis report generation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DiagnosisReport


class DiagnosisReportRepository:
    """Read, claim, and update the single report row for a detection task."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_task_id(self, task_id: int) -> DiagnosisReport | None:
        """Return one report without locking it."""

        result = await self._session.execute(
            select(DiagnosisReport).where(DiagnosisReport.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_task_id_for_update(
        self,
        task_id: int,
    ) -> DiagnosisReport | None:
        """Lock one report lifecycle row until transaction completion."""

        result = await self._session.execute(
            select(DiagnosisReport)
            .where(DiagnosisReport.task_id == task_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_processing(
        self,
        *,
        task_id: int,
        prompt_version: str,
    ) -> DiagnosisReport:
        """Reserve one task before making a potentially expensive model call."""

        report = DiagnosisReport(
            task_id=task_id,
            status="processing",
            llm_provider=None,
            llm_model=None,
            prompt_version=prompt_version,
            report_json=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            error_message=None,
            completed_at=None,
        )
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)
        return report
