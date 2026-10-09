FROM python:3.11-slim

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY apps ./apps
COPY core ./core
COPY modules ./modules
COPY agents ./agents
COPY tools ./tools
COPY integrations ./integrations

RUN pip install --no-cache-dir -e .

CMD ["celery", "-A", "apps.worker.celery_app", "worker", "--loglevel=info"]
