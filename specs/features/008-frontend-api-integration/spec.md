# 008 — Frontend ↔ Backend API Integration (Chat CRUD + WebSocket streaming)

- **Status:** `Tested`
- **Last updated:** 2026-09-28
- **Depends on:** `006-frontend-ui` (the UI shell being wired up) · `007-backend-api` (the API surface being consumed)
- **Source:** CLAUDE.md § Backend API surface · § Build decisions #5 (updated here) & #10 → ADR-011 · 007 spec § Notes ("Frontend WebSocket wiring … follow-up, not this feature")

## Problem / Motivation

The frontend (006) was built against a **retired** backend contract. Its only live transport, `SseChatService`, streams from `POST /api/chat` over SSE — an endpoint that no longer exists (007 rescoped chat transport to `WS /api/chats/{id}/ws`, ADR-011 superseding ADR-010/SSE). Its conversation list is persisted in **localStorage**, while the backend (007, `Tested`) now owns `conversations`/`messages` in PostgreSQL behind a real CRUD surface.

The result: the UI and the API speak different contracts and share no state. 007 explicitly deferred closing this gap: *"Wiring the UI to this WebSocket API is a 006 follow-up — not part of this feature."* This feature **is** that follow-up: make the chat UI drive the real backend end to end — conversations from the server, messages streamed over the WebSocket — so the platform's chat experience is genuinely working before the RAG pipeline feature arrives.

## Scope

**In scope**

- `frontend/` only — no backend changes (007 owns and froze the API).
- **Conversations from the server:** list, create, get-by-id (transcript), rename all hit the 007 HTTP surface. `useConversations` stops using `localStorage`.
- **WebSocket transport:** a `WebSocketChatService` behind the existing `ChatService` interface, implementing ADR-011's frame vocabulary against `WS /api/chats/{id}/ws`, selected by `VITE_CHAT_TRANSPORT=ws`.
- **Removal of the stale SSE transport** (`SseChatService`, `sseClient`, `utils/sse.ts` + its tests) — dead code against a nonexistent endpoint.
- **Type alignment:** `Conversation`/`Message`/`Source` updated to the wire shapes (nullable `title`, `updated_at`, `message_count`, `last_message_at`).
- **Client-side auto-title:** a new untitled chat still gets a title derived from its first user message — now a real `PATCH /api/chats/{id}` instead of a local write.
- **Env:** `VITE_CHAT_TRANSPORT=ws` default for dev; `VITE_API_BASE_URL` aligned to the backend's actual port (8001).
- Unit tests for the new/changed modules; build + lint clean; end-to-end smoke against the running backend.
- CLAUDE.md § Build decision #5 updated to match ADR-011 (SSE client wording is stale).

**Out of scope** (future features / open questions from 006 & 007)

- Delete-chat UI (`DELETE /api/chats/{id}` — 007 Open question 1).
- Socket reconnect/resume mid-turn (007 Open question 3) — this feature closes the socket after each turn; the backend explicitly supports multiple sockets per chat.
- Auth, document screens, evaluation/experiment screens.
- Backend changes of any kind (schema, routes, providers).

## Behavioral contract

### Interfaces

No CLAUDE.md Common Interface is involved (frontend feature). The frontend keeps its own stable contracts in `types/chat.ts`, now aligned to the 007 wire contracts (`frontend/src/spec` reference: `backend/app/schemas/chat.py`):

- `Source` — unchanged: `{ document_id, chunk_id, snippet, score?, metadata? }` (matches backend `Source`).
- `Message` — matches backend `MessageOut`: `{ id, role: "user"|"assistant", content, created_at, sources?, error }`.
- `Conversation` — matches `ChatOut`/`ChatSummary` plus an in-memory transcript: `{ id, title: string|null, created_at, updated_at, message_count?, last_message_at?, messages: Message[] }`.
- `ChatEvent` — unchanged vocabulary (ADR-011 preserves it): `message_start | token | sources | message_end | error`, plus a client-side `done` synthesized by transports.
- `ChatService` — `{ send(payload: ChatPayload): AsyncIterable<ChatEvent> }`, unchanged; now implemented by **`WebSocketChatService`** (real) and `MockChatService` (tests / dev without backend). This is the client-scale mirror of the Core Architectural Rule: the UI and hooks depend on the interface, never on a concrete transport.

New in `services/`:

- `chatApi.ts` — a typed HTTP client for the 007 surface: `listChats()`, `createChat(title?)`, `getChat(id)`, `renameChat(id, title)`. Throws on non-2xx with the backend error detail (`{"detail": {"code", "message"}, "request_id"}`) surfaced as the message.

