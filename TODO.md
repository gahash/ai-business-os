# TODO tecnico

Stato tecnico corrente del progetto. Aggiornato ad ogni milestone completata (vedi
[ROADMAP.md](ROADMAP.md) per il dettaglio di ciascuna).

## Milestone corrente

**M1 — Infrastruttura**, **M2 — Database**, **M3 — Auth + RBAC**: completate (vedi ROADMAP.md).

M3 — fatto:
- [x] JWT access token (`core/security/tokens.py`) + refresh token opaco con rotazione e
      rilevazione del riutilizzo (`RefreshToken.replaced_by_id`, revoca l'intera catena su
      riuso)
- [x] `core/auth/dependencies.py`: `get_current_user` (valida JWT, richiede match esatto
      user_id+tenant_id — è qui che vive l'invariante di isolamento tenant) e
      `require_permission("resource.action")` (wildcard-aware, riutilizzabile da ogni route)
- [x] `apps/api/routes/auth.py`, montate su `/api/v1/auth`: login, logout, refresh, me,
      password/reset/request, password/reset/confirm, mfa/setup
- [x] Migration `0febe9487ef2`: tabelle `refresh_tokens`/`password_reset_tokens`, colonne
      `users.mfa_enabled`/`mfa_secret`
- [x] Test: `tests/unit/test_permissions.py` (matching permessi, dependency isolata con
      `dependency_overrides`), `tests/integration/test_auth.py` (flusso completo contro Postgres
      reale), `tests/security/test_tenant_isolation.py` (§145, non negoziabile da qui in poi)
- [x] `.env` locale creato con secret reali generati (APP_SECRET/JWT_SECRET/ENCRYPTION_KEY) —
      necessario perché il default di `Settings` è stringa vuota

Limitazioni note introdotte da M3 (da chiudere quando le rispettive milestone arrivano):
- **MFA non applicata al login**: `/mfa/setup` genera e salva un secret TOTP reale, ma non
  esiste ancora un passo di verifica/conferma né un controllo al login che lo richieda. È
  esplicitamente uno "hook" (come da roadmap), non l'enforcement completo — da fare quando
  serve davvero, non a metà ora.
- **`/password/reset/request` restituisce il token direttamente nella risposta HTTP** invece di
  spedirlo via email, perché l'invio email non esiste fino a M5. Questo permette a chi conosce
  tenant+email di un account di confermarne l'esistenza (piccola fuga d'informazione) — quando
  M5 collega un provider email reale, questo endpoint deve smettere di restituire il token e
  inviarlo solo via email, con risposta uniforme indipendentemente dal fatto che l'account esista.
- Nessun endpoint business (companies/contacts/leads/deals) esiste ancora per dimostrare
  `require_permission` su una risorsa reale — dimostrato invece con un test unitario isolato
  (`tests/unit/test_permissions.py`); M4 lo eserciterà per davvero su ogni route CRUD.

Prossima milestone: **M4 — CRM interno** (vedi ROADMAP.md).

M2 — fatto:
- [x] Schema PostgreSQL reale (10 tabelle) con mixin condiviso `TenantScopedMixin`
      (`core/database/base.py`): `id, tenant_id, created_at, updated_at, created_by,
      updated_by, deleted_at` su ogni tabella business
- [x] Alembic configurato e collegato ai `Settings`/modelli reali (`migrations/env.py`),
      prima migration generata via autogenerate e applicata (`migrations/versions/
      592b99656f58_initial_schema.py`)
- [x] Modelli: `Tenant`/`Role`/`User` (`core/auth/models.py`), `Company`
      (`modules/companies/models.py`), `Contact` (`modules/contacts/models.py`, con
      `consent_status`/`consent_captured_at` già presenti), `Lead`
      (`modules/leads/models.py`), `Deal` (`modules/deals/models.py`), `Pipeline`/
      `PipelineStage` (`modules/pipeline/models.py`), `Activity` (`modules/crm/models.py`)
- [x] Script di seed idempotente (`scripts/seed.py`): tenant demo, ruolo Owner
      (`permissions=["*.*"]`), utente owner, pipeline standard a 7 stage
- [x] Test di integrazione reale (`tests/integration/test_schema.py`) contro Postgres vero:
      round-trip su tutte le tabelle + verifica vincolo unique tenant+email
- [x] `core/security/passwords.py`: hashing Argon2id (usato dal seed; gli endpoint auth
      arrivano in M3)

Da fare per chiudere M2 del tutto:
- [ ] Verificare la stessa migration anche contro Postgres via Docker quando disponibile
      (qui verificato contro un Postgres nativo, non containerizzato — vedi limitazioni sotto)

## Limitazioni note dell'ambiente di sviluppo corrente

- **Docker non installato** su questa macchina → `docker-compose.yml` non è stato eseguito,
  solo scritto secondo spec. Verificare appena disponibile un ambiente con Docker.
- **PostgreSQL reale ma non via Docker**: per sbloccare M2 è stato installato PostgreSQL 16
  nativo tramite il pacchetto Python `pgserver` (binari reali, nessun installer/servizio
  Windows — il download diretto dell'installer EnterpriseDB era bloccato dalla rete di questa
  sandbox, 403 su CloudFront). Gestito da `scripts/dev_postgres.py`
  (`make db-start` / `make db-stop`), dati in `.devdb/` (gitignored), ascolta su
  `127.0.0.1:5432` — stesso host/porta che userebbe `docker-compose.yml`. Non è un setup di
  produzione.
- **`make` non installato** (Git Bash / Windows) → i target del `Makefile` non sono stati
  eseguiti direttamente; gli stessi comandi sono stati lanciati a mano (vedi README.md,
  sezione "Setup locale senza Docker").
- **Python 3.11.8 disponibile** (via `py -3.11`), non 3.12+ come indicato dalla spec (§2).
  Il codice non usa ancora feature specifiche di 3.12: nessun blocco noto, ma da rivalutare se
  si installa 3.12.
- **Testo completo della specifica tecnica (205 sezioni) non disponibile in questa sessione**:
  solo il riassunto già trascritto in ROADMAP.md. Lo schema M2 è stato progettato secondo
  pattern CRM standard coerenti con quel riassunto, non ricopiato da un testo di sezione
  puntuale per §17-29/§183 — da riconciliare con la spec completa se emergono differenze.
- `make backup` / `make restore` puntano a `scripts/backup.sh` / `scripts/restore.sh`, non
  ancora implementati (arrivano con §115, fuori da M1/M2).

## Debito tecnico noto

_Nessuno oltre alle limitazioni d'ambiente sopra elencate._

## Dati mock in uso

_Nessuno._

## Decisioni in sospeso

- Provider email per M5: Gmail vs Microsoft — da scegliere prima di iniziare M5
- CRM esterno per M10: HubSpot vs Pipedrive — da scegliere prima di iniziare M10
- Vector DB per M12: pgvector vs Qdrant — da scegliere prima di iniziare M12
- Modello locale (Ollama) e modello cloud da configurare nel `ModelRouter` — da decidere entro M6
