# 007 — Chat CRUD API (FastAPI + PostgreSQL + WebSocket messaging)

- **Status:** `Tested`
- **Last updated:** 2026-09-27
- **Depends on:** `none`
- **Source:** CLAUDE.md § Backend API surface · Database · Observability · Build decisions #2/#3/#8 · user direction 2026-09-27 (rescope) · supersedes the first 007 draft

## Problem / Motivation

The first draft of this feature shipped the *entire* CLAUDE.md minimum API surface at once — document upload, evaluation runs, experiment runs, plus SSE chat — all backed by mocked payloads for subsystems (RAG, agent, evaluation) that do not exist yet. That was too broad: it produced speculative routes whose data had no real producer, and it buried the one thing the platform actually needs first.

This revision narrows 007 to the core chat experience, end to end and genuinely working:

> a user can **create a chat**, **rename it**, **see the chat list**, **open a chat by id**, and **send/receive messages in the chat window over a WebSocket**.

Everything is real (routes → services → PostgreSQL). The only mocked piece is the assistant's *content*, and that lives behind the `ChatProvider` interface that a future RAG-backed provider will implement — the Core Architectural Rule at the service seam.

Documents, evaluation, and experiments are **not** abandoned; they return to the backlog as features in their own right, to be specified once the RAG pipeline exists to produce real data. Their code and tables were removed from this repository (nothing was committed).

## Scope

**In scope**

