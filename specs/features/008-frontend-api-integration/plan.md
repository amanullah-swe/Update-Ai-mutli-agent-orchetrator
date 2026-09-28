# Plan — 008 Frontend ↔ Backend API Integration (Chat CRUD + WebSocket streaming)

- **Status:** `Complete`
- **Last updated:** 2026-09-28
- **Spec:** `./spec.md`

> Written after the spec became `Specified`, before any code. A build session executes the steps below and appends to `implementation.md`.

## Context

007 ships a real FastAPI surface — `POST/GET/GET/PATCH /api/chats` and `WS /api/chats/{id}/ws` (ADR-011 frame vocabulary) — while the 006 frontend still talks to the retired `POST /api/chat` (SSE) and stores conversations in localStorage. This feature re-wires the frontend to the real API, keeps the `ChatService` interface seam (`ws` + `mock` transports), removes the dead SSE code, and updates CLAUDE.md decision #5. No backend changes.

## Approach (one line)

Add a typed HTTP client (`chatApi.ts`) and a `WebSocketChatService` transport that maps ADR-011 frames to the existing `ChatEvent` stream (per-turn sockets: open → one turn → close), make `useConversations` server-backed, and delete the SSE files — all behind the unchanged `ChatService` interface.

## Decisions (resolving the spec's open questions)

