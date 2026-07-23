"""Dependencies shared by API routes."""

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import Database


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Give one database session to a request and close it afterward."""

    database = cast(Database, request.app.state.database)
    async with database.session_factory() as session:
        yield session
