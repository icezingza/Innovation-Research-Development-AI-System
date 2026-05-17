from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC
from src.memory.schema import Base
import uuid


class TenantSwarm(Base):
    __tablename__ = "tenant_swarms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    template_id = Column(String, nullable=False)  # e.g., "fintech", "legal", "health"
    config_override = Column(JSON, nullable=True)  # ให้ลูกค้าปรับจูนเพิ่มได้
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=datetime.now(UTC))
    deactivated_at = Column(DateTime, nullable=True)

    # tenant back-ref removed; Tenant model has no `swarms` collection
    # (Phase 4 feature; can be re-enabled when Tenant.swarms is added)
