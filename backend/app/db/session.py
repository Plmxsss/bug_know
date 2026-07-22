"""Create and manage the application's asynchronous MySQL connection pool."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import Settings


class DatabaseGateway(Protocol):
    """Small interface needed by application startup and readiness checks."""

    async def ping(self) -> None:
        """Raise an exception when the database cannot answer."""

    async def close(self) -> None:
        """Release database connections owned by the application."""


def build_database_url(settings: Settings) -> URL:
    """Build a safely escaped SQLAlchemy URL from application settings."""

    return URL.create(
        drivername="mysql+asyncmy",
        username=settings.mysql_user,
        password=settings.mysql_password.get_secret_value(),
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database,
        query={"charset": "utf8mb4"},
    )


class Database:
    """Own the shared connection pool and the factory that creates sessions."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            build_database_url(settings),
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    async def ping(self) -> None:
        """Run the smallest useful SQL statement to verify connectivity."""

        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Close every connection currently kept by the connection pool."""

        await self.engine.dispose()
