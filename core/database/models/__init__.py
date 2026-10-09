"""Import every ORM model here so `Base.metadata` is complete for Alembic autogenerate and for
`Base.metadata.create_all` in tests, regardless of which module actually owns the table."""

from modules.companies.models import Company
from modules.contacts.models import Contact
from modules.crm.models import Activity
from modules.deals.models import Deal
from modules.leads.models import Lead
from modules.pipeline.models import Pipeline, PipelineStage

from core.auth.models import PasswordResetToken, RefreshToken, Role, Tenant, User
from core.database.base import Base

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Role",
    "RefreshToken",
    "PasswordResetToken",
    "Company",
    "Contact",
    "Lead",
    "Deal",
    "Pipeline",
    "PipelineStage",
    "Activity",
]
