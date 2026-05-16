"""Canonical SQLAlchemy models for multi-tenant identity.

Tenant  — organization container with tier, domain, status
User    — member of a tenant with role and password
TenantMember — (legacy join table kept for backward-compat with existing tests)

These are the **single source of truth** for the tenants and users tables.
src/memory/schema.py re-exports Tenant and User from here.
"""
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.memory.schema import Base


class Tenant(Base):
    """Multi-tenant organization container."""

    __tablename__ = "tenants"

    # Primary key — accepts both str and UUID for backward-compat with older tests
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # domain: used by provisioning API (unique across the platform)
    domain: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    # slug: used by legacy tests (unique within the platform)
    slug: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    # tier: free | pro | enterprise
    tier: Mapped[str] = mapped_column(String(50), nullable=False, server_default="free")
    # status: active | suspended | deleted
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    db_connection_string: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    encrypted_settings: Mapped[Optional[dict]] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    members: Mapped[list["TenantMember"]] = relationship(
        "TenantMember", back_populates="tenant", cascade="all, delete-orphan"
    )


class User(Base):
    """Tenant-scoped user with email identity and role."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("tenants.id"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # display_name: kept for backward-compat with legacy tests
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # password_hash: column name used by auth routes
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # hashed_password: alias used by legacy tests
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), server_default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    memberships: Mapped[list["TenantMember"]] = relationship(
        "TenantMember", back_populates="user", cascade="all, delete-orphan"
    )


class TenantMember(Base):
    """Join table: User membership within Tenant with role."""

    __tablename__ = "tenant_members"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        SAEnum("owner", "admin", "member", name="tenant_role"),
        nullable=False,
        default="member",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="memberships")
