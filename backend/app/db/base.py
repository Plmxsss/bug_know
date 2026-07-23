"""Shared base class for every SQLAlchemy ORM model."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Collect table definitions declared by the application's ORM models."""

