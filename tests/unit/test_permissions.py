"""Unit tests for the §21 permission-matching logic and the `require_permission` dependency —
pure logic, no database, no network."""

import uuid
from collections.abc import AsyncGenerator

import pytest
from core.auth.dependencies import _permission_matches, get_current_user, require_permission
from core.auth.models import Role, User
from core.database.session import get_db_session
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.parametrize(
    ("granted", "resource", "action", "expected"),
    [
        ("leads.read", "leads", "read", True),
        ("leads.read", "leads", "write", False),
        ("leads.*", "leads", "write", True),
        ("*.read", "deals", "read", True),
        ("*.*", "anything", "anything", True),
        ("deals.read", "leads", "read", False),
    ],
)
def test_permission_matches(granted: str, resource: str, action: str, expected: bool) -> None:
    assert _permission_matches(granted, resource, action) is expected


def _fake_user() -> User:
    user = User(
        tenant_id=uuid.uuid4(),
        email="fake@example.com",
        full_name="Fake User",
        password_hash="irrelevant",  # noqa: S106 — placeholder, not a credential
        role_id=uuid.uuid4(),
    )
    user.id = uuid.uuid4()
    return user


class _FakeSession:
    def __init__(self, role: Role | None) -> None:
        self._role = role

    async def get(self, _model: type[Role], _pk: uuid.UUID) -> Role | None:
        return self._role


async def test_require_permission_allows_when_role_grants_it() -> None:
    user = _fake_user()
    role = Role(tenant_id=user.tenant_id, name="Tester", permissions=["leads.read"])

    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(
        current: User = Depends(require_permission("leads.read")),
    ) -> dict[str, str]:
        return {"user_id": str(current.id)}

    test_app.dependency_overrides[get_current_user] = lambda: user

    async def fake_db_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession(role)

    test_app.dependency_overrides[get_db_session] = fake_db_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 200


async def test_require_permission_denies_when_role_lacks_it() -> None:
    user = _fake_user()
    role = Role(tenant_id=user.tenant_id, name="Tester", permissions=["deals.read"])

    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected(
        current: User = Depends(require_permission("leads.read")),
    ) -> dict[str, str]:
        return {"user_id": str(current.id)}

    test_app.dependency_overrides[get_current_user] = lambda: user

    async def fake_db_session() -> AsyncGenerator[_FakeSession]:
        yield _FakeSession(role)

    test_app.dependency_overrides[get_db_session] = fake_db_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 403
