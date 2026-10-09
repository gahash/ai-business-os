import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.models import Role, User
from core.database.session import get_db_session
from core.security.tokens import TokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed token claims") from exc

    # §145: the tenant isolation invariant lives here — a token can only ever resolve to the
    # exact (user_id, tenant_id) pair it was issued for, never to that user_id under a
    # different tenant.
    user = await session.scalar(
        select(User).where(
            User.id == user_id, User.tenant_id == tenant_id, User.deleted_at.is_(None)
        )
    )
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")
    return user


def _permission_matches(granted: str, resource: str, action: str) -> bool:
    granted_resource, _, granted_action = granted.partition(".")
    return granted_resource in ("*", resource) and granted_action in ("*", action)


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    """§21: `permission` is a `resource.action` string; a role's `permissions` list grants it via
    an exact match or a wildcard (`"*.*"` or `"resource.*"`). Reusable by every route from M4
    onward — routes depend on `require_permission("leads.read")` etc. rather than reimplementing
    the check."""

    resource, _, action = permission.partition(".")

    async def _dependency(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db_session),
    ) -> User:
        role = await session.get(Role, user.role_id)
        granted = role is not None and any(
            _permission_matches(entry, resource, action) for entry in role.permissions
        )
        if not granted:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"missing permission: {permission}")
        return user

    return _dependency
