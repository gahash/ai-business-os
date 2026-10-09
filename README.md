# AI Business OS

Piattaforma operativa AI locale-first per la gestione aziendale: connette CRM, email,
calendario, pipeline vendite e social, interpreta i dati, propone decisioni ed esegue azioni
richiedendo approvazione umana quando necessario.

Non è un chatbot: opera secondo il ciclo OBSERVE → UNDERSTAND → REASON → PLAN → REQUEST
APPROVAL → EXECUTE → VERIFY → LOG → LEARN.

## Stato del progetto

**M1 — Infrastruttura, M2 — Database, M3 — Auth + RBAC: completate.** Scheletro repo, backend
FastAPI e frontend Next.js si avviano e comunicano tra loro; schema PostgreSQL reale con
Alembic e seed di demo; login JWT con refresh rotante e RBAC via permessi `resource.action` —
tutto verificato contro un database reale (locale, non containerizzato — Docker non è
installato qui, vedi [TODO.md](TODO.md)). Vedi [ROADMAP.md](ROADMAP.md) per il piano completo.

## Documenti di riferimento

- [ROADMAP.md](ROADMAP.md) — milestone sequenziali (M1…M16), mappate alla specifica tecnica
  completa e all'ordine di sviluppo obbligatorio
- [TODO.md](TODO.md) — todo tecnico corrente, aggiornato ad ogni milestone
- [CHANGELOG.md](CHANGELOG.md) — cronologia delle modifiche rilasciate

## Principi architetturali

Local First · Privacy First · Security First · API First · AI Provider Agnostic ·
Event Driven · Auditable · Multi Tenant Ready · Human In The Loop · Fail Safe ·
Observable · Modular

## Stack (target)

- **Backend:** Python 3.12+ (in sviluppo locale su questa macchina: 3.11.8, unica versione
  disponibile — vedi TODO.md), FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL, Redis,
  Celery, httpx, WebSocket
- **Frontend:** Next.js, React, TypeScript, TailwindCSS, TanStack Query, Zustand,
  React Hook Form, Zod (questi ultimi quattro verranno aggiunti quando serviranno, a partire da
  M4/M8)
- **Infra:** Docker Compose (frontend, backend, postgres, redis, worker, scheduler, ollama,
  reverse-proxy; opzionali: qdrant, minio, prometheus, grafana, loki, temporal)

## Setup locale

### Con Docker (consigliato, non ancora verificato su questa macchina)

```bash
cp .env.example .env
docker compose up -d
docker compose exec backend alembic upgrade head   # da M2 in poi
```

- API: http://localhost:8000/health
- Frontend: http://localhost:3000
- Reverse proxy: http://localhost (instrada `/` al frontend, `/api/` e `/health` al backend)

### Senza Docker (verificato — usato in sviluppo su questa macchina)

Database (PostgreSQL nativo via `pgserver`, nessun installer/servizio richiesto — vedi
`scripts/dev_postgres.py` e la sezione "Limitazioni note" in [TODO.md](TODO.md)):

```bash
.venv/Scripts/python -m scripts.dev_postgres start
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m scripts.seed
```

Backend:

```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m uvicorn apps.api.main:app --reload --port 8000
```

Frontend (in un altro terminale):

```bash
cd apps/web
npm install
npm run dev
```

Poi apri http://localhost:3000 — la home mostra lo stato live restituito da `/health`.

Login contro il tenant demo (creato da `scripts.seed`):

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"tenant_slug":"demo","email":"owner@demo.local","password":"ChangeMe123!"}'
```

Nota: `JWT_SECRET`/`APP_SECRET`/`ENCRYPTION_KEY` devono essere valori reali generati (non la
stringa vuota di default in `.env.example`) perché la firma dei JWT abbia senso — copia
`.env.example` in `.env` e genera dei valori, es. con
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.

### Makefile

I target in `Makefile` (§148) presuppongono `make` e Docker installati. Su questa macchina
nessuno dei due è disponibile: i comandi equivalenti sono quelli sopra.

## Regole di sviluppo

Vedi la sezione "Accordi di lavoro per questo repo" in [ROADMAP.md](ROADMAP.md#accordi-di-lavoro-per-questo-repo-202204):
niente pseudo-codice, niente funzioni vuote, niente integrazioni simulate spacciate per reali,
niente feature dichiarata "done" senza test e senza superare la sua Definition of Done.
