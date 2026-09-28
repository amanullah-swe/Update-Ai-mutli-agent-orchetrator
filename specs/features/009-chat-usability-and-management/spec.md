# 009 — Chat usability & conversation management (rename / delete / scrolling / composer)

- **Status:** `Tested`
- **Last updated:** 2026-09-28
- **Depends on:** `006-frontend-ui` (the UI shell) · `007-backend-api` (the chat CRUD surface) · `008-frontend-api-integration` (server-backed conversations + WebSocket streaming)
- **Source:** User bug report (6 issues) · CLAUDE.md § Frontend (minimal chat UI) · § Backend API surface · 007 spec open question 1 (delete chat, deferred "ask before adding")

## Problem / Motivation

The live app (008, `Tested`) has six reported usability defects. Four share **one root cause** in the layout shell:

**Root cause (issues 3, 4, 5): the app shell scrolls as a single page.** `.chat-layout` is a CSS grid with an implicit `auto` row and `height: 100%`. A tall transcript (or many chats) makes that row grow to its **max-content** height (verified live: a 40-message transcript inflated the row to 4159px inside a 707px viewport). The grid items — sidebar and main pane — stretch to the grown row and overflow the fixed shell, so the browser scrolls the **whole document**:

- **Issue 4** — the sidebar (with `overflow-y: auto` that *should* scroll) is stretched to 4235px and scrolls with the page instead of independently.
- **Issue 5** — the composer sits at the bottom of the 4235px page and scrolls away; nothing keeps it pinned to the viewport.
- **Issue 3** — the transcript pane never becomes a real scroll container (no overflow), so `Transcript`'s existing auto-scroll (`useEffect` → `scrollTop = scrollHeight`) is a silent no-op: there is nothing to scroll. The effect is correct; the container was wrong.

Verified fix (headless Chromium, before/after): making the grid row definite — `grid-template-rows: minmax(0, 1fr)` + `overflow: hidden` on the shell and `min-height: 0; overflow: hidden` on the main pane — yields `bodyScrollHeight == innerHeight` (707px), sidebar scrollHeight 1406 inside a 707px client (independent scroll), transcript auto-scrolled to the bottom (scrollTop 3528 = scrollHeight − clientHeight), and the composer pinned at the viewport bottom.

**Issue 6 (composer width):** `.composer__input { flex: 1 }` spans the whole main pane (measured 857px) while messages are capped by `.transcript__list { max-width: 760px; margin: 0 auto }`. The input is far wider than the message column. Verified fix: wrap the input + Send button in a centered `.composer__row { max-width: 760px; margin: 0 auto }` so the input matches the message measure.

**Issues 1 & 2 (rename / delete):** no affordances exist in `ConversationItem`. `useConversations.renameConversation` (→ `PATCH /api/chats/{id}`, implemented in 008) is never wired to a control. Delete needs **both** UI and a backend route — 007 deferred it (open question 1: *"When the UI grows a delete affordance, add `DELETE /api/chats/{id}` with cascade to messages (the FK already cascades). (Deferred — ask before adding.)"*). The user's report **is** that request; the FK `messages → conversations ON DELETE CASCADE` is already in the schema, so the route is cheap.

**Revision 2 (affordance + confirmation, per user review of the first build):** the first build put a pencil and an × directly on every item and confirmed deletes with the native `window.confirm`. The user asked for both to change: the two controls collapse into **one three-dot (kebab) button** that reveals **Rename** and **Delete** in a small menu, and the delete confirmation becomes a **custom in-app modal** (no browser alert). This is a pure affordance/UX revision — the data contracts (`onRename`, `onDelete`, `deleteConversation`, `DELETE /api/chats/{id}`) are unchanged.

## Scope

**In scope**

