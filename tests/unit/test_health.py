from apps.api.main import app
from httpx import ASGITransport, AsyncClient


async def test_health_endpoint_reports_all_subsystems() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("healthy", "degraded")
    assert set(body["services"]) == {"database", "redis", "ai", "email", "crm"}
    # AI/email/crm connectors don't exist yet (M6/M5/M10) — must report this honestly,
    # never a faked "online" (§202).
    assert body["services"]["ai"] == "not_configured"
    assert body["services"]["email"] == "not_configured"
    assert body["services"]["crm"] == "not_configured"
