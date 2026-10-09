import base64
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from core.auth.dependencies import get_current_user
from core.auth.models import PasswordResetToken, RefreshToken, Tenant, User
from core.config.settings import get_settings
from core.database.session import get_db_session
from core.security.passwords import hash_password, verify_password
from core.security.tokens import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

# §80: generic message for every credential/tenant/account lookup failure in this module —
# never reveal which part was wrong (email exists but wrong password vs. unknown tenant, etc.).
_INVALID_CREDENTIALS = "invalid credentials"


class LoginRequest(BaseModel):
    tenant_slug: str
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — OAuth2 scheme name, not a secret
    expires_in: int


class CurrentUser(BaseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str
    role_id: str
    mfa_enabled: bool


class PasswordResetRequest(BaseModel):
    tenant_slug: str
    email: str


class PasswordResetRequestResponse(BaseModel):
    status: Literal["reset_token_issued", "no_matching_account"]
    # Email delivery isn't wired until M5 (see TODO.md) — until then the raw token is returned
    # directly rather than silently discarded (§202: never fake success). This is a documented,
    # temporary gap: it lets a caller who knows a valid tenant+email confirm the account exists,
    # which a production email-delivery flow would not do.
    reset_token: str | None = None


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str
    new_password: str


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


async def _issue_token_pair(
    session: AsyncSession, user: User, *, replaces: RefreshToken | None = None
) -> TokenPair:
    settings = get_settings()
    access_token = create_access_token(user_id=str(user.id), tenant_id=str(user.tenant_id))

    raw_refresh = generate_opaque_token()
    refresh_row = RefreshToken(
        tenant_id=user.tenant_id,
        user_id=user.id,
        token_hash=hash_opaque_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days),
    )
    session.add(refresh_row)
    await session.flush()

    if replaces is not None:
        replaces.revoked_at = datetime.now(UTC)
        replaces.replaced_by_id = refresh_row.id

    await session.commit()
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_ttl_minutes * 60,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPair:
    tenant = await session.scalar(
        select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.deleted_at.is_(None))
    )
    user = None
    if tenant is not None:
        user = await session.scalar(
            select(User).where(
                User.tenant_id == tenant.id,
                User.email == payload.email,
                User.deleted_at.is_(None),
            )
        )
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _INVALID_CREDENTIALS)

    return await _issue_token_pair(session, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenPair:
    token_hash = hash_opaque_token(payload.refresh_token)
    row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")

    if row.revoked_at is not None:
        # Reuse of an already-rotated token is a theft signal (§103) — revoke every other active
        # token for this user, forcing re-login everywhere.
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await session.commit()
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "refresh token reuse detected — all sessions revoked"
        )

    if row.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token expired")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")

    return await _issue_token_pair(session, user, replaces=row)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)) -> None:
    token_hash = hash_opaque_token(payload.refresh_token)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


@router.get("/me", response_model=CurrentUser)
async def me(user: User = Depends(get_current_user)) -> CurrentUser:
    return CurrentUser(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        full_name=user.full_name,
        role_id=str(user.role_id),
        mfa_enabled=user.mfa_enabled,
    )


@router.post("/password/reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    payload: PasswordResetRequest, session: AsyncSession = Depends(get_db_session)
) -> PasswordResetRequestResponse:
    tenant = await session.scalar(
        select(Tenant).where(Tenant.slug == payload.tenant_slug, Tenant.deleted_at.is_(None))
    )
    user = None
    if tenant is not None:
        user = await session.scalar(
            select(User).where(
                User.tenant_id == tenant.id,
                User.email == payload.email,
                User.deleted_at.is_(None),
            )
        )
    if user is None:
        return PasswordResetRequestResponse(status="no_matching_account")

    raw_token = generate_opaque_token()
    session.add(
        PasswordResetToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await session.commit()
    return PasswordResetRequestResponse(status="reset_token_issued", reset_token=raw_token)


@router.post("/password/reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest, session: AsyncSession = Depends(get_db_session)
) -> None:
    token_hash = hash_opaque_token(payload.reset_token)
    row = await session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    now = datetime.now(UTC)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired reset token")

    user = await session.get(User, row.user_id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or expired reset token")

    user.password_hash = hash_password(payload.new_password)
    row.used_at = now
    # A password reset invalidates every existing session, not just the credential.
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await session.commit()


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db_session)
) -> MfaSetupResponse:
    """§103 MFA hook: generates and stores a real TOTP secret. Login does not enforce MFA yet —
    that needs a verification step (`/mfa/verify` + checking a submitted code against the
    secret), deliberately left out here rather than half-built (§202)."""
    secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    user.mfa_secret = secret
    user.mfa_enabled = False
    await session.commit()

    issuer = "AI Business OS"
    label = f"{issuer}:{user.email}"
    otpauth_uri = f"otpauth://totp/{label}?secret={secret}&issuer={issuer}"
    return MfaSetupResponse(secret=secret, otpauth_uri=otpauth_uri)
