import uuid
from datetime import datetime

from core.database.base import Base, TenantScopedMixin
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Activity(Base, TenantScopedMixin):
    """§29. A single activity timeline shared across contacts/companies/deals/leads — the
    internal `CRMConnector` (M4, §38) writes here for every interaction it records."""

    __tablename__ = "activities"
    __table_args__ = (Index("ix_activities_tenant_occurred_at", "tenant_id", "occurred_at"),)

    type: Mapped[str] = mapped_column(String(20), nullable=False)  # call/email/meeting/note/task
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id"), nullable=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True
    )
