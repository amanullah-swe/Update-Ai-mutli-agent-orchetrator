# Plan — 007 Chat CRUD API (FastAPI + PostgreSQL + WebSocket messaging)

- **Status:** `Complete`
- **Last updated:** 2026-09-27
- **Spec:** `./spec.md`

> Written **after** the spec became `Specified` and **before** any code. Steps are executed in order and ticked off; deviations are recorded in `implementation.md`.

## Approach (one line)

Reduce the existing FastAPI app to its chat core: delete the documents/evaluation/experiments slices, squash the schema down to `conversations` + `messages`, expose chats as CRUD over HTTP (`/api/chats`), and move message send/receive onto a per-chat WebSocket whose assistant side streams from a `ChatProvider` implementation selected by config.

## Decisions (resolving the spec's open questions)

| Choice | Decision |
| --- | --- |
| Transport | **WebSocket** at `/api/chats/{chat_id}/ws`, JSON text frames discriminated by `type`; ADR-011 supersedes ADR-010 (SSE). |
| Provider seam | Keep `ChatProvider` (interface) + `MockChatProvider`; routes/services hold the interface only. Config `chat.provider`. |
| Sync DB in async WS handler | The engine stays **sync SQLAlchemy 2.0 + psycopg 3** (per the prior build). WebSocket handlers are `async` and run in the event loop, so all DB work is dispatched via `starlette.concurrency.run_in_threadpool` with short-lived sessions — no blocking I/O on the loop. |
| Migration history | **Squash**: delete revision `a37a02c9694e` (ten tables, never committed) and generate one fresh initial revision for `conversations` + `messages`. Requires dropping/recreating the local `rag_learning` + `rag_learning_test` databases (or `DROP TABLE alembic_version`) so no dangling revision reference remains. |
| API vocabulary | Routes/schemas speak **chat** (`/api/chats`); models/tables keep CLAUDE.md's **conversations**/**messages**. |
| Mock assistant content | Reuse the existing canned markdown answer, now emitted as provider events over the socket. Keeps the seam honest and the traceability contract (mock sources) visible. |
| `sources` | Keep `json` on `messages` + `Source` schema; optional `sources` frame. |
| Delete chat | Out of scope (spec open question 1) — no `DELETE` route. |
| Auto-titling | Dropped; chats are created with a client-supplied title (or `null`) and renamed via `PATCH`. |
| Document upload config | `documents:` YAML section and `upload_dir`/`max_size_mb` Settings fields removed with the feature. |

## Steps (do these in order)

1. [x] **Delete the out-of-scope slices** — remove the documents/evaluation/experiments routes, services, schemas, models, and their tests; drop their table imports from `app/models/__init__.py` and their routers from `app/api/routes/__init__.py`. Touches: `backend/app/{api/routes,services,schemas,models}/…`, `backend/tests/…`
2. [x] **Remove document config** — delete `documents:` from `configs/*.yaml`, the `upload_dir`/`max_size_mb` Settings fields + `resolved_upload_dir`, and the uploads-dir creation in the app lifespan. Touches: `backend/app/core/config.py`, `backend/app/main.py`, `configs/*.yaml`, `backend/.env.example`
3. [x] **Chat models + transcript** — keep `Conversation`/`Message`, add `updated_at` semantics for rename; models now hold exactly those two entities. Touches: `backend/app/models/{__init__,conversation}.py`
4. [x] **Squash the migration** — delete `database/migrations/versions/a37a02c9694e_initial_schema.py`; drop/recreate the dev + test databases; autogenerate one initial revision for the two tables; regenerate `database/schemas/reference.sql` and `database/seed/dev.sql`. Touches: `database/**`
5. [x] **Chat schemas** — `app/schemas/chat.py`: `ChatCreate`, `ChatRename`, `ChatOut`, `ChatSummary`, `ChatListResponse`, `ChatDetail`, `MessageOut`, `Source`, and the WebSocket frame models (`UserMessageFrame`, and the server frames). One module for the chat contract. Touches: `backend/app/schemas/chat.py`
6. [x] **Chat service + provider** — `app/services/chat.py`: `ChatProvider` protocol + `MockChatProvider` emitting provider events (token/sources); `build_chat_provider(settings)`. `app/services/conversation_service.py`: `create_chat`, `list_chats`, `get_chat`, `rename_chat`, `append_message`, `resolve_provider_events`. Touches: `backend/app/services/{chat,conversation_service}.py`
7. [x] **HTTP chat routes** — `app/api/routes/chats.py`: `POST /api/chats`, `GET /api/chats`, `GET /api/chats/{id}`, `PATCH /api/chats/{id}`; delete `routes/chat.py` + `routes/conversations.py`. Touches: `backend/app/api/routes/{chats.py,__init__.py}`
8. [x] **WebSocket route** — `app/api/routes/chats.py` (same router): `WS /api/chats/{chat_id}/ws` — validate id → `ready`; loop over client frames; per turn: persist user message → `message` ack → stream provider events → persist assistant → `message_end`; in-band `error` frames; close `4404` for unknown chat. DB calls via `run_in_threadpool`. Touches: `backend/app/api/routes/chats.py`, `backend/app/core/database.py` (session factory helper if needed)
9. [x] **Tests** — rewrite `backend/tests/`: `conftest.py` (two tables only, real-Postgres migrations, `client` fixture, WS helper), `test_health.py`, `test_chats_crud.py` (create/rename/list/get/404/422), `test_chat_websocket.py` (frame sequence, persistence, multi-turn, bad frame, unknown chat 4404), `test_chat_provider_unit.py` (provider event sequence, no DB). Delete `test_chat.py`, `test_conversations.py`, `test_sse_unit.py`, `test_documents.py`, `test_evaluation.py`, `test_experiments.py`, `test_document_service_unit.py`. Touches: `backend/tests/**`
10. [x] **Docs + ADR** — write `specs/decisions/011-chat-transport-websocket.md` (supersedes 010, mark ADR-010 `Superseded`); update CLAUDE.md API surface + build decision #10; update root `README.md` and `backend/README.md` for the chat/WebSocket API; update the `Makefile` seed target if paths changed. Touches: `specs/decisions/**`, `CLAUDE.md`, `README.md`, `backend/README.md`
11. [x] **Verify** — `uv run pytest` green against real PostgreSQL; `alembic upgrade head` twice on a fresh DB (idempotent, two tables); live `uvicorn` smoke: create → rename → list → get over HTTP and one full WebSocket turn (via a small `websockets` client); tick the spec's acceptance criteria; append `implementation.md`.

