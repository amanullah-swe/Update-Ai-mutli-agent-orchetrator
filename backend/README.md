# Backend API (FastAPI + PostgreSQL + WebSocket chat)

Chat-first build of the RAG Learning Platform backend: a chat CRUD API with a
per-chat **WebSocket** for message send/receive. Every route is wired to
PostgreSQL; the assistant's content is **mock** (no model is invoked), produced
through a `ChatProvider` interface a future RAG-backed provider will implement —
the Core Architectural Rule at the service seam. The AI agent / RAG pipeline / LLM
integration are separate features; this is the stable shell they plug into later.

## Requirements

- Python 3.13+ (developed on 3.14) and [uv](https://docs.astral.sh/uv/)
- PostgreSQL 15+ (dev: `make up` via Docker, or a local instance)

## Setup

```sh
make up                 # start PostgreSQL (docker compose), or use a local instance
cp backend/.env.example backend/.env   # optional overrides
make migrate            # apply Alembic migrations (the only DDL source)
make seed               # optional dev seed data
make backend            # uvicorn on :8001 with reload
```

Open http://localhost:8001/docs for the interactive OpenAPI UI, or hit
`GET /api/health`.

## Routes

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | app + db status, request-id |
| POST | `/api/chats` | create a chat (`{"title": "…"|null}`) → 201 |
| GET | `/api/chats` | chat list, most recently active first |
| GET | `/api/chats/{id}` | one chat + its transcript (404 if missing) |
| PATCH | `/api/chats/{id}` | rename a chat (`{"title": "…"}`) → 200 |
| WS | `/api/chats/{id}/ws` | send/receive messages (JSON frames) |

## WebSocket chat

`WS /api/chats/{chat_id}/ws` is the chat window's message channel — one socket
carries one chat's live turns. History comes from `GET /api/chats/{id}`; the
socket does not replay it.

**Send a message** (text frame, JSON):

```json
{ "type": "user_message", "content": "How does chunking work?" }
```

**Received frames** (JSON, discriminated by `type`):

```
{ "type": "ready", "chat_id": "<uuid>" }
{ "type": "message", "message": MessageOut }                 // user ack (persisted)
{ "type": "message_start", "id": "<assistant id>" }
{ "type": "token", "delta": "<text>" }                       // … repeated
{ "type": "sources", "sources": [ Source… ] }                // citations
{ "type": "message_end", "id": "<assistant id>", "message": MessageOut }
{ "type": "error", "code": "…", "message": "…" }             // in-band, socket stays open
```

The socket stays open across turns (multi-turn on one connection). Unknown
`chat_id` → an `error` frame + close code `4404`.

```ts
// MessageOut / Source — the shape the frontend types already model
interface Source { document_id: string; chunk_id: string; snippet: string; score?: number; metadata?: Record<string, unknown> }
interface MessageOut { id: string; role: 'user' | 'assistant'; content: string; created_at: string; sources?: Source[]; error?: boolean }
```

## How mock chat works

`WS /api/chats/{id}/ws` persists your `user_message`, then streams a
**deterministic canned reply** through the `ChatProvider` interface
(`MockChatProvider`) and persists the assistant message. The provider is chosen by
config, not code: `configs/<env>.yaml → chat.provider`. Swapping `mock` for a real
RAG-backed provider later means adding an implementation and changing that config
value — routes don't change.

## Adding / changing provider implementations

- Implement `app/services/chat.py:ChatProvider` in a new module and wire it in
  `build_chat_provider()`, then set `chat.provider` in config (today: `mock`).
- DB schema changes go to `app/models/*` then `make migrate-make name="..."` +
  `make migrate`. `database/schemas/reference.sql` is reference only —
  **Alembic is the source of truth**.

## Tests

```sh
cd backend && uv run pytest      # unit (provider, no DB) + integration (real PostgreSQL)
```

Requires a reachable `rag_learning_test` database (see `tests/conftest.py`); the
schema is rebuilt from Alembic at session start.

## Layout (Feature-Sliced Architecture)

```text
backend/
  app/
    main.py            # FastAPI application factory, CORS, exception handlers, middleware
    core/              # Cross-cutting: config (Settings + YAML), logging, exceptions
    database/          # Database engine, SessionLocal, get_db, Base declarative model
    features/          # Vertical feature slices (domain-driven)
      chats/           # Chat feature slice: router, schemas, models, repository, provider, ws
      health/          # Health feature slice: router, schemas
    shared/            # Backward-compatibility shims (core, database)
  rag/                 # RAG pipeline components: chunking, embeddings, ingestion, retrieval, etc.
  tests/               # pytest unit + integration test suites
database/              # migrations (Alembic), schemas (reference), seed
configs/               # development.yaml / testing.yaml / production.yaml
docker/                # docker-compose (postgres + pgvector) + Dockerfile.backend
```