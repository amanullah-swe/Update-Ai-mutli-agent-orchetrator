# Implementation Log — 006 Frontend UI (Chatbot)

- **Status:** `Tested`
- **Spec:** `spec.md`
- **Plan:** `plan.md`

> **Append-only.** Every build session adds a dated entry here (newest at the bottom). Never edit older entries — this is the back-tracking record. Format: `specs/templates/implementation.md`.

## Log

### 2026-09-27 — Initial build: Vite + React + TS chat UI

**Session scope:** Execute `specs/features/006-frontend-ui/plan.md` steps 1–9 (scaffold through tests + smoke). All 11 acceptance criteria ticked in `spec.md`.

**What was done**

- Scaffolded `frontend/` with Vite 8 (react-ts template) + React 19 + TS 6 + oxlint; added `react-markdown` + `remark-gfm`; added `vitest` + `jsdom` + `@testing-library/react|jest-dom|user-event` as dev deps; added `test`/`test:watch` scripts; configured the vitest `test` block (jsdom, `src/test/setup.ts`, include `src/**/*.test.{ts,tsx}`).
- Env config: `.env.development` + `.env.development.example` with `VITE_API_BASE_URL` and `VITE_CHAT_TRANSPORT`; `.gitignore` now ignores `.env*` except `*.example`.
- Types (`src/types/chat.ts`): `Conversation`, `Message`, `Source`, `ChatEvent` discriminated union, `ChatPayload`, `Role`.
- Pure utils: `src/utils/sse.ts` (incremental SSE parser — blank-line framing, CRLF normalization, multi-line `data:`, comment/unknown-field tolerance, `[DONE]` sentinel) and `src/utils/messages.ts` (`createId`, `appendToken`, `addSources` de-dup, `conversationTitle`, message factories).
- Services: `chatService.ts` (`ChatService` interface + `createChatService()` factory selecting transport from env), `sseClient.ts` (`fetch` POST + `ReadableStream` → `SseFrame`s), `SseChatService.ts` (frame → `ChatEvent` mapping, unknown events dropped, tolerant `parseSources`), `MockChatService.ts` (timed canned stream: markdown answer with list + code block + 2 sources; "fail"/"error" in the message triggers a streamed `error` event).
- Hooks: `useChat.ts` (streams into the transcript, binds conversation via ref, guards concurrent sends, error/debounce), `useConversations.ts` (localStorage persistence under `rag-chat.conversations.v1`, auto-title from first user message, corrupt-storage tolerance).
- Components: `ChatPage` (grid layout + wiring/`onTranscriptChange` persistence), `Sidebar` + `ConversationItem`, `Transcript` + `MessageBubble`, `MarkdownContent`, `Sources`, `Composer` (auto-grow, Enter=send, Shift+Enter=newline, disabled while streaming). Global styles in `index.css` (design tokens, three-region grid). Removed scaffold demo (`App.css`, `assets/`).

**Deviations from plan & why**

- Plan's `useChat` sketch had the event dispatcher as a separate `applyEvent` callback; final code inlines the switch into `send` to satisfy `exhaustive-deps` without a temporal-dead-zone dep reference (lint-driven, no behavior change).
- `onTranscriptChange` signature carries the bound `conversationId` (not just messages) so conversation persistence is correct even when the selection changes mid-stream (fixes a stale-closure bug found during implementation).
- Mock delay is configurable (`{ tokenDelayMs }`) so hook tests can run without artificial waiting; not in the plan but required by the test strategy.

**Tests run / results**

- `npx vitest run` → 4 files, **33 passed** (utils/sse: 12, utils/messages: 10, useChat: 5, useConversations: 6).
- `npm run build` (tsc -b + vite build) → clean; 284 modules; bundle 384 kB (118 kB gzip).
- `npm run lint` (oxlint) → no warnings/errors.
- Dev-server smoke: `npm run dev` → HTTP 200 on `/` with title "RAG Learning Platform — Chat".

**Decisions made**

- Streaming uses `fetch` + `ReadableStream` rather than `EventSource` (EventSource cannot POST) — matches the SSE-over-POST backend contract; no ADR needed (recorded in plan).
- Conversation list is localStorage-only until the backend defines `GET /api/conversations` (spec open question default kept).

**Progress**

- Plan steps: 1–9 complete (scaffold, env, types, utils, services, hooks, components, wiring, tests/smoke). Step 10 (this log + AC ticking) done here.
- Acceptance criteria in `spec.md`: 11/11 checked. Feature status → `Tested` (awaiting user review for `Accepted`).

**Notes**

- Real-backend streaming validation (`VITE_CHAT_TRANSPORT=sse`) is deferred to the backend chat feature, per plan.
- `frontend/` is currently untracked in git (no commit yet).