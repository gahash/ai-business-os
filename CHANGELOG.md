# Changelog

Tutte le modifiche rilevanti al progetto sono documentate in questo file.
Formato ispirato a [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **M3 (completa):** JWT access token + refresh token opaco con rotazione e rilevazione del
  riutilizzo (`core/security/tokens.py`); dependency `get_current_user`/`require_permission`
  riutilizzabili da ogni route futura (`core/auth/dependencies.py`); endpoint
  `/api/v1/auth/{login,logout,refresh,me,password/reset/request,password/reset/confirm,
  mfa/setup}` (`apps/api/routes/auth.py`); tabelle `refresh_tokens`/`password_reset_tokens` +
  colonne MFA su `users`; test unitari sul matching permessi, test di integrazione sul flusso
  auth completo contro Postgres reale, test di sicurezza sull'isolamento tenant (§145)
- **M2 (completa):** schema PostgreSQL reale (`tenants`, `users`, `roles`, `companies`,
  `contacts`, `leads`, `deals`, `pipelines`, `pipeline_stages`, `activities`) con mixin
  condiviso tenant/audit/soft-delete; Alembic collegato ai modelli reali con la prima
  migration generata via autogenerate e applicata; script di seed idempotente (tenant demo,
  ruolo Owner, utente owner, pipeline standard a 7 stage); hashing password Argon2id
  (`core/security/passwords.py`); test di integrazione contro Postgres reale
  (`tests/integration/test_schema.py`); `scripts/dev_postgres.py` + target Makefile
  `db-start`/`db-stop`/`db-migrate`/`db-seed` per uno sviluppo locale senza Docker

### Fixed
- `/health` riportava `database: offline` a freddo perché il timeout di default (2s) era più
  basso del tempo della prima connessione asyncpg osservato su questa macchina (~2.06s);
  alzato a 5s (`core/config/settings.py`)
- Import ciclico tra `core.database.models` e `core.auth.models` risolto spostando i mixin
  condivisi in `core/database/base.py`
- `MissingGreenlet` di SQLAlchemy/asyncpg al secondo test asincrono, causato da un engine
  condiviso a livello di modulo riusato su loop diversi per test; risolto impostando un
  event loop di sessione condiviso per pytest-asyncio (coerente con l'esecuzione reale
  dell'app, che ha un solo loop per l'intera vita del processo)

### Added (M1)
- Roadmap di progetto ([ROADMAP.md](ROADMAP.md)) che traduce la specifica tecnica completa in
  milestone sequenziali (M1…M16)
- README.md e TODO.md iniziali
- **M1 (completa):** scheletro repo completo (§5); backend FastAPI con `GET /health` reale
  (controlla davvero connettività DB/Redis, riporta onestamente "not_configured" per
  AI/email/CRM non ancora costruiti); frontend Next.js che chiama `/health` e mostra lo stato
  live; primo test unitario (`tests/unit/test_health.py`); ruff/mypy strict/black configurati e
  puliti; `docker-compose.yml`, `docker-compose.prod.yml`, Dockerfile per
  api/worker/scheduler/web, nginx reverse proxy, `Makefile`, `.env.example`, `.gitignore`

### Known limitations
- Docker e `make` non disponibili sull'attuale macchina di sviluppo: gli artefatti Docker/
  Makefile sono scritti secondo spec ma non ancora eseguiti end-to-end (vedi TODO.md)
- PostgreSQL usato per M2 è nativo (via `pgserver`), non containerizzato — vedi TODO.md
