# Plan — 006 Frontend UI (Chatbot)

- **Status:** `Complete`
- **Last updated:** 2026-09-27
- **Spec:** `spec.md`

> Written after this spec became `Specified`, before any code. Implementation is **not started**; a build session executes the steps below and appends to `implementation.md`.

## Context

The repo is spec-only today — no code anywhere. This feature builds the human-facing shell: a React + TypeScript chatbot UI (`frontend/`) with the three-region layout (sidebar conversation list · center transcript · bottom composer), streaming from the backend's `POST /api/chat` over SSE, markdown rendering, sources/citations, and a mock transport so UI development proceeds before the backend exists. Build decision #5 fixes tooling (Vite + React + TS). CLAUDE.md explicitly says *keep it simple*.

## Approach (one line)

Scaffold a Vite + React + TypeScript app in `frontend/`, model the chat contract as types, put all transport behind a `ChatService` interface (SSE + mock, env-selected), and build the three-region home screen as typed components on top of testable pure utils and hooks.

## Decisions (resolving the spec's open questions)

| Open question | Decision (default per spec) |
|---|---|
| Conversation list source | **Local-first**: persist to `localStorage` via `useConversations`. No backend endpoint exists; documented in spec. |
| Styling | **Plain CSS** (one global stylesheet, CSS custom properties, CSS grid for the 3-region layout). No utility framework — "do not overspend". |
| Markdown/code rendering | **`react-markdown` + `remark-gfm`**; code blocks styled via CSS (no syntax-highlighter lib). Minimal, per spec. |
| Contract ownership | Frontend defines `ChatEvent`/`Source` types now; SSE parser ignores unknown fields so the future backend can evolve them. Backend feature freezes the server side. |
| SSE transport mechanics | **`fetch` + `ReadableStream`** (NOT `EventSource` — `EventSource` can't POST). Parsing split into a pure, unit-tested module. |

## Steps (ordered)

1. **Scaffold the app** — from repo root: `npm create vite@latest frontend -- --template react-ts`; `cd frontend && npm install`. Add runtime deps `react-markdown remark-gfm`. Add dev deps `vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event`. Add npm scripts: `test` (vitest run), `test:watch`.
   - **Files:** `frontend/` scaffold, `frontend/package.json`, `frontend/vite.config.ts` (`test` block: environment `jsdom`), `frontend/tsconfig.json`.
2. **Environment config** — create `frontend/.env.development` and `.env.development.example` with `VITE_API_BASE_URL=http://localhost:8001`, `VITE_CHAT_TRANSPORT=mock` (default mock for dev; docs show `sse`).
3. **Types** — `src/types/chat.ts`: `Source`, `Message`, `Conversation`, `ChatEvent` discriminated union (`message_start | token | sources | message_end | error | done`).
4. **Pure utils** — `src/utils/sse.ts` (incremental SSE frame parser: line buffering, `event:`/`data:` fields, `[DONE]`, malformed-line tolerance) and `src/utils/messages.ts` (`appendToken`, `addSources`, `toUserMessage`, `toAssistantMessage`, `toErrorMessage`).
5. **Services** — `src/services/chatService.ts` (the `ChatService.send(payload): AsyncIterable<ChatEvent>` interface + `createChatService()` factory reading `import.meta.env`); `src/services/sseClient.ts` (`fetch` POST + `ReadableStream` reader → raw events); `src/services/SseChatService.ts`; `src/services/MockChatService.ts` (timed canned stream: markdown answer with list + code block + one `Source`, then `error` and delayed `done` paths).
6. **Hooks** — `src/hooks/useChat.ts` (send → iterate `ChatEvent`s → append tokens/sources into transcript state; `isLoading`, `error`); `src/hooks/useConversations.ts` (list/select/create + `localStorage` hydration & persistence under key `rag-chat.conversations.v1`).
7. **Components** — `src/pages/ChatPage.tsx` (layouts the three regions); `src/components/Sidebar/{Sidebar,ConversationItem}.tsx`; `src/components/Transcript/{Transcript,MessageBubble}.tsx`; `src/components/Markdown/MarkdownContent.tsx`; `src/components/Sources.tsx`; `src/components/Composer/Composer.tsx` (auto-grow textarea, Enter to send / Shift+Enter newline, disabled while streaming).
8. **Wire up** — `src/main.tsx`, `src/App.tsx` (state in hooks, passed down), `src/index.css` (grid layout: fixed sidebar / flex center / bottom composer; minimal message-bubble, code-block, source-chip styling).
9. **Tests** — unit tests below; run `npm test`, `npm run build` (tsc + vite build), dev-server smoke via mock.
10. **Close the loop** — tick acceptance criteria in the spec, append a dated entry to `implementation.md` after building.

## Files to create / modify

| Path | Purpose |
|---|---|
| `frontend/` (scaffold) | Vite + React + TS app, `package.json`, configs, `index.html` |
| `frontend/.env.development(.example)` | `VITE_API_BASE_URL`, `VITE_CHAT_TRANSPORT` |
| `frontend/src/types/chat.ts` | `Conversation`, `Message`, `Source`, `ChatEvent` |
| `frontend/src/utils/{sse,messages}.ts` | pure, testable parsers/helpers |
| `frontend/src/services/{chatService,sseClient,SseChatService,MockChatService}.ts` | transport behind the interface |
| `frontend/src/hooks/{useChat,useConversations}.ts` | transcript + conversation state |
| `frontend/src/pages/ChatPage.tsx`, `src/components/…`, `src/App.tsx`, `src/main.tsx`, `src/index.css` | layout & rendering |
| `frontend/src/**/*.test.{ts,tsx}` | Vitest unit tests |
| `specs/features/006-frontend-ui/implementation.md` | log appended during builds |

## Test strategy

- **Unit (Vitest, jsdom):** `sse.test.ts` — frame parsing (multi-line, event+data, `[DONE]`, garbage tolerance); `messages.test.ts` — token append, sources merge, error message.
- **Hooks (@testing-library/react `renderHook`):** `useChat.test.tsx` against `MockChatService` — happy path (stream → final content), error path; `useConversations.test.tsx` with `localStorage` mocked — create/select/persist round-trip.
- **Regression/smoke:** `npm run build` (type-check), manual dev-server walkthrough with `VITE_CHAT_TRANSPORT=mock` (layout, streaming, new-conversation, sources). Real-backend smoke is deferred to the backend feature (sse transport).

## Risks / dependencies

- SSE over POST needs `ReadableStream` on `fetch` — supported in all modern browsers; the parser is isolated and unit-tested to absorb backend format drift.
- No backend yet → the `MockChatService` keeps dev + tests green and unblocked.
- `react-markdown` v9+ is ESM-only — fine under Vite (no CommonJS concern).
- `localStorage` can be empty/throwing (private mode, tests) → wrapped in try/catch; UI renders without it.

## Definition of Done for this plan

A build session considers this feature Done when all 11 acceptance criteria in `specs/features/006-frontend-ui/spec.md` are ticked, frontend runs (`npm run dev`), `npm test` and `npm run build` pass, and an entry is appended to `implementation.md`.