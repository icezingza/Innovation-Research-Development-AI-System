"""Declarative Base for SQLAlchemy ORM models.

Defined in a separate module to prevent circular dependencies between
src/memory/schema.py and src/tenants/models.py.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy ORM models."""

    pass
