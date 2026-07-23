"""Database operations for model_versions records."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ModelVersion


class ModelVersionRepository:
    """Read and write model version rows through one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name_and_version(
        self,
        *,
        name: str,
        version: str,
    ) -> ModelVersion | None:
        """Return one matching model version, or None when it is not registered."""

        statement = select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_by_name_and_version(
        self,
        *,
        name: str,
        version: str,
    ) -> ModelVersion | None:
        """Return the exact active model configured for inference."""

        statement = select(ModelVersion).where(
            ModelVersion.name == name,
            ModelVersion.version == version,
            ModelVersion.is_active.is_(True),
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        version: str,
        weights_path: str,
        checksum_sha256: str,
        class_count: int,
        is_active: bool = False,
    ) -> ModelVersion:
        """Add one model version and load its database-generated values."""

        model_version = ModelVersion(
            name=name,
            version=version,
            weights_path=weights_path,
            checksum_sha256=checksum_sha256,
            class_count=class_count,
            is_active=is_active,
        )
        self._session.add(model_version)
        await self._session.flush()
        await self._session.refresh(model_version)
        return model_version
