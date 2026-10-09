from typing import Literal

from core.config.settings import get_settings
from core.database.session import database_is_reachable
from core.events.bus import redis_is_reachable
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

ServiceStatus = Literal["online", "offline", "not_configured"]


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    services: dict[str, ServiceStatus]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    timeout = settings.health_check_timeout_seconds

    database: ServiceStatus = "online" if await database_is_reachable(timeout) else "offline"
    redis_status: ServiceStatus = "online" if await redis_is_reachable(timeout) else "offline"

    # AI provider, email, and CRM connectors are not wired yet (they land in M6/M5/M10) — report
    # this honestly rather than faking a status, per §202 ("mai dichiarare successo senza
    # verifica").
    services: dict[str, ServiceStatus] = {
        "database": database,
        "redis": redis_status,
        "ai": "not_configured",
        "email": "not_configured",
        "crm": "not_configured",
    }

    overall = "healthy" if database == "online" and redis_status == "online" else "degraded"
    return HealthResponse(status=overall, services=services)
