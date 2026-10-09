import uuid

from core.database.base import Base, TenantScopedMixin
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column


class Lead(Base, TenantScopedMixin):
    """§24-25. `score`/`score_explanation` are populated by the scoring engine in M7 — both stay
    NULL until then, never a fabricated value (§202)."""

    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_tenant_status", "tenant_id", "status"),)

    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_explanation: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