## Files to create / modify

| Path | Purpose |
| --- | --- |
| `backend/app/api/routes/chats.py` | **new** — chat CRUD + WebSocket endpoint |
| `backend/app/api/routes/__init__.py` | only `health` + `chats` routers |
| `backend/app/schemas/chat.py` | **rewritten** — chat resources, message contract, WS frame models |
| `backend/app/services/chat.py` | **rewritten** — provider interface, mock provider, provider-event vocabulary |
| `backend/app/services/conversation_service.py` | **rewritten** — chat CRUD + message persistence |
| `backend/app/models/{__init__,conversation}.py` | two entities only |
| `backend/app/core/config.py` | drop document settings |
| `backend/app/main.py` | drop upload-dir lifespan work |
| `configs/{development,testing,production}.yaml` | drop `documents:` |
| `database/migrations/versions/<new>_initial_chat_schema.py` | **new** single initial revision (2 tables) |
| `database/schemas/reference.sql`, `database/seed/dev.sql` | regenerated to match |
| `backend/tests/**` | rewritten suites + WS helper |
| `specs/decisions/011-chat-transport-websocket.md` | **new** ADR |
| `specs/decisions/010-streaming-transport.md` | mark `Superseded by ADR-011` |
| `CLAUDE.md`, `README.md`, `backend/README.md` | chat/WebSocket surface + decision #10 |
| **deleted** | `backend/app/api/routes/{chat,conversations,documents,evaluation,experiments}.py`, `backend/app/services/{chat_service,document_service,evaluation_service,experiment_service}.py`, `backend/app/schemas/{conversation,document,evaluation,experiment}.py`, `backend/app/models/{document,chunk,evaluation,experiment}.py`, the matching tests |

## Test strategy

- **Unit (no DB, dialect-agnostic):** provider event sequence and ordering (`message_start` id, tokens concatenate to the canned answer, sources present); frame serialization/parsing round-trip; title validation rules; chat-list ordering comparator on synthetic rows.
- **Integration (real PostgreSQL `rag_learning_test`, schema via Alembic):** chats CRUD — create (201, null title), rename (bumps `updated_at`, 404, 422 blank/too long), list (ordering + counts after messaging), get by id (transcript order, 404); WebSocket via `TestClient.websocket_connect` — `ready` frame, full turn frame order, both rows persisted with correct roles/content, multi-turn on one socket, malformed frame → `error` + still usable, unknown chat → `error` + close `4404`.
- **Migration:** `alembic upgrade head` on an empty database creates exactly `conversations` + `messages` + `alembic_version`; second run is a no-op.
- **Regression:** none — no golden dataset exists yet (the RAG feature adds it).

## Risks / dependencies

- **Squashed migration + existing DBs:** the local `rag_learning`/`rag_learning_test` databases already have the ten-table schema and an `alembic_version` row for the deleted revision. Plan: drop and recreate both databases before generating the new initial revision. Local dev data only — nothing was committed, so no data loss of consequence.
- **Sync DB inside async WebSocket:** blocking the event loop is the main correctness risk. Mitigation: every DB call in the socket path goes through `run_in_threadpool` on a short-lived `SessionLocal()`; the streaming loop only awaits socket sends.
- **`TestClient` WebSocket + threaded DB:** Starlette's `TestClient` runs the app on a portal thread; the threadpool sessions are independent, so assertions read committed rows from a separate session.
- **Prior build artifacts:** `.venv`, `egg-info`, `__pycache__`, `.pytest_cache` remain valid; `psycopg[binary] 3.3.6` already installs on CPython 3.14.
- **Stale frontend transport** (SSE) is a known follow-up, not a risk to this feature.

## Definition of Done for this plan

- [ ] All steps ticked
- [ ] Spec acceptance criteria ticked in `spec.md`
- [ ] `uv run pytest` passes (unit + real-PostgreSQL integration incl. WebSocket)
- [ ] `alembic upgrade head` idempotent on a fresh database, two tables only
- [ ] Live HTTP + WebSocket smoke against real PostgreSQL
- [ ] ADR-011 written, ADR-010 superseded, CLAUDE.md updated
- [ ] `implementation.md` entry appended; `spec.md` status → `Tested`
