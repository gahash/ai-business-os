"""Integration test for the M2 schema: exercises every table against a real PostgreSQL, not
mocks (§202). Skips — rather than faking a pass — when no reachable database is configured;
see `scripts/dev_postgres.py` for how to run one locally without Docker."""

import uuid
from datetime import UTC, datetime

import pytest
from core.auth.models import Role, Tenant, User
from core.database.session import async_session_factory, database_is_reachable
from modules.companies.models import Company
from modules.contacts.models import Contact
from modules.crm.models import Activity
from modules.deals.models import Deal
from modules.leads.models import Lead
from modules.pipeline.models import Pipeline, PipelineStage
from sqlalchemy import delete, select


@pytest.fixture(autouse=True)
async def _require_database() -> None:
    if not await database_is_reachable(timeout_seconds=5.0):
        pytest.skip("no reachable PostgreSQL configured (see scripts/dev_postgres.py)")


async def test_full_schema_round_trip() -> None:
    suffix = uuid.uuid4().hex[:8]

    async with async_session_factory() as session:
        tenant = Tenant(name=f"Test Tenant {suffix}", slug=f"test-{suffix}")
        session.add(tenant)
        await session.flush()

        role = Role(tenant_id=tenant.id, name="Owner", permissions=["*.*"])
        session.add(role)
        await session.flush()

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{suffix}@example.com",
            full_name="Test Owner",
            password_hash="not-a-real-hash",  # noqa: S106 — placeholder, not a credential
            role_id=role.id,
        )
        session.add(user)

        company = Company(tenant_id=tenant.id, name="Acme Inc")
        session.add(company)
        await session.flush()

        contact = Contact(
            tenant_id=tenant.id,
            company_id=company.id,
            first_name="Ada",
            last_name="Lovelace",
            email=f"ada-{suffix}@example.com",
        )
        session.add(contact)
        await session.flush()

        pipeline = Pipeline(tenant_id=tenant.id, name="Test Pipeline", is_default=True)
        session.add(pipeline)
        await session.flush()

        stage = PipelineStage(tenant_id=tenant.id, pipeline_id=pipeline.id, name="New", position=0)
        session.add(stage)
        await session.flush()

        lead = Lead(
            tenant_id=tenant.id,
            contact_id=contact.id,
            company_id=company.id,
            source="manual",
            status="new",
        )
        session.add(lead)
        await session.flush()

        deal = Deal(
            tenant_id=tenant.id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            company_id=company.id,
            contact_id=contact.id,
            lead_id=lead.id,
            title="Acme renewal",
            amount=1000,
        )
        session.add(deal)
        await session.flush()

        activity = Activity(
            tenant_id=tenant.id,
            type="note",
            subject="Kickoff call",
            occurred_at=datetime.now(UTC),
            contact_id=contact.id,
            deal_id=deal.id,
        )
        session.add(activity)
        await session.commit()

        tenant_id = tenant.id

        try:
            stored_deal = await session.scalar(select(Deal).where(Deal.tenant_id == tenant_id))
            assert stored_deal is not None
            assert stored_deal.status == "open"
            assert stored_deal.lead_id == lead.id

            stored_activity = await session.scalar(
                select(Activity).where(Activity.tenant_id == tenant_id)
            )
            assert stored_activity is not None
            assert stored_activity.deal_id == deal.id
        finally:
            # Real rows created for a one-off test tenant — clean up rather than leaving demo
            # data behind for every test run.
            for model in (
                Activity,
                Deal,
                Lead,
                PipelineStage,
                Pipeline,
                Contact,
                Company,
                User,
                Role,
            ):
                await session.execute(delete(model).where(model.tenant_id == tenant_id))
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()


async def test_user_email_is_unique_per_tenant() -> None:
    suffix = uuid.uuid4().hex[:8]
    email = f"dup-{suffix}@example.com"

    async with async_session_factory() as session:
        tenant = Tenant(name=f"Dup Tenant {suffix}", slug=f"dup-{suffix}")
        session.add(tenant)
        await session.flush()
        role = Role(tenant_id=tenant.id, name="Owner", permissions=["*.*"])
        session.add(role)
        await session.flush()
        tenant_id, role_id = tenant.id, role.id

        session.add(
            User(
                tenant_id=tenant_id,
                email=email,
                full_name="First",
                password_hash="hash-one",  # noqa: S106 — placeholder, not a credential
                role_id=role_id,
            )
        )
        await session.commit()

    # A fresh session per attempt mirrors real request handling — one session per request,
    # discarded (not reused) after an error, which is what avoids asyncpg pool/greenlet issues
    # from resuming work on a connection an unhandled exception left in a failed-transaction state.
    try:
        with pytest.raises(Exception, match="uq_users_tenant_email"):
            async with async_session_factory() as session:
                session.add(
                    User(
                        tenant_id=tenant_id,
                        email=email,
                        full_name="Second",
                        password_hash="hash-two",  # noqa: S106 — placeholder, not a credential
                        role_id=role_id,
                    )
                )
                await session.commit()
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.tenant_id == tenant_id))
            await session.execute(delete(Role).where(Role.tenant_id == tenant_id))
            await session.execute(delete(Tenant).where(Tenant.id == tenant_id))
            await session.commit()
