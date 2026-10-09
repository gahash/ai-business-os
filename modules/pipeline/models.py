import uuid

from core.database.base import Base, TenantScopedMixin
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Pipeline(Base, TenantScopedMixin):
    """§28."""

    __tablename__ = "pipelines"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stages: Mapped[list["PipelineStage"]] = relationship(
        back_populates="pipeline", order_by="PipelineStage.position"
    )


class PipelineStage(Base, TenantScopedMixin):
    """§28. `is_won`/`is_lost` mark terminal stages; `position` orders the kanban columns."""

    __tablename__ = "pipeline_stages"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "position", name="uq_pipeline_stages_pipeline_position"),
        Index("ix_pipeline_stages_tenant_pipeline", "tenant_id", "pipeline_id"),
    )

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_won: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_lost: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    pipeline: Mapped[Pipeline] = relationship(back_populates="stages")
