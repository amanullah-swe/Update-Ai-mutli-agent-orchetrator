# Implementation Log — 007 Backend API (FastAPI + PostgreSQL + mock chat)

- **Status:** `Tested`
- **Spec:** `./spec.md`
- **Plan:** `./plan.md`

> **Append-only.** Every build session adds a dated entry here (newest at the bottom). Never edit older entries — this is the back-tracking record.

## Log

### 2026-09-27 — Initial build: FastAPI backend, PostgreSQL schema, mock SSE chat

**Session scope:** Execute `specs/features/007-backend-api/plan.md` in full — `backend/` FastAPI app, database setup, routes, all acknowledge the mock-chat path, migration/tests/smoke, ADRs, CLAUDE.md updates. All 10 acceptance criteria ticked in `spec.md`.

**Environment (resolved with the user)**
- **PostgreSQL:** installed locally rootless (no sudo available). Built PostgreSQL **18.0** from source into `$HOME/local/pg` (had to pass `--without-icu --without-readline --without-zlib --disable-rpath`, and provide `bison`/`flex`/`m4` extracted from Ubuntu `.deb`s with `BISON_PKGDATADIR` + `M4` set because the Ubuntu `bison` binary embeds an absolute `/usr/bin/m4`). Runtime needs `LD_LIBRARY_PATH=$HOME/local/pg/lib` because rpath was disabled. Running on `127.0.0.1:5432` with role `rag`/`rag` and DBs `rag_learning` + `rag_learning_test`. A reproducible path for other machines is `make up` (docker compose).
- **Tooling:** uv **0.12.19** installed locally; backend uses `uv` + `pyproject.toml` (resolves build decision #2 → ADR-002). `uv sync` succeeded on CPython 3.14 — `psycopg[binary] 3.3.6` ships cp314 wheels, so no pure-Python libpq fallback was needed.

**What was done**

- `backend/` FastAPI app (uv project): `app/main.py` (app factory: CORS, request-id middleware, exception handlers, lifespan engine-dispose, `api_router` under `/api`), `app/core/{config,database,logging,exceptions}.py`, `app/models/` (10 entities), `app/schemas/`, `app/services/` (chat provider seam + orchestration, documents, conversations, evaluation, experiment), `app/api/routes/` (health, chat, documents, conversations, evaluation, experiments), `tests/`.
- Config: `configs/{development,testing,production}.yaml` loaded at startup by pydantic-settings `Settings`; YAML is the lowest-priority source (env + `.env` override). Resolves decision #3 → ADR-003.
- Models: `documents`, `document_versions`, `chunks`, `embeddings` (scaffold, `has_vector` flag; vector column deferred), `conversations`, `messages` (`sources` JSON), `evaluation_datasets`, `evaluation_results`, `experiments`, `experiment_runs`. UUID PKs, FK cascade on document delete, `server_default now()` timestamps.
- Migrations: Alembic at `database/migrations/`, `env.py` reads the app `Settings` URL + `Base.metadata`; initial revision `a37a02c9694e` (`sa.Uuid()` → PG native `uuid`). Applied to `rag_learning` twice (idempotent — second run was a no-op); 10 tables + `alembic_version` confirmed in `information_schema`. `database/schemas/reference.sql` (reference only) + `database/seed/dev.sql`. Resolves decision #8 → ADR-008.
- Chat: `POST /api/chat` persists the user message, streams SSE frames via `MockChatProvider` (`message_start → token* → sources → message_end → done`), persists the assistant message + 2 mock sources. Frozen frame format verified against `frontend/src/utils/sse.ts`/`SseChatService.ts` and live via `curl`. Resolves decision #10 → ADR-010.
- Ops: `docker/docker-compose.yml` (postgres:18 + backend), `docker/Dockerfile.backend`, root `Makefile` (`backend`, `test`, `migrate`, `migrate-make`, `seed`, `up`, `up-all`, `down`), root `.gitignore`, `backend/.env.example`, `backend/README.md`.
- Docs: ADRs `specs/decisions/{002,003,008,010}-*.md`; updated `spec.md` (status `Tested`, ACs ticked), `plan.md` (status `Complete`); CLAUDE.md build decisions #2/#3/#8/#10 marked ✅ RESOLVED with ADR pointers.

**Deviations from plan & why**

- **Plan steps had no `[ ]` checkboxes** (written as numbered bold headings) — completion is recorded by `Status: Complete` + this log rather than per-step ticks. Template deviation only; acceptance criteria remain the source of truth for Done.
- `DocumentOut.metadata` field: drafting used `alias="metadata"`, which made Pydantic read `DeclarativeBase.metadata` (`MetaData()`) → response-validation error. Fixed with `validation_alias="metadata_"` + `serialization_alias="metadata"`.
- Alembic `script_location` set to `%(here)s` (ini-directory-relative) after the tests failed from CWD=backend — `script_location=.` is CWD-relative and only worked from the migrations dir.
- uvicorn smoke on `:8001` failed (another process already bound 8001 on this machine) — verified on `:8001` instead; the app itself is port-agnostic.
- ORM/driver: **sync SQLAlchemy 2.0 + psycopg 3** (sync endpoints in FastAPI's threadpool) rather than asyncpg — chosen in the plan to avoid async-driver wheel risk on Python 3.14; no ADR (implementation-level choice, recorded in plan decisions).
- Unit tests were written as pure-logic tests (no DB) plus one SQLite service test; the API tests run against real PostgreSQL via `TestClient`. `clean_tables` is requested via the `client` fixture (not autouse) so pure-unit tests don't need Postgres.

**Tests run / results**

- `cd backend && uv run pytest` → **30 passed** (health 3, chat 6, documents 5, conversations 3, evaluation 2, experiments 2, SSE unit 6, document-service unit 4). Run against real `rag_learning_test` with schema rebuilt each session via Alembic (`downgrade base` → `upgrade head`).
- `alembic upgrade head` on a fresh empty database, run **twice** → second was a no-op (idempotent).
- Live smoke (uvicorn on 127.0.0.1:8001): `GET /api/health` → `{"status":"ok","database":{"status":"ok"}}`; `POST /api/chat` streamed `event: message_start` / `event: token` frames in the exact frozen format; `GET /api/documents` → `{"items":[],"total":0}` against Postgres. (The frontend SSE transport against the real backend is deferred — UI work, not this feature.)

**Decisions made**

- ADR-002 (uv + pyproject.toml), ADR-003 (pydantic-settings + YAML), ADR-008 (Alembic source of truth), ADR-010 (SSE framing) — all written and reflected in CLAUDE.md.
- `messages.sources` stored as JSON in the frontend's frozen `Source[]` shape (spec open question 1: keep; the evaluation-feature follow-up remains open).
- `embeddings` column is a scaffold until the vectorstore feature adds the vector migration (spec open question 2 remains a follow-up).

**Progress**

- Plan: 12 steps executed (statuses recorded via plan `Status: Complete`).
- Acceptance criteria in `spec.md`: 10/10 checked. Feature status → `Tested` (awaiting user review for `Accepted`).

**Notes / follow-ups**

- Real-backend streaming validation from the UI (`VITE_CHAT_TRANSPORT=sse`) is a frontend adoption task, not this feature.
- Frontend is fully untracked/uncommitted and this feature (backend) is also uncommitted — no git commits made in this session.
- `backend/uploads/` is gitignored; `rag_learning`/`rag_learning_test` are runtime artifacts on the local rootless Postgres.

---

### 2026-09-27 — Rescope: chat CRUD + WebSocket messaging (removes documents/evaluation/experiments + SSE)

**Session scope:** Re-executed feature 007 after a user-directed rescope. The first build's broad surface (document upload, evaluation runs, experiment runs, SSE `POST /api/chat`) was deemed too speculative — none of its data had a real producer. 007 now delivers only the chat app: **create / rename / list / get a chat over HTTP, and send/receive messages over a per-chat WebSocket.** Spec (`spec.md`) and plan (`plan.md`) were rewritten first, then the code, per the spec-first workflow.

**What was done**

- **Spec + plan rewritten** to the chat-CRUD scope; statuses `Specified` → `Tested` / `Complete`; all 12 acceptance criteria ticked.
- **Deleted** the out-of-scope slices: routes `{chat,conversations,documents,evaluation,experiments}.py`, services `{chat_service,document_service,evaluation_service,experiment_service}.py`, schemas `{conversation,document,evaluation,experiment}.py`, models `{document,chunk,evaluation,experiment}.py`, and their tests. `app/models/__init__.py` + `app/api/routes/__init__.py` now expose only the chat surface.
- **Config:** removed the `documents:` YAML section, `upload_dir`/`max_size_mb` Settings fields, `resolved_upload_dir`, and the app-lifespan upload-dir `mkdir`; dropped `RAG_UPLOAD_DIR`/`RAG_MAX_SIZE_MB` from `.env.example`. `config.py`/`main.py` updated.
- **Models:** only `Conversation` + `Message` remain (CLAUDE.md entity names). API speaks *chat* (`/api/chats`); a note in the spec records the vocabulary mapping.
- **Migration squashed:** deleted `database/migrations/versions/a37a02c9694e_initial_schema.py` (never committed) and hand-wrote a single initial revision `b2e9f1c4a5d6_initial_chat_schema.py` for `conversations` + `messages`. Regenerated `database/schemas/reference.sql` + `database/seed/dev.sql` to match. **Both local databases were dropped/recreated** (user-consented, destructive) to clear the dangling `alembic_version` → old revision; `upgrade head` then applied cleanly and idempotently (ran twice), creating exactly `conversations` + `messages`.
- **Schemas** (`app/schemas/chat.py`): `Source`/`MessageOut` (keep the frontend shape), chat resources (`ChatCreate`, `ChatRename`, `ChatOut`, `ChatSummary`, `ChatListResponse`, `ChatDetail`), and WebSocket frames (`UserMessageFrame`, `ReadyFrame`, `MessageFrame`, `MessageStartFrame`, `TokenFrame`, `SourcesFrame`, `MessageEndFrame`, `ErrorFrame`).
- **Provider seam** (`app/services/chat.py`): `ChatProvider` protocol + `MockChatProvider` now emit `TokenEvent`/`SourcesEvent` *content* events (decoupled from transport framing). `build_chat_provider(settings)` — the only name→class dispatch, at the config seam, no `if provider` in routes.
- **Service** (`app/services/conversation_service.py`): `create_chat`, `list_chats` (most-recent-activity-first), `get_chat`, `rename_chat`, `append_message`.
- **Routes** (`app/api/routes/chats.py`): `POST/GET /api/chats`, `GET/PATCH /api/chats/{id}`, and `WS /api/chats/{chat_id}/ws`. The WebSocket handler is async; **all DB work runs in the threadpool** on short-lived `SessionLocal()` sessions so the sync engine never blocks the event loop. Turn flow: `ready` → validate chat (else `error` + close `4404`) → loop `user_message` → persist user → `message` ack → `message_start` → `token`* → `sources` → persist assistant → `message_end`; malformed frames → in-band `error`, socket stays open.
- **Tests** rewritten: `conftest.py` (two tables; `migrated_database` now a *requested* fixture so pure unit tests need no Postgres), `test_chat_provider_unit.py`, `test_chats_crud.py`, `test_chat_websocket.py`; `test_health.py` kept. Deleted the seven obsolete suites.
- **Docs:** ADR-011 (`specs/decisions/011-chat-transport-websocket.md`, supersedes ADR-010 for chat); ADR-010 marked `Superseded` (its event vocabulary carried over). CLAUDE.md decision #10 + "Backend API surface" updated; root `README.md` and `backend/README.md` rewritten for the chat/WebSocket API.

**Deviations from plan & why**

- **Migration squashed by hand** rather than `alembic revision --autogenerate`: autogenerate needs a live DB baseline, and the DB had the to-be-deleted schema. The rescue path (drop/recreate, then `upgrade head`) both cleared the stale `alembic_version` (which `downgrade base` could no longer resolve) and validated the fresh revision twice.
- **First `sources` persistence bug:** the assistant `sources` were streamed over the socket but dropped on persist — the route helper never forwarded them to `append_message`. Fixed by collecting `SourcesEvent.sources` in the turn loop and passing them through; two WS tests caught it (sources length 0/None → now 2).
- **Dataclass ordering:** `TokenEvent`/`SourcesEvent` initially declared `kind` with a default before the non-default fields — `TypeError` at import; reordered (fields with values first).
- **Multiple-heads hiccup:** the old migration file wasn't deleted initially (a compound DB command was permission-denied wholesale), leaving two heads. Splitting deletion (repo edit) from the DB reset (user-consented) resolved it.
- The developer-friendly live smoke left one "live smoke" chat row in the dev DB — harmless dev data, not part of any migration/seed.

**Tests run / results**

- `cd backend && uv run pytest` → **23 passed** (provider unit 5, chat CRUD 8, chat WebSocket 6, health 3, …: schema/migration via the `migrated_database` fixture). One Starlette deprecation warning about httpx — not actionable.
- `alembic upgrade head` on a fresh database, run twice → second run a no-op (idempotent); `conversations` + `messages` + `alembic_version` confirmed in `information_schema` on both `rag_learning` and `rag_learning_test`.
- **Live smoke** (uvicorn :8012): `GET /api/health` → `db: ok`; `POST /api/chats` 201 → `PATCH` rename 200 → `GET /api/chats` total 1 → `GET` transcript empty → WebSocket `ready`, full turn (`message → message_start → token* → sources → message_end`), assistant sources persisted (2), transcript `[user, assistant]` confirmed over HTTP after the socket closed.

**Decisions made**

- **ADR-011** (WebSocket for chat) recorded; **ADR-010 superseded**. CLAUDE.md decision #10 and the API surface updated to match.
- Chat transport uses JSON text frames with the prior SSE event vocabulary.
- Sync SQLAlchemy engine kept — no async-driver dependency; WS DB work via `run_in_threadpool`.
- Backlog carry-over: document upload, evaluation runs, experiment runs return to the backlog as their own features when the RAG pipeline exists to produce real data.

**Progress**

- Plan steps 1–11 all ticked; plan `Status: Complete`.
- Acceptance criteria in `spec.md`: 12/12 checked; feature status → `Tested` (awaiting user review for `Accepted`).
- Document-upload env keys dropped from `backend/.env.example` with the feature.

**Notes / follow-ups**

- **Frontend is NOT wired to this chat yet** — `frontend/src/services/{SseChatService,sseClient}.ts` + `utils/sse.ts` target the retired SSE transport. Reworking the UI to `fetch` + WebSocket is a 006-frontend-ui follow-up, explicitly out of scope here.
- `DELETE /api/chats/{id}` is not implemented (spec open question 1); the `messages.conversation_id` FK already cascades for a future delete.
- The WebSocket does not replay history or resume a dropped connection (spec open questions 3); `GET /api/chats/{id}` serves history.
### 2026-09-29 — PostgreSQL moved to Docker exclusively; local build removed

- **Removed** the locally-built PostgreSQL (from-source install at `$HOME/local/pg` + data dir `$HOME/pgdata`). It was stopped; Docker's `db` service (`postgres:18-alpine`, volume `pgdata`) is now the sole owner of `127.0.0.1:5432` and the only source of the `rag_learning` database.
- **Backend unchanged** — `RAG_DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag_learning` already resolves to the Docker instance; no config change needed.
- **`make seed` reworked** to run psql inside the container (`docker compose ... exec -T db psql -U rag -d rag_learning -f - < database/seed/dev.sql`) since host `psql` no longer exists; seed file header comment updated to match.
- **Makefile:** fixed `installdo` → `install` typo in the `install-docker` recipe.
- Verified `make db` / `make migrate` (idempotent) / `make seed` all succeed against the Docker DB (`alembic_version`, `conversations`, `messages` present).