### Data flow

1. **App mount** → `listChats()` → sidebar renders server summaries (`messages: []`).
2. **Select a chat** → `getChat(id)` → transcript loaded into `useChat` (`load`); a loading state shows while it fetches.
3. **New chat** → `createChat()` → sidebar gains the chat; composer sends to it with no title.
4. **Send a message** → `WebSocketChatService.send` opens `ws://<base>/api/chats/{conversation_id}/ws`, sends `{"type":"user_message","content":…}`, then maps server frames: `ready`/`message` (acks) are consumed internally; `message_start/token/sources/message_end/error` yield as `ChatEvent`s; after `message_end` (or `error`) the socket is closed and a `done` event ends the stream. `useChat` renders tokens/sources incrementally exactly as it does today.
5. **First user message on an untitled chat** → `renameChat(id, title)` with the client-derived title → sidebar + server both update.
6. Source of truth is the server; the transcript is re-fetched on every selection, so a reload shows the persisted chat and its messages.

### Configuration

```env
# frontend/.env.development (committed)
VITE_API_BASE_URL=http://localhost:8001
VITE_CHAT_TRANSPORT=ws        # ws (real backend) | mock (dev/tests without backend)

# frontend/.env.development.example (committed, documented)
VITE_API_BASE_URL=http://localhost:8001
VITE_CHAT_TRANSPORT=mock      # mock remains the safe documented default; dev uses ws
```

Transport selection stays in `createChatService()`: `ws` → `WebSocketChatService`; anything else → `MockChatService`.

### Errors

- HTTP: `chatApi` throws `ApiError`/`Error` with the backend's `detail.message` when a request fails (non-2xx) or the network fails.
- WebSocket: an in-band `error` frame yields a `ChatEvent.error` (existing `useChat` error path — inline alert + `error: true` assistant bubble) and ends the turn; an unexpected server close before `message_end` throws (same catch path). A missing `conversation_id` throws a descriptive error before any socket opens.
- The UI's existing loading/error rendering is unchanged.

## Acceptance criteria

- [x] All conversation state is server-backed: list/create/get/rename hit 007 HTTP routes; `localStorage` persistence is gone from `useConversations`.
- [x] `VITE_CHAT_TRANSPORT=ws` streams a reply from the real backend through `WS /api/chats/{id}/ws` with the ADR-011 frame vocabulary; token-by-token rendering, sources, and inline errors all work.
- [x] Selecting a chat fetches and renders its transcript from the server (with a loading state); a reload shows persisted chats and messages.
- [x] The stale SSE transport (`SseChatService`, `sseClient`, `utils/sse.ts`) and its tests are removed — no code references the retired `POST /api/chat`.
- [x] `ChatService` keeps exactly one interface; `ws` + `mock` remain the two selectable transports.
- [x] `types/chat.ts` wire shapes match the backend schemas (nullable `title`, `updated_at`, `message_count`, `last_message_at`).
- [x] `npm test`, `npm run build`, `npm run lint` all pass in `frontend/`.
- [x] Backend + frontend both running: a chat can be created, messaged (streamed reply + mock sources), and after a page reload the chat and transcript persist; renaming persists.
- [x] CLAUDE.md § Build decision #5 no longer promises an SSE `/api/chat` client; ADR-011 is cited for the WebSocket forward.
- [x] Feature logged in `implementation.md`; status reaches `Tested`.

## Open questions

- [ ] **Sidebar preview:** 007 `ChatSummary` carries `message_count`/`last_message_at` but no message text. The sidebar preview (`conversation.messages.at(-1)`) is fed from the in-memory transcript only — after a reload it shows `last_message_at` info or nothing. Acceptable for now (keep it simple); a `last_message` snippet field on the summary would be a 007 change.
- [ ] **Socket lifetime:** per-turn sockets (open → one turn → close) vs. one persistent socket per chat. 007 supports both; per-turn is simpler and is the default here. Revisit if reconnect/resume semantics are needed (007 open question 3).

## Notes / links

- 007 spec (this feature's contract source): `specs/features/007-backend-api/spec.md`; ADR-011 `specs/decisions/011-chat-transport-websocket.md`.
- 007 spec § Scope: *"Frontend WebSocket wiring (006 owns the UI; its SSE transport becomes stale — follow-up, not this feature)."* — resolved here.
- 006 spec (the UI being integrated): `specs/features/006-frontend-ui/spec.md`; its open question *"Conversation list source"* is resolved here (server).
- The mock transport is retained (tests + backend-less dev), matching 006's decision that the UI stays runnable before a backend.