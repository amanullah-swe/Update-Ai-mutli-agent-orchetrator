# ADR-011 — Chat transport: WebSocket (supersedes ADR-010's SSE)

- **Status:** Accepted
- **Date:** 2026-09-27
- **Supersedes:** ADR-010 (SSE over `POST /api/chat`)
- **Related:** CLAUDE.md "Build decisions" #10 · spec 007-backend-api

## Context

The 007 feature was reshaped from a broad API surface (documents/evaluation/experiments +
SSE chat) into a single chat CRUD app where messages are sent and received **in the
chat window**. The chat window is inherently bidirectional and long-lived: the client
sends, the assistant streams back, and the window stays open for the next turn. The prior
decision (ADR-010) standardized on SSE over a POST response, chosen mainly to match the
then-existing frontend parser — but SSE is one-directional and couples each turn to a new
HTTP request, which does not match a persistent chat-window transport.

Options:
(a) WebSocket — a persistent bidirectional socket per chat;
(b) SSE over `POST` (ADR-010's choice) — one request per turn, server→client only;
(c) plain request/response polling.

## Decision

Adopt **WebSocket** for chat messaging: one socket at `WS /api/chats/{chat_id}/ws` carries
message send **and** receive for a chat, with JSON text frames discriminated by a `type`
field. The event vocabulary is unchanged from ADR-010's set (`message_start → token →
sources → message_end`, plus in-band `error`) — only the transport and framing change.

Payloads (abridged):

- client → server: `{"type":"user_message","content":"…"}`
- server → client: `ready`, then per turn `message` (user ack), `message_start`, `token`*,
  `sources`, `message_end` (final assistant message); `error` is in-band.

The socket stays open across turns (multi-turn on one connection), and history is served by
`GET /api/chats/{id}` — the socket does not replay the transcript.

## Consequences

- **ADR-010 is superseded.** SSE code (route, framing helpers, frontend SSE client) is
  retired for chat; CLAUDE.md decision #10 now records WebSocket (this ADR) as the chat
  transport. A future real-time streaming need (e.g. long RAG runs) may still use SSE or
  WebSocket on its own merits — no global rule.
- **Bidirectional, persistent** connection — a natural fit for a chat window; no
  per-turn HTTP setup.
- **Sync DB managed carefully:** the socket handlers are async on the event loop, so all
  database work is dispatched via `run_in_threadpool` on short-lived sessions (the engine
  stays sync SQLAlchemy → avoids an async-driver dependency).
- **Connection management** becomes explicit: close codes (`4404` unknown chat, `1000`
  clean, `1011` failure) and in-band `error` frames replace HTTP status codes.
- **Frontend follow-up:** `frontend/src/services/{SseChatService,sseClient}.ts` and
  `utils/sse.ts` target the retired SSE transport and must be reworked to a WebSocket
  client — tracked under feature 006-frontend-ui.