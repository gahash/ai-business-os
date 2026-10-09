import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A tenant is the root of the multi-tenant hierarchy (§18); it has no `tenant_id` of its
    own and every other business table hangs off it via `TenantScopedMixin`."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Role(Base, TenantScopedMixin):
    """Roles are tenant-scoped and carry a list of `resource.action` permission strings (§20-21).
    Permission *enforcement* (the reusable dependency every route uses) lands in M3 — this table
    only defines the shape the enforcement layer will read from."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TenantScopedMixin):
    """§19. `password_hash` is always an Argon2id hash (`core/security/passwords.py`), never a
    plaintext value. `mfa_secret`/`mfa_enabled` are the MFA hook (§103): `mfa/setup` (M3)
    generates and stores the TOTP secret, but login does not yet enforce it — enforcement is a
    follow-up once a real TOTP verification flow is needed, not before."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)

    role: Mapped[Role] = relationship(back_populates="users")


class RefreshToken(Base, TenantScopedMixin):
    """Opaque refresh tokens (§103): only a SHA-256 hash of the token is stored, never the raw
    value. `replaced_by_id` implements rotation — each `/auth/refresh` call revokes the token
    used and issues a new one, linking the chain so reuse of an already-rotated token is
    detectable (and revokes the whole chain, since that reuse signals theft)."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True
    )


class PasswordResetToken(Base, TenantScopedMixin):
    """§80 `/auth/password/reset`. Only a SHA-256 hash of the reset token is stored. Delivery of
    the raw token to the user happens over email — not wired until M5 — so `request_reset`
    currently returns the token directly to the caller rather than silently discarding it; see
    the TODO.md note on this limitation."""

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
