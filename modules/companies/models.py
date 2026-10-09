from core.database.base import Base, TenantScopedMixin
from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column


class Company(Base, TenantScopedMixin):
    """§22."""

    __tablename__ = "companies"
    __table_args__ = (Index("ix_companies_tenant_name", "tenant_id", "name"),)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[int | None] = mapped_column(nullable=True)
