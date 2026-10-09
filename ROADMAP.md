# AI Business OS — Roadmap

Fonte: specifica tecnica fornita il 2026-09-05 (205 sezioni). Questa roadmap traduce quella
specifica in milestone sequenziali e verificabili, seguendo l'ordine di sviluppo obbligatorio
di §201 (STEP 1–16) e raggruppando il lavoro nelle fasi MVP di §151–154.

Regola (§201 / §203): **non iniziare una milestone finché la precedente non supera la sua
Definition of Done.** DoD per ogni ticket (§204):
codice implementato → migration creata (se applicabile) → API funzionante → permessi
verificati → test passati → errori gestiti → audit implementato → frontend collegato (se
applicabile) → documentazione aggiornata.

Legenda stato: `[ ]` da iniziare · `[~]` in corso · `[x]` completato

---

## Fase 0 — MVP Fase 1 (§151): il nucleo operativo

Tutto quanto sotto deve funzionare prima di iniziare la Fase 2. Il test di uscita per l'intera
fase è lo scenario a 20 passi di §200 (arriva un'email → viene classificata → si crea/valuta un
lead → compare in dashboard → l'AI propone una risposta → l'utente approva → l'email parte →
l'audit trail è completo → il CEO chiede "quali sono i lead migliori di oggi?" e ottiene una
risposta reale basata sui dati).

### M1 — Infrastruttura (§201 STEP 1, §2–4, §146–150)
- [x] Scheletro repo secondo §5 (`apps/`, `core/`, `modules/`, `agents/`, `tools/`,
      `integrations/`, `workflows/`, `tests/`, `scripts/`, `migrations/`, `docs/`, `docker/`)
- [x] `docker-compose.yml` con i servizi minimi (§4): frontend, backend, postgres, redis,
      worker, scheduler, ollama, reverse-proxy — **scritto, non ancora verificato** (Docker non
      disponibile su questa macchina di sviluppo)
- [x] `.env.example` secondo §146
- [x] `Makefile` con i target di §148 (install/start/stop/logs/migrate/seed/test/lint/backup/restore)
- [x] Scheletro FastAPI (`apps/api`) che si avvia, `GET /health` risponde (§113) — verificato
      con `uvicorn` + `curl`
- [x] Scheletro Next.js (`apps/web`) che si avvia e si collega all'API — verificato in browser
      (build di produzione pulita, dev server chiama `/health` e mostra lo stato live)
- [x] Standard di codice attivi: ruff/mypy strict/black (backend, puliti), eslint/tsconfig
      strict (frontend, puliti) (§155)
- [x] README.md, CHANGELOG.md, TODO.md inizializzati e mantenuti aggiornati da qui in poi (§202)

**DoD:** `docker compose up -d` porta su tutti i servizi in stato healthy; `/health` risponde
200 con tutti i sottosistemi `"online"` (stato stub accettabile finché le integrazioni reali
non esistono).

**Stato reale:** verificato tutto tranne l'avvio effettivo via Docker Compose (Docker non
installato su questa macchina — vedi TODO.md). Backend e frontend sono stati avviati ed
esercitati direttamente (senza container) con esito positivo.

### M2 — Database (§201 STEP 2, §17–29)
- [x] Schema PostgreSQL, PK UUID, ogni tabella business ha
      `id, tenant_id, created_at, updated_at, created_by, updated_by, deleted_at` (§17) —
      `core/database/base.py` (`TenantScopedMixin`)
- [x] Alembic configurato, prima migration committata (§149) — `migrations/env.py` +
      `migrations/versions/592b99656f58_initial_schema.py`
- [x] Tabelle: `tenants` (§18, `core/auth/models.py`), `users`/`roles` (§19–20, idem),
      `companies` (§22, `modules/companies/models.py`), `contacts` (§23,
      `modules/contacts/models.py`, con tracciamento consenso §135-137 fin da subito),
      `leads` (§24–25, `modules/leads/models.py`), `deals` (§26, `modules/deals/models.py`),
      `pipelines`/`pipeline_stages` (§28, `modules/pipeline/models.py`), `activities` (§29,
      `modules/crm/models.py`)
- [x] Indici: `tenant_id` su ogni tabella business + indici compositi mirati (status lead,
      stage deal, email contatto/utente, occurred_at activity) — non essendo disponibile il
      testo di §183 in questa sessione, la scelta segue i pattern di query più ovvi per ogni
      tabella (vedi TODO.md)