- **Layout shell fix (one root cause, three issues):** `.chat-layout` gains `grid-template-rows: minmax(0, 1fr)` and `overflow: hidden`; `.chat-layout__main` gains `min-height: 0; overflow: hidden`. Result: page never scrolls; sidebar scrolls independently; transcript is a real scroll container (auto-scroll works); composer is pinned to the viewport bottom.
- **Composer width fix:** `.composer` becomes a block container; textarea + Send move into a centered `.composer__row` (max-width 760px, matching the message column).
- **Item affordances (sidebar):** one **three-dot (kebab) button** per item opens a small menu containing **Rename** and **Delete**. Rename reveals an inline title editor; Enter/blur saves via `PATCH /api/chats/{id}`, Escape cancels, blank is rejected (cancel). Delete opens a custom confirmation modal (below).
- **Delete confirmation modal:** a reusable in-app `ConfirmDialog` (no native `window.confirm`) — title, message naming the chat, Cancel + Delete actions; Escape, the backdrop, and Cancel all dismiss; the destructive action is visually marked.
- **Delete:** confirmed delete calls `DELETE /api/chats/{id}`, removes the item, clears the transcript/selection if the deleted chat was active.
- **Backend `DELETE /api/chats/{id}`:** returns 204; cascades to messages via the existing FK; 404 for unknown ids. Resolves 007 open question 1.
- `chatApi.deleteChat`, `useConversations.deleteConversation`, the pending-delete state in `ChatPage`, prop threading through `Sidebar` → `ConversationItem`.
- Unit tests (frontend + backend), build + lint clean, headless-browser verification of the layout fixes (jsdom has no layout engine, so #3–#5 are verified by browser automation, not unit tests).
- CLAUDE.md § Backend API surface updated with `DELETE`; 007 spec open question 1 marked resolved.

**Out of scope** (future features)

- Socket reconnect/resume (007 open question 3), auth, document/evaluation/experiment screens.
- Sidebar preview text from the server (`last_message` snippet on `ChatSummary` — 007 change, 008 open question).
- Any other backend behavior (no schema change needed; the cascade FK already exists).

## Behavioral contract

### Interfaces

No CLAUDE.md Common Interface is involved. Frontend stays on its existing stable contracts (`types/chat.ts`, `ChatService`, `chatApi`):

- `chatApi.deleteChat(id: string): Promise<void>` — `DELETE /api/chats/{id}`, resolves on 204, throws with the backend error detail otherwise (same contract as the other verbs).
- `useConversations.deleteConversation(id: string): Promise<boolean>` — calls the API; on success removes the conversation from the list and clears `activeId` if it was active; on failure keeps state and returns `false`.
- `ConversationItem` grows two props: `onRename(id, title)` and `onDelete(id)` (both optional so the item stays renderable without them). `onDelete` now means *"the user asked to delete this chat"* — the confirmation happens above it, so the item never deletes anything itself.
- **New** `ConfirmDialog` — a reusable, controlled modal: `{ open, title, message?, confirmLabel?, cancelLabel?, danger?, onConfirm, onCancel }`. Renders into `document.body` via a portal; `role="dialog"` + `aria-modal`; Escape and backdrop dismiss. Deleting a chat is its first consumer.

### Data flow

1. **Rename** — user clicks the item's kebab → menu → **Rename** → inline editor (prefilled title) → Enter/blur → `onRename(id, trimmed)` → `renameConversation` → `PATCH /api/chats/{id}` → server + sidebar both update. Escape or a blank value cancels (no request). Choosing an action closes the menu.
2. **Delete** — user clicks the item's kebab → menu → **Delete** → `onDelete(id)` → `ChatPage` records a *pending delete* (id + title) and opens `ConfirmDialog` → **Delete** → `deleteConversation(id)` → `DELETE /api/chats/{id}` (204) → item removed; if it was the active chat, the transcript clears to the empty state and `activeId` becomes null. **Cancel**, Escape, or the backdrop closes the modal with nothing changed; a failed request surfaces via the existing page error line.
3. **Menu behaviour** — the kebab toggles the menu (`aria-haspopup="menu"`, `aria-expanded`); the menu closes on choosing an action, on Escape, and on any click outside it. Opening it must never select the chat.
4. **Layout** — pure CSS; no data-flow change. The transcript/sidebar/composer panes scroll exactly as they render.

### Configuration

None. No env/config change; transport, API base URL, and provider selection are untouched.

### Errors

- Rename: backend 422 (blank) never fires because blank cancels client-side; other failures (404, network) surface via `renameConversation`'s existing error path → page error line.
- Delete: 404 (already deleted) and network failures surface via `deleteConversation` → page error line; state is only mutated on success.

## Acceptance criteria

- [x] Sidebar affordances: every conversation has a single three-dot button; opening it shows Rename and Delete; it never selects the chat; it closes on choosing an action, on Escape, and on an outside click.
- [x] Sidebar rename: the menu's Rename opens the inline editor; it saves via `PATCH /api/chats/{id}` and the new title persists across a reload; Escape cancels; blank cancels.
- [x] Sidebar delete: the menu's Delete opens a **custom modal** (no `window.confirm` anywhere in the app); confirming calls `DELETE /api/chats/{id}`, removes the row, and (if active) clears the transcript and selection. Cancel / Escape / backdrop dismiss with nothing changed.
- [x] Backend `DELETE /api/chats/{id}`: 204 on success, cascades the chat's messages (FK `ON DELETE CASCADE`), 404 for an unknown id.
- [x] The page itself never scrolls: `document.body.scrollHeight` equals the viewport height with a long transcript and many chats (verified in a real browser).
- [x] Sidebar and transcript scroll independently of each other; the composer stays pinned at the viewport bottom regardless of transcript length.
- [x] Auto-scroll: the latest message stays in view while streaming and immediately after selecting a chat with a long transcript (verified in a real browser).
- [x] Composer input row is constrained to the message column measure (~760px), not the full pane width.
- [x] CLAUDE.md § Backend API surface lists `DELETE /api/chats/{id}`; 007 spec open question 1 is marked resolved.
- [x] `npm test`, `npm run build`, `npm run lint` pass in `frontend/`; `uv run pytest` passes in `backend/`.
- [x] Feature logged in `implementation.md`; status reaches `Tested`.

## Open questions

- [x] **Delete confirmation:** resolved in revision 2 — a custom `ConfirmDialog` modal replaced the native `window.confirm` (the user asked for an in-app modal).
- [x] **Affordance shape:** resolved in revision 2 — the pencil + × were replaced by a single three-dot menu, per user review.
- [ ] **Kebab visibility:** the three-dot button reveals on hover, stays visible on the active item, and shows on keyboard focus (`:focus-within`). Making it permanently visible on every row is a styling choice, not a contract change.
- [ ] **Menu interaction details:** click-outside + Escape close the menu; arrow-key roving focus within the menu is not implemented (Tab reaches the items). Add roving focus if the menu grows past two actions.

## Notes / links

- Root-cause verification (headless Chromium, 1280×850): baseline `bodyScrollHeight` 4235 vs `innerHeight` 707 with 33 chats + a 40-message transcript; after the candidate CSS, `bodyScrollHeight` 707, sidebar `clientHeight` 707 / `scrollHeight` 1406, transcript auto-scrolled to bottom (`scrollTop` 3528 = `scrollHeight` − `clientHeight`).
- 007 spec open question 1 (delete chat) is resolved here — this feature is the requested follow-up.
- 008 spec open question (sidebar preview) remains open; unchanged by this feature.
- The layout fix relies on the CSS grid `minmax(0, 1fr)` idiom (definite row, items clipped at `min-height: 0`) — the standard remedy for grid rows growing to content height.
