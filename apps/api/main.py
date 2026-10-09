from core.logging.setup import configure_logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import auth, health

configure_logging()

app = FastAPI(title="AI Business OS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# §113: unprefixed GET /health for infra probes. Business APIs are mounted under /api/v1 (§79),
# starting with auth in M3.
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
