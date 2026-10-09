"""§145: tenant isolation is non-negotiable from M3 onward. This proves the core invariant
`get_current_user` relies on — a token can only ever resolve to the exact (user_id, tenant_id)
pair it was issued for. Even a token forged with a *different* tenant_id for a *real* user_id
(the shape a cross-tenant attack would take) must resolve to nothing."""

import uuid

import pytest
from apps.api.main import app
from core.auth.models import Role, Tenant, User
from core.database.session import async_session_factory, database_is_reachable
from core.security.passwords import hash_password
from core.security.tokens import create_access_token
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

PASSWORD = "Sup3rSecret!1"  # noqa: S105 — fixture credential for this test only


@pytest.fixture(autouse=True)
async def _require_database() -> None:
    if not await database_is_reachable(timeout_seconds=5.0):
        pytest.skip("no reachable PostgreSQL configured (see scripts/dev_postgres.py)")


async def test_token_forged_with_another_tenant_id_is_rejected() -> None:
    suffix = uuid.uuid4().hex[:8]
    async with async_session_factory() as session:
        tenant_a = Tenant(name=f"Tenant A {suffix}", slug=f"tenant-a-{suffix}")
        tenant_b = Tenant(name=f"Tenant B {suffix}", slug=f"tenant-b-{suffix}")
        session.add_all([tenant_a, tenant_b])
        await session.flush()

        role_a = Role(tenant_id=tenant_a.id, name="Owner", permissions=["*.*"])
        session.add(role_a)
        await session.flush()

        user_a = User(
            tenant_id=tenant_a.id,
            email=f"user-{suffix}@example.com",
            full_name="User A",
            password_hash=hash_password(PASSWORD),
            role_id=role_a.id,
        )
        session.add(user_a)
        await session.commit()
        user_a_id, tenant_a_id, tenant_b_id = user_a.id, tenant_a.id, tenant_b.id

    try:
        genuine_token = create_access_token(user_id=str(user_a_id), tenant_id=str(tenant_a_id))
        # Same user_id, a different tenant_id — the shape a cross-tenant attack would take.
        forged_token = create_access_token(user_id=str(user_a_id), tenant_id=str(tenant_b_id))

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            genuine_response = await client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {genuine_token}"}
            )
            assert genuine_response.status_code == 200
            assert genuine_response.json()["tenant_id"] == str(tenant_a_id)

            forged_response = await client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_token}"}
            )
            assert forged_response.status_code == 401
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.tenant_id == tenant_a_id))
            await session.execute(delete(Role).where(Role.tenant_id == tenant_a_id))
            await session.execute(delete(Tenant).where(Tenant.id.in_([tenant_a_id, tenant_b_id])))
            await session.commit()