| Open question | Decision |
|---|---|
| Socket lifetime | **Per-turn sockets.** `WebSocketChatService.send()` opens a socket for its `conversation_id`, streams one turn, yields a synthetic `done` after `message_end`/`error`, closes with 1000. 007 explicitly supports multiple sockets per chat; reconnect/resume stays a 007 open question. |
| Sidebar preview | Feed from the in-memory transcript only (keep `updateMessageList` as pure state, no localStorage). After a reload the preview may be blank — accepted, spec open question notes it. |
| Auto-title | Kept client-side: first user message on a null-title chat → `renameChat(id, conversationTitle(text))`. Server no longer auto-titles (007 rescope). |
| Default transport | Dev env committed as `ws` (backend+frontend run together in this feature's smoke); `.env.development.example` documents `mock` as the safe fallback. |

## Steps (ordered)

1. **Types — align wire shapes.** `src/types/chat.ts`: `Conversation` → `{ id, title: string | null, created_at, updated_at, message_count?, last_message_at?, messages }`; update the `ChatEvent` doc comment to the WebSocket contract (keep the union; `done` stays client-side). Touches: `src/types/chat.ts`.
2. **HTTP client.** `src/services/chatApi.ts`: `listChats/createChat/getChat/renameChat` against `VITE_API_BASE_URL`; parse the backend error shape (`detail.message`) into thrown `Error`s; base URL trimmed once. Touches: `src/services/chatApi.ts` (+ `src/services/index.ts` if one exists — it doesn't).
3. **WebSocket transport.** `src/services/WebSocketChatService.ts`: implements `ChatService`; `send(payload)` rejects without `conversation_id`, opens `ws(s)://<base>/api/chats/<id>/ws`, sends `{"type":"user_message","content"}`, maps frames: `ready`/`message` consumed silently; `message_start`→`{type:'message_start',id}`; `token`→`{type:'token',delta}`; `sources`→`{type:'sources',sources}`; `message_end`→`{type:'message_end',id}` then `{type:'done'}`; `error`→`{type:'error',message}` then `{type:'done'}`; closes socket at stream end; unexpected close before end throws. Constructor takes `(baseUrl, socketFactory?)` so tests inject a fake socket. Touches: `src/services/WebSocketChatService.ts`.
4. **Factory.** `src/services/chatService.ts`: `ws` → `WebSocketChatService`, else `MockChatService` (unchanged default). Touches: `src/services/chatService.ts`.
5. **Delete stale SSE.** Remove `src/services/SseChatService.ts`, `src/services/sseClient.ts`, `src/utils/sse.ts`, `src/utils/sse.test.ts` — nothing references the retired `POST /api/chat`. Verify no imports remain (`grep -r "utils/sse\|SseChatService\|sseClient"`). Touches: deletions in `frontend/src/`.
6. **Server-backed conversations.** Rewrite `src/hooks/useConversations.ts`: hydrate from `listChats()` on mount; `createConversation()` async → `createChat()` + prepend; `renameConversation(id,title)` async → `renameChat()` + local update; `updateMessageList` stays as pure in-memory state (sidebar preview + auto-title trigger); `loading` state for the initial fetch; drop `localStorage`/`STORAGE_KEY`. Touches: `src/hooks/useConversations.ts`.
7. **Wire the page.** `src/pages/ChatPage.tsx`: `handleSelect` = select + `getChat(id)` → `load(id, detail.messages)` (async, with a transcript loading flag); `handleNew` = `await createConversation()` → `load`; `handleSend` = create-if-needed, then if the chat has no title and this is its first user message, derive + `renameConversation`; keep error/loading wiring. Touches: `src/pages/ChatPage.tsx`, `src/components/Transcript/Transcript.tsx` (accept a `loading` prop for detail fetch, if needed).
8. **Sidebar null-title placeholder.** `src/components/Sidebar/ConversationItem.tsx`: render `conversation.title ?? 'Untitled chat'`. Touches: `src/components/Sidebar/ConversationItem.tsx`.
9. **Env.** `frontend/.env.development` → `VITE_API_BASE_URL=http://localhost:8001`, `VITE_CHAT_TRANSPORT=ws`; refresh `frontend/.env.development.example` to name `ws | mock`. Touches: both env files.
10. **CLAUDE.md decision #5.** Replace the stale "SSE client for `/api/chat`" wording with the WebSocket client (ADR-011). Touches: `CLAUDE.md`.
11. **Tests.** Rewrite `src/hooks/useConversations.test.tsx` against a mocked `chatApi`; add `src/services/chatApi.test.ts` (mocked `fetch`) and `src/services/WebSocketChatService.test.ts` (fake socket: happy turn, error frame, unexpected close, missing conversation_id). Keep `src/hooks/useChat.test.tsx` (mock transport). Run `npm test`. Touches: test files.
12. **Build, lint, smoke.** `npm run build` + `npm run lint`; start the backend (`uv run uvicorn app.main:app --port 8001`) and confirm `GET /api/health` 200; run an existing backend WS round-trip test; serve the frontend (`npm run dev`) and curl `/` for the shell + a real `WS` traffic check via a node script against the running backend; then `implementation.md` + tick acceptance criteria.

## Files to create / modify

| File | Purpose |
| ---- | ------- |
| `frontend/src/types/chat.ts` | wire-aligned `Conversation`; `ChatEvent` doc update |
| `frontend/src/services/chatApi.ts` | new — typed HTTP client (list/create/get/rename) |
| `frontend/src/services/WebSocketChatService.ts` | new — WebSocket transport |
| `frontend/src/services/chatService.ts` | factory: `ws` | `mock` |
| `frontend/src/services/{SseChatService,sseClient}.ts` | **deleted** (stale SSE) |
| `frontend/src/utils/{sse.ts,sse.test.ts}` | **deleted** (stale SSE parsing) |
| `frontend/src/hooks/useConversations.ts` | server-backed list/create/rename |
| `frontend/src/pages/ChatPage.tsx` | select→fetch transcript; new→POST; auto-title |
| `frontend/src/components/Transcript/Transcript.tsx` | loading prop for detail fetch |
| `frontend/src/components/Sidebar/ConversationItem.tsx` | null-title placeholder |
| `frontend/.env.development(.example)` | `ws` default, base URL 8001 |
| `CLAUDE.md` | decision #5 wording → WebSocket (ADR-011) |
| `frontend/src/hooks/useConversations.test.tsx` | rewrite against mocked `chatApi` |
| `frontend/src/services/{chatApi,WebSocketChatService}.test.ts` | new unit tests |
| `specs/features/008-frontend-api-integration/implementation.md` | log appended during build |

## Test strategy

- **Unit (Vitest, jsdom):** `chatApi.test.ts` — success paths + error-detail parsing + network failure, with `fetch` stubbed; `WebSocketChatService.test.ts` — fake socket: full happy turn (`message_start→token×2→sources→message_end→done`), `error` frame → `error`+`done`, socket close before end → throws, missing `conversation_id` → throws; `useConversations.test.tsx` — mocked `chatApi`: mount hydration, `createConversation` POST returns+prepends+selects, `renameConversation` persists via PATCH, null-title auto-title, updateMessageList stays pure.
- **Regression:** existing `useChat.test.tsx` (mock transport) stays green — proves the UI/hook layer is transport-neutral. Existing backend pytest suite is untouched and re-run for the smoke.
- **E2E smoke (manual, this feature):** backend `uvicorn` on 8001 + frontend `npm run dev`; verify health, a scripted WS round-trip against the live backend, and the built client (`npm run build`) serving. Real click-through is offered to the user.

## Risks / dependencies

- **`ready`/`message` acks:** consumed silently — the user-message ack content is identical to what the client sent; rendered ids are client-side until a reload re-syncs from `GET /api/chats/{id}`. Accepted.
- **Per-turn sockets** re-open for each message — 007 explicitly allows it; cost is one handshake per turn.
- **jsdom has no `WebSocket`** — the fake-socket factory keeps transport tests hermetic (inject in constructor).
- **Backend must be running** for the smoke; PostgreSQL is already up locally (seeded `conversations` present). No DB work needed.
- Depends on: nothing new. Consumes 007's frozen contract only.

## Definition of Done for this plan

- [ ] All steps ticked
- [ ] Spec acceptance criteria ticked in `spec.md`
- [ ] `implementation.md` log written for the build session(s)
- [ ] Status in `spec.md` moved to `Tested` (then `Accepted` after review)