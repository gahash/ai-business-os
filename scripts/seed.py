"""Demo seed data per §150: a demo tenant, an owner user, and the standard sales pipeline (§28).

Idempotent — safe to run multiple times; it looks up the demo tenant by slug before creating
anything. Run with `python -m scripts.seed` (see Makefile `make seed`).
"""

import asyncio

from core.auth.models import Role, Tenant, User
from core.database.session import async_session_factory
from core.security.passwords import hash_password
from modules.pipeline.models import Pipeline, PipelineStage
from sqlalchemy import select

DEMO_TENANT_SLUG = "demo"
DEMO_OWNER_EMAIL = "owner@demo.local"
DEMO_OWNER_PASSWORD = "ChangeMe123!"  # noqa: S105 — demo-only seed credential, not a real secret

STANDARD_STAGES = [
    ("New", False, False),
    ("Contacted", False, False),
    ("Qualified", False, False),
    ("Proposal", False, False),
    ("Negotiation", False, False),
    ("Won", True, False),
    ("Lost", False, True),
]


async def seed() -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
        if existing is not None:
            print(f"Demo tenant already seeded (id={existing.id}); nothing to do.")
            return

        tenant = Tenant(name="Demo Tenant", slug=DEMO_TENANT_SLUG)
        session.add(tenant)
        await session.flush()

        # Wildcard permission convention: "*.*" grants every resource.action pair (§21). The
        # real permission-check dependency lands in M3 and is what interprets this string.
        owner_role = Role(tenant_id=tenant.id, name="Owner", permissions=["*.*"])
        session.add(owner_role)
        await session.flush()

        owner = User(
            tenant_id=tenant.id,
            email=DEMO_OWNER_EMAIL,
            full_name="Demo Owner",
            password_hash=hash_password(DEMO_OWNER_PASSWORD),
            role_id=owner_role.id,
        )
        session.add(owner)

        pipeline = Pipeline(tenant_id=tenant.id, name="Standard Pipeline", is_default=True)
        session.add(pipeline)
        await session.flush()

        for position, (name, is_won, is_lost) in enumerate(STANDARD_STAGES):
            session.add(
                PipelineStage(
                    tenant_id=tenant.id,
                    pipeline_id=pipeline.id,
                    name=name,
                    position=position,
                    is_won=is_won,
                    is_lost=is_lost,
                )
            )

        await session.commit()
        print(
            f"Seeded demo tenant {tenant.slug!r} (id={tenant.id}) — "
            f"owner {DEMO_OWNER_EMAIL!r} / password {DEMO_OWNER_PASSWORD!r}, "
            f"pipeline {pipeline.name!r} with {len(STANDARD_STAGES)} stages."
        )


if __name__ == "__main__":
    asyncio.run(seed())
