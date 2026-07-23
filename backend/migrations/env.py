"""Configure Alembic to use the application's async MySQL connection."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.session import build_database_url
from app.models import ModelVersion

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = ModelVersion.metadata


def run_migrations_offline() -> None:
    """Render SQL without opening a database connection."""

    url = build_database_url(get_settings())
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migration operations through one synchronous connection view."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Open an async connection and let Alembic use it for migrations."""

    connectable = create_async_engine(
        build_database_url(get_settings()),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against the configured MySQL database."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
