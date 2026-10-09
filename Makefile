.PHONY: install start stop logs migrate seed db-start db-stop db-migrate db-seed test lint backup restore

COMPOSE = docker compose

install: ## Install backend + frontend dependencies for local (non-docker) development
	py -3.11 -m venv .venv
	.venv/Scripts/python -m pip install -e ".[dev]"
	cd apps/web && npm install

start: ## Start the full stack via Docker Compose
	$(COMPOSE) up -d

stop: ## Stop the full stack
	$(COMPOSE) down

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

migrate: ## Apply database migrations (Docker Compose stack)
	$(COMPOSE) exec backend alembic upgrade head

seed: ## Load demo tenant/user/pipeline seed data (Docker Compose stack)
	$(COMPOSE) exec backend python -m scripts.seed

db-start: ## Start local PostgreSQL without Docker (see scripts/dev_postgres.py)
	.venv/Scripts/python -m scripts.dev_postgres start

db-stop: ## Stop the local (non-docker) PostgreSQL instance
	.venv/Scripts/python -m scripts.dev_postgres stop

db-migrate: ## Apply database migrations against the local (non-docker) PostgreSQL
	.venv/Scripts/python -m alembic upgrade head

db-seed: ## Load demo seed data against the local (non-docker) PostgreSQL
	.venv/Scripts/python -m scripts.seed

test: ## Run the backend test suite
	.venv/Scripts/python -m pytest

lint: ## Run linters (backend: ruff/mypy/black --check, frontend: eslint)
	.venv/Scripts/python -m ruff check .
	.venv/Scripts/python -m mypy .
	.venv/Scripts/python -m black --check .
	cd apps/web && npm run lint

backup: ## Back up database, config and uploaded documents
	bash scripts/backup.sh

restore: ## Restore from the most recent backup
	bash scripts/restore.sh