- [x] Script di seed (`scripts/seed.py`, idempotente): tenant demo, ruolo Owner, utente owner,
      pipeline standard a 7 stage (§150)

**DoD:** `make migrate && make seed` produce un tenant demo funzionante con la pipeline
standard (§28) verificabile via query diretta al DB.

**Stato reale:** verificato end-to-end contro un PostgreSQL 16 reale locale (non Docker — vedi
TODO.md): `alembic upgrade head` crea le 10 tabelle, `python -m scripts.seed` crea
tenant/ruolo/utente/pipeline verificati via `psql` diretto, e un test di integrazione
(`tests/integration/test_schema.py`) esercita ogni tabella (insert/relazioni/vincolo unique)
contro lo stesso database reale.

### M3 — Auth + RBAC (§201 STEP 3, §20–21, §103)
- [x] Hashing password Argon2id (`core/security/passwords.py`, da M2); JWT access token a breve
      scadenza (`core/security/tokens.py`) + refresh token opaco con rotazione e rilevazione
      del riutilizzo (revoca l'intera catena se un token già ruotato viene riusato); hook MFA
      (`/auth/mfa/setup` genera e salva un secret TOTP reale — l'enforcement al login resta da
      fare, vedi TODO.md)
- [x] Tabella `roles` con permessi stringa `resource.action` (già da M2); dependency
      `require_permission()` (`core/auth/dependencies.py`) che la interpreta con wildcard
      (`"*.*"`, `"resource.*"`)
- [x] `/api/v1/auth/login`, `/logout`, `/refresh`, `/me`, `/password/reset/request`,
      `/password/reset/confirm`, `/mfa/setup` (`apps/api/routes/auth.py`)
- [x] `get_current_user`/`require_permission` sono le dependency riutilizzabili da ogni route
      futura (M4+) — non reimplementare il controllo permessi altrove
- [x] Test di sicurezza isolamento tenant (`tests/security/test_tenant_isolation.py`): un JWT
      con lo stesso `user_id` ma un `tenant_id` diverso da quello reale non risolve a nessun
      utente

**DoD:** login → JWT → richiesta autenticata → RBAC nega un utente senza permesso; un test
automatico dimostra che l'accesso cross-tenant è impossibile.

**Stato reale:** verificato sia via test automatici (19/19 verdi, inclusi
`tests/integration/test_auth.py` e `tests/security/test_tenant_isolation.py`) sia manualmente
via `curl` contro il tenant demo reale (login, `/me`, rotazione refresh, rilevazione riutilizzo,
tutti osservati con l'esito atteso).

### M4 — CRM interno (§201 STEP 4, §22–29, §38, §81–84)
- [ ] Livelli service/repository secondo §157–160 (route → service → domain → repository → DB)
- [ ] CRUD + endpoint REST per Companies/Contacts/Leads/Deals (§81–84)
- [ ] Modello dati pipeline kanban + `POST /deals/{id}/stage|win|lose` (§84, §194)
- [ ] Implementazione `CRMConnector` interno (§38) — è il CRM di default prima di qualsiasi
      connettore esterno
- [ ] Eventi di dominio emessi (`lead.created`, `deal.stage_changed`, …) secondo §161–162, §76–77
- [ ] Tabella audit log + scrittura collegata a ogni mutazione (§100, §190)

**DoD:** creare un lead → azienda/contatto collegati o creati automaticamente → spostare un
deal tra stage di pipeline via API → ogni scrittura compare in `audit_logs` con dati
before/after.

### M5 — Ingestione email (§201 STEP 5, §30–34)
- [ ] `email_accounts` + storage del riferimento OAuth (nessun token grezzo nel DB) (§30, §104)
- [ ] Un connettore provider reale (Gmail o Microsoft — scegliere uno per l'MVP) che alimenta
      la tabella `emails`
- [ ] Pipeline email passo-passo secondo §32: ricezione → normalizzazione → thread detection →
      spam check → classificazione → estrazione entità → match contatto → match azienda →
      rilevazione lead → scoring → sync CRM → next action → notifica → audit
- [ ] Categorie di classificazione + output strutturato secondo §33 (validato con Pydantic,
      §167)

**DoD:** un'email reale in ingresso finisce nel DB con `category`, `confidence` e collegamento
al thread popolati automaticamente.

### M6 — Orchestrazione AI (§201 STEP 6, §7–16, §198–199)
- [ ] Astrazione `AIProvider` + `OllamaProvider` (locale) come minimo (§15)
- [ ] `ModelRouter` con configurazione di routing reale (classificazione→locale,
      generazione→modello cloud configurato, embeddings→locale) (§16)
- [ ] `BusinessOrchestrator.execute()` che implementa il ciclo OBSERVE→…→LEARN (§0, §7)
- [ ] Modelli `AgentRequest` / `AgentResult` esattamente come da specifica (§8–9)
- [ ] Interfaccia `BaseAgent` + `AGENT_REGISTRY` (§10–11), partendo solo con `EmailAgent`
- [ ] Sistema tool: decoratore `@tool(name, permission, risk)` + metadata (§12–14)
- [ ] Context builder che applica il principio "minimum necessary context" (§198–199)
- [ ] Tabella log `ai_executions` (costi/token/latenza) (§101–102)
- [ ] Confine anti prompt-injection: tutto il contenuto di email/documenti/pagine web è
      trattato come dato non fidato, mai come istruzione (§108) — la stessa regola sotto cui
      opera questa sessione

**DoD:** `POST /ai/chat` passa attraverso l'orchestrator, seleziona un modello via router,
chiama almeno un tool reale e registra una riga in `ai_executions` con `correlation_id`.

### M7 — Estrazione e scoring lead (§201 STEP 7, §35–37, §59)
- [ ] Schema strutturato di estrazione entità (§34) guidato dalla pipeline email (M5) tramite
      l'orchestrator (M6)
- [ ] Motore di scoring lead: formula pesata secondo §36, normalizzata 0–100
- [ ] Spiegazione dello score salvata insieme al punteggio (§37)
- [ ] Hook di scoring ICP match (§59) — può restare uno stub finché il prospecting (Fase 2 del
      roadmap) non arriva

**DoD:** un'email commerciale in ingresso produce un lead con punteggio numerico e lista di
motivazioni leggibili, end-to-end, senza passaggi manuali.

### M8 — Sistema di approvazione (§201 STEP 8, §47–55)
- [ ] Tabella `approval_requests` + macchina a stati (§47–48)
- [ ] API `GET/POST /approvals*` (§49)
- [ ] UI Action Center: approvazioni pendenti con Approve/Edit/Reject (§50)
- [ ] Livelli di autonomia: Copilot / Supervised / Autonomous, configurabili per tenant
      (§51–54)
- [ ] Policy engine `evaluate_policy(...)` (§55) che blocca almeno: invio email, modifica deal
      oltre soglia, delete, azioni finanziarie

**DoD:** un'email proposta dall'AI non può essere inviata senza che una riga di approvazione
passi a `APPROVED`, e la decisione del policy engine (allowed / requires_approval / reason) è
ispezionabile per ogni richiesta.

### M9 — Intelligenza pipeline vendite (§201 STEP 9, §42–46)
- [ ] Sales Agent che risponde alle cinque domande standard di §42 su dati reali
- [ ] `deal_health_score` (§43) + struttura output rischio (§44)
- [ ] Tabelle motore follow-up (`followup_sequences/steps/enrollments`, §45) + una sequenza
      seed (§46)
- [ ] Sistema task (§91–92) collegato ai passi di follow-up e alle raccomandazioni del Sales
      Agent

**DoD:** un deal senza attività da più di N giorni mostra un health score, una lista di motivi
di rischio e un'azione raccomandata, visibile via API e dashboard.

### Checklist di uscita Fase 0
- [ ] Lo scenario completo di §200 gira end-to-end contro servizi reali (non mock)
- [ ] L'audit log mostra ogni passo dello scenario
- [ ] Il CEO può chiedere "quali sono i lead migliori di oggi?" via `/ai/chat` e ottenere una
      risposta basata su dati reali del DB, non una risposta precostituita

---

## Fase 1 — MVP Fase 2 (§152) — STEP 10–12

### M10 — Connettori CRM esterni (§201 STEP 10, §39–41, §127–128)
- [ ] Adapter `CRMConnector`: scegliere il primo target esterno (HubSpot o Pipedrive) end to end
- [ ] Connettore REST generico + motore di field mapping (§40–41)
- [ ] Motore di sync: full / incremental / webhook (§125–127), policy di conflict resolution
      (§128)

### M11 — Motore di automazione (§201 STEP 11, §74–79)
- [ ] Schema workflow (trigger/condizioni/azioni/gestore errori) (§74)
- [ ] Event bus + struttura evento (§76–77), chiavi di idempotenza sulle scritture critiche
      (§78)
- [ ] Rilasciare l'automazione di riferimento "Inbound lead" di §75

### M12 — Knowledge base / RAG (§201 STEP 12, §66–73)
- [ ] Pipeline di ingestione (§70): upload → virus check → validazione → estrazione testo →
      normalizzazione → chunking → embedding → indicizzazione → ready
- [ ] Vector DB: pgvector o Qdrant (§67)
- [ ] Regola "cerca prima nella knowledge base" applicata alle risposte degli agenti (§71) —
      mai inventare quando viene chiesto un fatto aziendale non trovato
- [ ] Separazione business memory (§72–73)

### Anche in questa fase (§152)
- [ ] Servizio notifiche multicanale (§93–94)
- [ ] Job briefing giornaliero CEO (§95) + calcolo forecast vendite (§96) + set KPI (§97) +
      dashboard CEO (§98) + motore raccomandazioni (§99)
- [ ] Monitor attività AI via WebSocket (§118–119)

---

## Fase 2 — Fase 3 (§153) — STEP 13–15
- [ ] M13 Modulo social (§60–65) — generazione contenuti, brand profile, pubblicazione con
      approvazione (§138), calendario marketing (§65)
- [ ] M14 Analytics (§97, reportistica avanzata, export CSV/XLSX/PDF §187)
- [ ] M15 Assistente vocale (§131) — STT/AI/TTS, agnostico dal provider
- [ ] Meeting intelligence (§130), prospecting avanzato (§56–59), revenue forecast (§96)

## Fase 3 — Fase 4 (§154) — STEP 16
- [ ] M16 Hardening SaaS multi-tenant, billing/abbonamenti, limiti di utilizzo, portale
      cliente esterno, integrazioni marketplace, workflow builder avanzato

---

## Requisiti trasversali (valgono per ogni milestone, non sono step a sé)

Non sono step separati — vengono verificati nella DoD di ogni milestone:

- **Sicurezza** (§103–110, §144): nessuna chiave hardcoded, nessun segreto in chiaro,
  whitelist di tool per agente, l'AI non riceve mai credenziali DB grezze, confine
  anti prompt-injection rispettato
- **Osservabilità** (§111–114): log JSON strutturati, Prometheus/Grafana/Loki, endpoint
  `/health` mantenuto accurato man mano che si aggiungono servizi
- **Testing** (§140–146): test unitari per scoring/permessi/policy/mapping/health-score/
  condizioni workflow; test di integrazione contro provider mockati; il test di isolamento
  tenant è non negoziabile e gira da M3 in poi
- **Compliance** (§135–137): tracciamento consenso sui contatti dal momento in cui esiste
  `contacts` (M2), controlli di suppression-list + consenso prima che qualsiasi capacità di
  invio venga rilasciata (M5/M8)
- **Controllo costi** (§102, §173): log esecuzioni AI e controllo budget giornaliero vengono
  rilasciati insieme all'orchestrator (M6), non aggiunti dopo

## Non-obiettivi espliciti prima della rispettiva milestone
- Nessuna chiamata a LLM cloud per dati classificati RESTRICTED prima che esista il Privacy
  Router (§107) — default al modello locale fino ad allora
- Nessun invio/pubblicazione autonomo prima che esista il Sistema di Approvazione (M8) —
  comportamento solo Copilot (§52) fino ad allora
- Nessun SQL generato direttamente contro produzione a partire da linguaggio naturale — il
  Query DSL (§89–90) è obbligatorio prima che qualsiasi funzione di query NL venga rilasciata

## Accordi di lavoro per questo repo (§202–204)
- Niente pseudo-codice, funzioni vuote o integrazioni "simulate" presentate come completate
- Nessun dato mock senza etichettarlo esplicitamente come tale nel codice e in TODO.md
- Una feature non è "done" finché la sua checklist DoD (in cima a questo file) non è
  completamente spuntata
- Questo file, README.md, CHANGELOG.md e TODO.md vengono aggiornati come parte del completamento
  di una milestone, non a posteriori
