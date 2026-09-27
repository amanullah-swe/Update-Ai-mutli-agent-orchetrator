# 006 — Frontend UI (Chatbot)

- **Status:** `Tested`
- **Last updated:** 2026-09-27
- **Depends on:** `none` (consumes the backend API surface from CLAUDE.md; backend feature specs are future work)
- **Source:** CLAUDE.md — Frontend (minimal chat UI), Backend API surface (minimum), Build decision #5

## Problem / Motivation

There is no UI yet — the platform is only spec documents. The chat UI is the human-facing front door: users talk to the AI agent and read RAG-grounded answers with citations. It must be the shell that makes the platform visible and testable, wired to the backend's streaming `/api/chat`.

The CLAUDE.md contract is explicit: React + TypeScript, `frontend/` package, SSE client for `/api/chat`, streaming responses, source/citation display. Build decision #5 fixes the tooling (→ Vite + React + TypeScript). Keep it simple — the spec warns against overspending on visual customization.

## Scope

**In scope**

- `frontend/` package (Vite + React + TypeScript) — `components/`, `pages/`, `hooks/`, `services/`, `types/`, `utils/`
- Chatbot home screen with a three-region layout:
  - **Left sidebar** — conversation list + new-conversation action
  - **Center** — scrolling user/assistant message transcript
  - **Bottom** — message composer (input + send)
- Streaming chat over SSE against `POST /api/chat`
- Markdown + code block rendering for assistant messages
- Loading and error states
- Source/citation display attached to assistant messages
- `services/`: SSE client, API client, and a mock transport so the UI is developable before the backend exists
- Unit tests for `utils/` and the core hooks

**Out of scope** (future features)

- Backend endpoints — the UI only *consumes* the CLAUDE.md API surface; backend implementation is its own feature
- Document upload / management screens (`POST|GET|DELETE /api/documents/…` exposed in the API surface but not this feature's screen)
- Evaluation & experiment screens (their API endpoints exist in the surface; later features)
- Auth, theming system, responsive/mobile polish — nothing beyond a functional desktop layout
- Visual customization beyond minimal styling

## Behavioral contract

### Interfaces

The frontend has no CLAUDE.md "Common Interface", but holds its own stable contracts (declared in `types/`, consumed in `services/`):

- `Conversation` — `{ id, title, created_at, messages?: Message[] }`
- `Message` — `{ id, role: "user" | "assistant", content, created_at, sources?: Source[] , error?: boolean }`
- `Source` — `{ document_id, chunk_id, snippet, score?, metadata? }` (shape frozen against the backend's chat response when that feature lands)
- `ChatEvent` — discriminated union of SSE frames: `{ type: "token" | "message_start" | "message_end" | "error" | "done", ... }`
- `ChatService` (in `services/`) — `{ send(...): AsyncIterable<ChatEvent> }`, implemented by `SseChatService` (backend) and `MockChatService` (dev without backend), selected by config/env — mirrors the interface-over-concrete rule at a client scale.

### Data flow

1. App mounts → loads conversation list → home screen renders (sidebar / transcript / composer).
2. User types + sends → `ChatService.send(payload)` opens an SSE connection to `POST /api/chat`.
3. Incoming `ChatEvent` frames stream into the active conversation → transcript re-renders incrementally (no full-page reload).
4. `message_end`/`done` closes the stream; any `error` frame surfaces an inline error state.
5. New-conversation resets the transcript and adds a fresh conversation to the sidebar list.

### Configuration

```env
# frontend/.env.development
VITE_API_BASE_URL=http://localhost:8001
VITE_CHAT_TRANSPORT=sse        # sse | mock — mock lets the UI run without a backend
```

## Acceptance criteria

- [x] `frontend/` Vite + React + TypeScript scaffold runs (`npm run dev`)
- [x] Home screen shows the three-region layout: sidebar (conversation list), center transcript, bottom composer
- [x] Composer sends a message and streams the assistant reply token-by-token over SSE from `POST /api/chat`
- [x] Assistant messages render markdown and code blocks
- [x] Sidebar lists conversations; clicking one loads it; new-conversation starts a fresh thread
- [x] Loading state while awaiting the first token; error state rendered inline on stream failure
- [x] Assistant messages display sources/citations when the event carries them
- [x] `ChatService` has at least two transports — SSE and mock — switched by env, no backend required for UI dev
- [x] `types/` defines `Conversation`, `Message`, `Source`, `ChatEvent`; `services/` and `hooks/` depend on types, not on fetch internals
- [x] Unit tests cover `utils/` (e.g. message merge, event parsing) and the use-chat hook (send → stream → done/error)
- [x] No backend code is introduced by this feature

## Open questions

- [ ] Conversation list source: the minimum API surface has no `GET /api/conversations` — should the sidebar persist locally (localStorage) for now, or does the backend chat feature add that endpoint? (Local-first is the default until that decision.)
- [ ] Styling approach: plain CSS / CSS modules vs. a utility framework given "do not overspend on visual customization"
- [ ] Markdown/code rendering: hand-rolled renderer vs. a small library (`react-markdown` + syntax highlighter)
- [ ] `Source` / `ChatEvent` shapes must be frozen against the backend chat spec when it lands — who owns the contract first?

## Notes / links

- Monorepo contract: `frontend/` → `components/`, `pages/`, `hooks/`, `services/`, `types/`, `utils/`
- CLAUDE.md Frontend section: "User/assistant message list, input box + send, streaming responses, markdown + code block rendering, loading/error states, new-conversation, and source/citation display. Keep it simple."
- Build decision #5: → Vite + React + TypeScript, with an SSE client for `/api/chat` streaming
- Backend surface consumed: `POST /api/chat` (SSE), `GET /api/health`