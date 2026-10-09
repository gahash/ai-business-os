"""Integration tests for M3 auth: login, refresh rotation + reuse detection, logout, /me,
password reset, and the MFA setup hook — all against a real PostgreSQL and the real FastAPI app
(§202: no mocks). Skips, rather than faking a pass, when no database is reachable."""

import uuid

import pytest
from apps.api.main import app
from core.auth.models import PasswordResetToken, RefreshToken, Role, Tenant, User
from core.database.session import async_session_factory, database_is_reachable
from core.security.passwords import hash_password
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

PASSWORD = "Sup3rSecret!1"  # noqa: S105 — fixture credential for these tests only


@pytest.fixture(autouse=True)
async def _require_database() -> None:
    if not await database_is_reachable(timeout_seconds=5.0):
        pytest.skip("no reachable PostgreSQL configured (see scripts/dev_postgres.py)")


async def _make_tenant_with_user() -> tuple[Tenant, User]:
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        tenant = Tenant(name=f"Auth Test {suffix}", slug=f"auth-{suffix}")
        session.add(tenant)
        await session.flush()

        role = Role(tenant_id=tenant.id, name="Tester", permissions=[])
        session.add(role)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"user-{suffix}@example.com",
            full_name="Test User",
            password_hash=hash_password(PASSWORD),
            role_id=role.id,
        )
        session.add(user)
        await session.commit()
        return tenant, user


async def _cleanup_tenant(tenant_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(RefreshToken).where(RefreshToken.tenant_id == tenant_id))
        await session.execute(
            delete(PasswordResetToken).where(PasswordResetToken.tenant_id == tenant_id)
        )
        await session.execute(delete(User).where(User.tenant_id == tenant_id))
        await session.execute(delete(Role).where(Role.tenant_id == tenant_id))
        await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
        await session.commit()


async def test_login_returns_token_pair_and_me_requires_it() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": PASSWORD},
            )
            assert login.status_code == 200
            tokens = login.json()
            assert tokens["token_type"] == "bearer"  # noqa: S105 — scheme name, not a secret

            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            assert me.status_code == 200
            assert me.json()["email"] == user.email

            unauthenticated = await client.get("/api/v1/auth/me")
            assert unauthenticated.status_code == 401
    finally:
        await _cleanup_tenant(tenant.id)


async def test_login_rejects_wrong_password() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": "wrong"},
            )
            assert response.status_code == 401
    finally:
        await _cleanup_tenant(tenant.id)


async def test_refresh_rotates_and_detects_reuse() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": PASSWORD},
            )
            first_refresh = login.json()["refresh_token"]

            rotated = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": first_refresh}
            )
            assert rotated.status_code == 200
            second_refresh = rotated.json()["refresh_token"]
            assert second_refresh != first_refresh

            reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
            assert reuse.status_code == 401

            # Reuse detection revokes the whole chain, so the still-valid rotated token dies too.
            also_dead = await client.post(
                "/api/v1/auth/refresh", json={"refresh_token": second_refresh}
            )
            assert also_dead.status_code == 401
    finally:
        await _cleanup_tenant(tenant.id)


async def test_logout_revokes_refresh_token() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": PASSWORD},
            )
            token = login.json()["refresh_token"]

            logged_out = await client.post("/api/v1/auth/logout", json={"refresh_token": token})
            assert logged_out.status_code == 204

            refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": token})
            assert refreshed.status_code == 401
    finally:
        await _cleanup_tenant(tenant.id)


async def test_password_reset_flow() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            requested = await client.post(
                "/api/v1/auth/password/reset/request",
                json={"tenant_slug": tenant.slug, "email": user.email},
            )
            assert requested.status_code == 200
            body = requested.json()
            assert body["status"] == "reset_token_issued"
            reset_token = body["reset_token"]
            assert reset_token

            new_password = "AnotherSecret!2"  # noqa: S105
            confirmed = await client.post(
                "/api/v1/auth/password/reset/confirm",
                json={"reset_token": reset_token, "new_password": new_password},
            )
            assert confirmed.status_code == 204

            old_login = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": PASSWORD},
            )
            assert old_login.status_code == 401

            new_login = await client.post(
                "/api/v1/auth/login",
                json={
                    "tenant_slug": tenant.slug,
                    "email": user.email,
                    "password": new_password,
                },
            )
            assert new_login.status_code == 200
    finally:
        await _cleanup_tenant(tenant.id)


async def test_password_reset_request_for_unknown_account_does_not_error() -> None:
    tenant, _user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            requested = await client.post(
                "/api/v1/auth/password/reset/request",
                json={"tenant_slug": tenant.slug, "email": "nobody@example.com"},
            )
            assert requested.status_code == 200
            assert requested.json() == {"status": "no_matching_account", "reset_token": None}
    finally:
        await _cleanup_tenant(tenant.id)


async def test_mfa_setup_generates_and_stores_secret() -> None:
    tenant, user = await _make_tenant_with_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"tenant_slug": tenant.slug, "email": user.email, "password": PASSWORD},
            )
            token = login.json()["access_token"]

            setup = await client.post(
                "/api/v1/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"}
            )
            assert setup.status_code == 200
            body = setup.json()
            assert body["secret"]
            assert body["otpauth_uri"].startswith("otpauth://totp/")

        async with async_session_factory() as session:
            refreshed_user = await session.get(User, user.id)
            assert refreshed_user is not None
            assert refreshed_user.mfa_secret == body["secret"]
            assert refreshed_user.mfa_enabled is False
    finally:
        await _cleanup_tenant(tenant.id)