- `backend/` FastAPI package (`app/api/routes/`, `app/core/`, `app/models/`, `app/schemas/`, `app/services/`, `app/main.py`, `tests/`), managed with `uv` + `pyproject.toml`.
- **Chats over HTTP:** create, list, get by id, rename.
- **Messaging over WebSocket:** one socket per chat; client sends a message, server streams the assistant reply back on the same socket; both messages persisted.
- Persistence for the two entities this feature needs: `conversations` (a chat) and `messages` (its transcript), per CLAUDE.md's entity list.
- `ChatProvider` interface + `MockChatProvider`, selected by config (`chat.provider`), so a real provider swaps in later without touching routes.
- `configs/{development,testing,production}.yaml` → typed `Settings` (pydantic-settings), env-overridable; `backend/.env.example`.
- Alembic migrations as the single DDL source (decision #8) — one fresh initial revision for the two tables.
- `GET /api/health` (kept — it is the ops entry point and costs nothing).
- Unit tests + integration tests against real PostgreSQL, including WebSocket round-trips.

**Out of scope** (backlog — each gets its own feature when it has a real producer)

- ~~`DELETE /api/chats/{id}` — not requested; the chat list has no delete affordance yet. *(Open question 1.)*~~ → added by **009** (see Open questions).
- Document upload / ingestion / loaders / chunking / embeddings / vectorstore / retrieval / reranking.
- Evaluation and experiments (routes, services, models, tables) — removed by this rescope.
- AI agent, LLM calls, RAG pipeline — the assistant reply is mocked.
- Frontend WebSocket wiring (006 owns the UI; its SSE transport becomes stale — follow-up, not this feature).
- Authentication/authorization, rate limiting, multi-user chat ownership.
- pgvector extension and vector columns.

## Behavioral contract

### Naming (decision)

The product term the user speaks — **chat** — is used for the API surface (`/api/chats`). The database entities keep the names CLAUDE.md fixes: **`conversations`** and **`messages`**. The service/model layer therefore speaks "conversation"; routes and schemas speak "chat". This mapping is deliberate and is the only place the two vocabularies meet.

### HTTP surface

| Method | Path | Purpose | Success | Failure |
| --- | --- | --- | --- | --- |
| `GET` | `/api/health` | liveness + database reachability | `200` | — |
| `POST` | `/api/chats` | create a chat | `201` | `422` invalid body |
| `GET` | `/api/chats` | chat list (summaries) | `200` | — |
| `GET` | `/api/chats/{chat_id}` | one chat + its transcript | `200` | `404` unknown id |
| `PATCH` | `/api/chats/{chat_id}` | rename a chat | `200` | `404` unknown id · `422` invalid body |
| `WS` | `/api/chats/{chat_id}/ws` | send/receive messages | `101` upgrade | error frame + close `4404` unknown id |

Request and response bodies:

```jsonc
// POST /api/chats            request  — title optional; omitted → null
{ "title": "Chunking experiments" }

// ChatOut — the chat resource (POST 201, GET by id, PATCH 200)
{ "id": "<uuid>", "title": "Chunking experiments",
  "created_at": "<iso8601>", "updated_at": "<iso8601>" }

// GET /api/chats             response
{ "items": [ ChatSummary… ], "total": 3 }

// ChatSummary — one row of the chat list
{ "id": "<uuid>", "title": "…", "created_at": "<iso8601>", "updated_at": "<iso8601>",
  "message_count": 4, "last_message_at": "<iso8601>|null" }

// GET /api/chats/{id}        response — ChatOut plus the transcript
{ "id": "<uuid>", "title": "…", "created_at": "…", "updated_at": "…",
  "messages": [ MessageOut… ] }

// MessageOut
{ "id": "<uuid>", "role": "user|assistant", "content": "…",
  "created_at": "<iso8601>", "sources": [Source…] | null, "error": false }

// PATCH /api/chats/{id}      request — title required, non-blank, ≤ 500 chars
{ "title": "Renamed chat" }
```

- **Chat list order:** most recently active first — `max(messages.created_at)` descending, chats with no messages ordered after them by `created_at` descending. Stable and deterministic.
- **`title` may be `null`** (a chat created with no title, or titled later by the client). The list and detail views render the title as-is; the client substitutes placeholder text.
- **`sources`** keeps the 006 `Source` shape (`document_id`, `chunk_id`, `snippet`, `score?`, `metadata?`) so the future RAG provider can populate it without a contract change. The mock provider emits two mock sources, keeping the traceability requirement (CLAUDE.md § Observability) visible in the wire contract.

### WebSocket contract for `WS /api/chats/{chat_id}/ws`

The socket is the chat window's message channel. **One socket carries one chat's live turn**: the client sends a user message, and the server streams the assistant's reply back on the same connection. History comes from `GET /api/chats/{id}` — the socket does not replay the transcript.

Every frame in both directions is a single JSON object (text frame, UTF-8), discriminated by `type`.

**Client → server**

```jsonc
{ "type": "user_message", "content": "How does chunking work?" }
```

**Server → client**

| Order | Frame | Payload |
| --- | --- | --- |
| 1 | `ready` | `{"type":"ready","chat_id":"<uuid>"}` — connection accepted, which chat |
| 2 | `message` | the **persisted user message**: `{"type":"message","message":MessageOut}` (ack — carries the real id/timestamp) |
| 3 | `message_start` | `{"type":"message_start","id":"<assistant message uuid>"}` |
| 4…n | `token` | `{"type":"token","delta":"<text>"}` — one text delta per frame |
| n+1 | `sources` | `{"type":"sources","sources":[Source…]}` — optional |
| n+2 | `message_end` | `{"type":"message_end","id":"<uuid>","message":MessageOut}` — the final assistant message with full content + sources |
| — | `error` | `{"type":"error","code":"<slug>","message":"<human text>"}` — in-band failure; the socket stays open |

The event vocabulary (`message_start` → `token` → `sources` → `message_end`, plus in-band `error`) is deliberately the same set 006 already models in `types/chat.ts` — only the transport and framing change (JSON frames on a socket instead of SSE on a POST response). There is no `done` frame: the socket stays open for the next turn.

**Turn semantics**

1. Server validates `chat_id` on connect. Unknown → send an `error` frame (`code: "not_found"`) and close with **`4404`**. Known → accept, send `ready`.
2. Client sends `user_message`. Server persists the user message, sends the `message` ack, then streams the assistant reply (`message_start` → tokens → optional `sources` → `message_end`).
3. The assistant message is persisted when its stream completes, before `message_end` is sent — so the transcript the client renders always matches the database.
4. The socket then **stays open** and accepts the next `user_message` (multi-turn on one connection). Multiple sockets may be open on the same chat; each gets its own reply stream.
5. A malformed or unknown client frame gets an `error` frame (`code: "bad_request"`) and the socket stays open — one bad frame does not kill the session.

**Close codes**

| Code | When |
| --- | --- |
| `4404` | `chat_id` does not exist (after `error` frame) |
| `1000` | client or server closes normally |
| `1011` | unexpected server failure while handling a turn |

### Core Architectural Rule at the service seam

The assistant's reply is produced by a `ChatProvider` interface (`app/services/chat.py`) returning an ordered stream of provider events. This feature ships `MockChatProvider`; `chat.provider` in config selects it (today the only value). The WebSocket route and the chat service depend on the interface only — no `if provider == …` in route or pipeline code. Adding a RAG-backed provider later means: new file, register, config value. This is the same rule that governs chunkers, retrievers, and rerankers.

### Data flow

**Create / rename / list / get** — validate (`schemas`) → service (`app/services/`) → SQLAlchemy session (commit/rollback) → Pydantic response.

**Send a message** — WebSocket frame → validate → persist user message → `ChatProvider` stream → persist assistant message → frames to client.

### Errors

- HTTP errors keep the existing consistent shape: `{"detail": {"code": "…", "message": "…"}, "request_id": "…"}`, with `X-Request-ID` echoed back (observability — every request traceable).
- Typed `AppError` hierarchy (`NotFoundError`, `ConflictError`, `ValidationError`, `StorageError`) mapped to status codes by handlers in `app/core/exceptions.py`.
- WebSocket errors are **in-band** `error` frames (a socket has no status codes); only connection-level failures use close codes.
- Unknown `chat_id` on `GET`/`PATCH` → `404` with `code: "not_found"`.

### Configuration

```yaml
# configs/development.yaml
app:
  name: rag-learning-platform
  environment: development
  debug: true
  version: 0.1.0
database:
  url: postgresql+psycopg://rag:rag@localhost:5432/rag_learning
cors:
  origins: [http://localhost:5173, http://127.0.0.1:5173]
chat:
  provider: mock          # mock today; the seam leaves room for a future `rag` provider
  mock:
    token_delay_ms: 25    # tests force 0
```

```env
# backend/.env.example  (env prefix RAG_; env + .env override YAML)
RAG_ENVIRONMENT=development
RAG_DATABASE_URL=postgresql+psycopg://rag:rag@localhost:5432/rag_learning
RAG_CHAT_PROVIDER=mock
RAG_CORS_ORIGINS=["http://localhost:5173"]
```

The `documents:` config section (`upload_dir`, `max_size_mb`) is removed with the document feature.

### Database contract

Two tables, created by one Alembic revision (the only DDL source):

- **`conversations`** — `id` (uuid PK), `title` (nullable, ≤500), `created_at`, `updated_at` (both `timestamptz`, server `now()`; `updated_at` bumps on rename so the chat list reorders honestly).
- **`messages`** — `id` (uuid PK), `conversation_id` (FK → `conversations.id`, `ON DELETE CASCADE`, indexed), `role` (`user|assistant`), `content` (text), `sources` (json, nullable), `error` (bool, default false), `created_at` (indexed via the FK scan; `timestamptz`, server `now()`).

The migration history is **squashed**: the previous ten-table revision is deleted (nothing was ever committed) and replaced by a single initial revision for these two tables. `database/schemas/reference.sql` is regenerated to match; `database/seed/dev.sql` seeds two chats with a few messages.

## Acceptance criteria

- [x] `uv run uvicorn app.main:app` boots; `GET /api/health` returns `200` with the database reported ok against real PostgreSQL.
- [x] `POST /api/chats` creates a chat (`201`, returns id/title/timestamps); `title` omitted → `null`.
- [x] `PATCH /api/chats/{id}` renames a chat and bumps `updated_at`; unknown id → `404`; blank/oversized title → `422`.
- [x] `GET /api/chats` returns summaries ordered by recent activity with correct `message_count` / `last_message_at`.
- [x] `GET /api/chats/{id}` returns the chat with its full transcript in order; unknown id → `404`.
- [x] `WS /api/chats/{id}/ws` connects, sends `ready`, and round-trips a turn: client `user_message` → `message` ack → `message_start` → `token`* → `sources` → `message_end`, with both messages persisted.
- [x] A single socket handles multiple turns; a malformed frame yields an `error` frame without closing the socket; an unknown `chat_id` yields an `error` frame and close `4404`.
- [x] Switching `chat.provider` is a config change only — no provider dispatch in routes or the chat service.
- [x] The ten-entity schema is gone: `alembic upgrade head` on an empty database creates exactly `conversations` + `messages` (+ `alembic_version`) and is idempotent; tests never `create_all` against PostgreSQL.
- [x] Unit tests (dialect-agnostic) + integration tests (real PostgreSQL, including WebSocket round-trips) pass under `uv run pytest`.
- [x] Documents/evaluation/experiments code, routes, models, tables, config, and tests are removed; no RAG/agent/LLM code is introduced.
- [x] ADR-011 records the WebSocket decision and supersedes ADR-010; CLAUDE.md's API surface and build decision #10 are updated to match.

## Open questions

- [x] **Delete a chat?** ✅ RESOLVED in **009** — the UI grew a delete affordance, so `DELETE /api/chats/{id}` now exists (204; messages cascade via the FK, which was already in place).
- [ ] **Chat titles:** server-side auto-titling from the first message was dropped with the rescope (the client can rename instead). Revisit if the UI wants zero-effort titles.
- [ ] **Resume vs. replay:** the socket does not replay history and does not resume a dropped connection mid-turn. If the UI needs reconnect-with-context, specify it then.
- [ ] **`sources` provenance:** still `json` on `messages`; whether evaluation later reads sources from messages or a join table is the evaluation feature's call.

## Notes / links

- Supersedes the first 007 draft (broad API surface + SSE chat). The prior build's ten-entity schema, document upload, evaluation, and experiment routes are deleted by this rescope; the backlog keeps the requirements.
- **ADR-011** (`specs/decisions/011-chat-transport-websocket.md`) supersedes **ADR-010** (SSE) — decision #10 in CLAUDE.md is updated to point at it.
- Kept from the prior build (unchanged, still valid): ADR-002 (uv tooling), ADR-003 (pydantic-settings + YAML), ADR-008 (Alembic as the only DDL source).
- Frontend note: `frontend/src/services/SseChatService.ts`, `sseClient.ts`, `utils/sse.ts` target the retired SSE transport. Wiring the UI to this WebSocket API is a 006 follow-up — **not** part of this feature.
