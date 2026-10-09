import uuid
from datetime import datetime

from core.database.base import Base, TenantScopedMixin
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Contact(Base, TenantScopedMixin):
    """§23. `consent_status`/`consent_captured_at` implement §135-137 consent tracking from the
    moment this table exists, ahead of any send capability (M5/M8 gate on it, not this table)."""

    __tablename__ = "contacts"
    __table_args__ = (Index("ix_contacts_tenant_email", "tenant_id", "email"),)

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)

    consent_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    consent_captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
