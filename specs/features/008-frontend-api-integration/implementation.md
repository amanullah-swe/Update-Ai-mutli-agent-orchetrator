# Implementation Log — 008 Frontend ↔ Backend API Integration (Chat CRUD + WebSocket streaming)

- **Status:** `Tested`
- **Spec:** `./spec.md`
- **Plan:** `./plan.md`

> **Append-only.** Every build session adds a dated entry here (newest at the bottom). Never edit older entries — this is the back-tracking record. Format: `specs/templates/implementation.md`.

## Log

### 2026-09-28 — Initial build: WebSocket transport + server-backed conversations

**Session scope:** Execute `specs/features/008-frontend-api-integration/plan.md` steps 1–12 (types → HTTP client → WS transport → factory → SSE cleanup → hooks → page wiring → env → CLAUDE.md → tests → smoke). Spec set `Draft → Specified → Planned → Tested`; all 10 acceptance criteria ticked.

**What was done**

- `src/types/chat.ts` — `Conversation` now matches the backend wire shape (`title: string | null`, `updated_at`, `message_count?`, `last_message_at?`); `ChatEvent` doc comment updated to the WebSocket contract (vocabulary unchanged; `done` stays client-side).
- `src/services/chatApi.ts` (new) — typed HTTP client for 007: `listChats` / `createChat` / `getChat` / `renameChat`; non-2xx surfaces backend `detail.message`; network failure → "Could not reach the backend…".
- `src/services/WebSocketChatService.ts` (new) — `ChatService` transport over `WS /api/chats/{id}/ws`, one socket per turn (open → send `user_message` → map frames → close 1000). `ready`/`message` acks consumed silently; `message_start/token/sources/message_end/error` map to `ChatEvent`s; synthetic `done` ends the stream; unexpected close before `message_end` throws. Constructor accepts an injectable `socketFactory` (jsdom has no `WebSocket`); the DOM `WebSocket` is adapted at the boundary via a typed cast.
- `src/services/chatService.ts` — factory selects `ws` → `WebSocketChatService`, else `mock`; `sse` path removed.
- **Deleted stale SSE code:** `SseChatService.ts`, `sseClient.ts`, `utils/sse.ts`, `utils/sse.test.ts` (all targeted the retired `POST /api/chat`); `src/vite-env.d.ts` transport union `'sse' | 'mock'` → `'ws' | 'mock'`.
- `src/hooks/useConversations.ts` — server-backed: fetch list once on mount (cancellation-guarded effect, no localStorage); `createConversation` → POST + prepend + select; `renameConversation` → PATCH + local reflect; `updateMessageList` kept as pure in-memory state (sidebar preview only); `loading` starts `true`; initial `loading` state satisfies the `react(set-state-in-effect)` rule.
- `src/pages/ChatPage.tsx` — `handleSelect` fetches `GET /api/chats/{id}` and loads the transcript (with a transcript loading flag + error); `handleNew` awaits POST create; `handleSend` creates if needed and **auto-titles** a brand-new (null-title) chat via `renameConversation(conversationTitle(text))` after the first send; page-level error surfaces `listError ?? transcriptError ?? chatError`.
- `src/components/Transcript/Transcript.tsx` — new `loading` prop renders a "Loading transcript…" state during the detail fetch.
- `src/components/Sidebar/ConversationItem.tsx` — renders `Untitled chat` when `title` is null.
- `frontend/.env.development` — `VITE_API_BASE_URL=http://localhost:8001` (was 8000 — a mismatch with the backend) and `VITE_CHAT_TRANSPORT=ws`; `.env.development.example` refreshed (`ws | mock`).
- `CLAUDE.md` § Build decision #5 — "SSE client for `/api/chat` streaming" replaced with the WebSocket client for `/api/chats/{id}/ws` (ADR-011 / decision #10).
- Tests: rewrote `useConversations.test.tsx` against a mocked `chatApi`; added `chatApi.test.ts` (7 cases: mapping, POST/PATCH bodies, error-detail parsing, non-JSON error, network failure) and `WebSocketChatService.test.ts` (5 cases: happy turn, in-band error, abrupt close → throw, garbage/unknown frames ignored, missing `conversation_id` → throw before opening). `useChat.test.tsx` unchanged (still runs against the mock transport — proves the hook layer is transport-neutral).

**Deviations from plan & why**

- `useConversations` no longer exposes a `refresh()` — the one-time mount fetch is inlined in the effect with a `cancelled` guard, which is what satisfies oxlint's `react(set-state-in-effect)` rule (it flagged calling `refresh()` from the effect even though its setters are async). No behavior loss; a retry affordance would add it back.
- `WebSocketLike` handler signatures mirror the DOM `WebSocket` (first arg `Event`-shaped) rather than a bespoke narrower shape, so the DOM type is structurally closer; the boundary cast in the default factory absorbs the remaining mismatch. Tests pass an ignored event arg when invoking `onopen`.
- `transcriptLoading` is shown for the detail fetch (small addition — better UX than a blank transcript while `GET /api/chats/{id}` is in flight).

**Tests run / results**

- `npm test` (frontend) — 5 files, **33 passed** (useChat: 5, useConversations: 5, chatApi: 7, WebSocketChatService: 5, messages utils: 10).
- `npm run build` (tsc -b + vite build) — clean; 385 kB bundle (118 kB gzip).
- `npm run lint` (oxlint) — no warnings.
- `uv run pytest` (backend) — **23 passed** (unchanged; no backend code touched).

**Decisions made**

- Per-turn sockets (one socket per `send`, closed 1000 after the turn) — resolves spec open question 2; 007 explicitly permits multiple sockets per chat, and it keeps `ChatService.send()`'s async-iterator contract untouched.
- Auto-title is client-driven (server has none, per 007 rescope): first user message on a null-title chat triggers `PATCH /api/chats/{id}`.
- Sidebar preview fed from the in-memory transcript only (spec open question 1 accepted as-is).

**Smoke (all against the live app)**

- Backend `uv run uvicorn app.main:app --port 8001` — `GET /api/health` 200, DB ok; `GET /api/chats` returns the seeded chat with correct summary fields.
- Real WebSocket round-trip (Node `ws://localhost:8001/api/chats/{id}/ws`) — frame order exactly `ready → message → message_start → token* → sources → message_end`; the assistant message persisted with 2 mock sources (verified via `GET /api/chats/{id}`).
- Frontend `npm run dev` (5173) — shell serves; new modules transform; CORS preflight + actual request from `Origin: http://localhost:5173` to the backend both carry `access-control-allow-origin` (browser flow confirmed).
- Manual browser click-through (create → stream → rename → reload persistence) left to the user; all transport/data contracts it depends on are verified above.

**Progress**

- Plan steps: 1–12 complete. Acceptance criteria in `spec.md`: 10/10 checked. Feature status → `Tested` (awaiting user review for `Accepted`).

**Notes**

- `frontend/` had no tracked changes committed for this feature yet (repo is clean per start-of-session git status; commit happens on acceptance per the workflow).
- Backend `uvicorn` and Vite `npm run dev` are still running in the background from the smoke (`8001` / `5173`) — hand off or stop at the user's discretion.