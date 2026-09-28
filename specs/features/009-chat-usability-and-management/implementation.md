# Implementation Log — 009 Chat usability & conversation management

- **Status:** `Tested`
- **Spec:** `./spec.md`
- **Plan:** `./plan.md`

> **Append-only.** Every build session adds a dated entry here (newest at the bottom). Never edit older entries — this is the back-tracking record. Format: `specs/templates/implementation.md`.

## Log

### 2026-09-28 — Six UX fixes: layout shell, rename/delete affordances, composer width

**Session scope:** Execute `specs/features/009-chat-usability-and-management/plan.md` steps 1–12. Spec set `Draft → Specified → Planned → Tested`; all 10 acceptance criteria ticked.

**Root-cause analysis (per reported issue)**

| # | Issue | Root cause | Fix |
|---|-------|-----------|-----|
| 1 | No rename button | `ConversationItem` had no affordance; `renameConversation` (PATCH, from 008) was never wired to the UI | Pencil button → inline title editor (Enter/blur save, Escape/blank cancel) |
| 2 | No delete button | No affordance **and no backend route** — 007 deferred it (open question 1); the cascade FK already existed | `DELETE /api/chats/{id}` (204, cascade) + `chatApi.deleteChat` + `deleteConversation` + × button (native confirm) |
| 3 | No auto-scroll | **Shared layout bug** — `.chat-layout`'s implicit `auto` grid row grew to the transcript's max-content (4159px inside a 707px viewport); the pane never overflowed, so the existing `scrollTop = scrollHeight` effect was a no-op | `grid-template-rows: minmax(0, 1fr)` + `overflow: hidden` on the shell; `min-height: 0; overflow: hidden` on the main pane → auto-scroll works with zero code change in `Transcript` |
| 4 | Sidebar scrolls with page | Same layout bug — the sidebar stretched to the grown row (4235px) instead of scrolling internally | Same fix (verified: client 707 / scroll 1446) |
| 5 | Composer scrolls | Same layout bug — the composer sat at the bottom of the 4235px page | Same fix (composer pinned top 631 / bottom 707) |
| 6 | Input too wide | `.composer__input { flex: 1 }` spanned the whole pane (857px) vs messages capped at 760px | `.composer` becomes block; textarea + Send wrapped in centered `.composer__row` (max-width 760px, margin 0 auto) |

**What was done**

- `backend/app/services/conversation_service.py` — `delete_chat(db, chat_id)`: `get_chat` (404) then `db.delete` + commit; messages cascade via the FK.
- `backend/app/api/routes/chats.py` — `DELETE /{chat_id}` route, `status_code=204`, returns `Response` (no body).
- `backend/tests/test_chats_crud.py` — 3 new tests: 204 + row gone (GET → 404) + empty body; cascade removes the chat's messages; 404 for unknown id.
- `frontend/src/services/chatApi.ts` — `request` gains a `parseJson` flag (204 has no body); new `deleteChat(id)`; doc comment lists DELETE.
- `frontend/src/hooks/useConversations.ts` — `deleteConversation(id): Promise<boolean>`: DELETE, remove from list on success, clear `activeId` if it was active, return success; errors surface on the existing page-error line.
- `frontend/src/components/Sidebar/ConversationItem.tsx` — new `onRename`/`onDelete` props; hover/active-revealed action cluster (pencil + ×, inline SVG); inline rename editor with Enter/blur save, Escape/blank cancel, and a `cancelPending` ref guarding the Escape→blur race (reset on each `startRename`).
- `frontend/src/components/Sidebar/Sidebar.tsx` — threads `onRename`/`onDelete` through to each item.
- `frontend/src/pages/ChatPage.tsx` — `handleDelete`: native `confirm("Delete this conversation?")` → `deleteConversation`, then `load('', [])` if the deleted chat was active (transcript returns to the empty state).
- `frontend/src/components/Composer/Composer.tsx` — input + Send wrapped in `<div className="composer__row">`.
- `frontend/src/index.css` — shell row fix (`.chat-layout` `grid-template-rows: minmax(0, 1fr)` + `overflow: hidden`; `.chat-layout__main` `min-height: 0; overflow: hidden`); `.composer__row` (flex, max-width 760px, centered); item row/actions/rename styles.
- `frontend/src/test/setup.ts` — added explicit `afterEach(cleanup)` (vitest runs without `globals`, so `@testing-library/react`'s auto-cleanup never registers — without this, DOM accumulated across tests in a file).
- Docs: `CLAUDE.md` § Backend API surface gains `DELETE /api/chats/{id}` (009); 007 spec open question 1 marked resolved (two places: scope note + Open questions).

**Deviations from plan & why**

- `handleDelete` also calls `load('', [])` when the deleted chat was active (plan said "clears selection"; clearing the stale in-memory transcript too is what actually empties the pane).
- Added `frontend/src/test/setup.ts` cleanup — not in the plan's file list; required because DOM was leaking between tests in `ConversationItem.test.tsx` (vitest has no `globals: true`).
- No unit test for the layout fixes (#3–#5, #6) — jsdom has no layout engine; verified in a real browser instead (below). The plan flagged this risk and the spec says so.
- `window.confirm` is stubbed in the browser verification (`window.confirm = () => true`) and would be mocked in tests if `ChatPage` gets component tests.

**Tests run / results**

- `uv run pytest` (backend) — **26 passed** (23 existing + 3 new DELETE).
- `npm test` (frontend) — 6 files, **44 passed** (33 existing + 11 new: chatApi delete ×2, useConversations delete ×3, ConversationItem ×6).
- `npm run build` (tsc -b + vite build) — clean; 387 kB bundle (119 kB gzip).
- `npm run lint` (oxlint) — no warnings.

**Browser verification (headless Chromium, live app, 1280×850)**

- With the seeded 40-message transcript + 33 chats: `bodyScrollHeight` 707 == `innerHeight` 707 (page never scrolls); sidebar client 707 / scroll 1446 (independent scroll); transcript auto-scrolled to bottom (`scrollTop` 3528 = scrollHeight − clientHeight) — issues 3, 4, 5 confirmed fixed.
- Composer pinned at viewport bottom (top 631 / bottom 707); input row 680px (input) + Send ≈ 760px message measure — issue 6 confirmed.
- **Delete end-to-end:** stubbed confirm → clicked a chat's × → item removed from the sidebar (34 → 33 rows) and the transcript cleared.
- **Rename end-to-end:** clicked a chat's pencil → prefilled editor → typed + Enter → sidebar updated and `GET /api/chats` returned the new title (server persisted).
- Test data seeded for verification (30 `Bulk chat #N`, `Long scroll test`, one curl-created chat) was removed afterward; only the user's chats remain (`heloo`, `live smoke (renamed)`).

**Decisions made**

- Delete confirmation uses the native `window.confirm` (simple + safe; spec open question 1).
- Action buttons reveal on hover, always visible on the active item, and on keyboard focus (`:focus-within`) — spec open question 2.
- Composer row width set to exactly the message measure (760px) per the request "same or a little wider than messages".

**Progress**

- Plan steps 1–12 complete. Acceptance criteria in `spec.md`: 10/10 checked. Feature status → `Tested` (awaiting user review for `Accepted`).

### 2026-09-28 — Revision 2: three-dot menu + custom delete modal (user review)

**Session scope:** Execute `plan.md` steps 13–18 (the Revision 2 section). The first build's per-item pencil + × controls and the native `window.confirm` were rejected on review; both were replaced. Data contracts from steps 5–8 are unchanged — this is a pure affordance/UX revision. `spec.md` and `plan.md` were revised **before** any code (spec-first on change).

**What was done**

- `frontend/src/components/ConfirmDialog/ConfirmDialog.tsx` **(new)** — reusable controlled modal: `{ open, title, message?, confirmLabel?, cancelLabel?, danger?, onConfirm, onCancel }`. `createPortal` into `document.body` (no ancestor overflow/stacking context can clip it); `role="dialog"` + `aria-modal="true"` + `aria-labelledby` via `useId`. Escape and a backdrop `onMouseDown` dismiss (only when the press *starts* on the backdrop, so a drag out of the panel doesn't close it). Focus lands on **Cancel** — the safe action — on open. The keydown effect reads `onCancel` through a ref so parent re-renders don't re-run it and steal focus back to Cancel.
- `frontend/src/components/ConfirmDialog/ConfirmDialog.test.tsx` **(new)** — 6 tests: closed renders nothing; title/message/actions render with `aria-modal`; Cancel focused on open; confirm/cancel callbacks fire correctly; Escape cancels; backdrop press cancels while a press inside the panel does not.
- `frontend/src/components/Sidebar/ConversationItem.tsx` — `.conversation-item__actions` (pencil + ×) replaced by **one kebab button** (`.conversation-item__kebab`, inline three-dot SVG, `aria-haspopup="menu"`, `aria-expanded`, `aria-label="More actions for {title}"`) opening a `role="menu"` with two `role="menuitem"` buttons — **Rename** and **Delete**. Opening the menu focuses the first action and never selects the chat. Closes on choosing an action, on Escape (returning focus to the kebab), and on any outside `pointerdown` (checked against `menuRef` + `kebabRef`). MENU_FIT_HEIGHT (96px) + `getBoundingClientRect().bottom` vs `window.innerHeight` decides whether the menu opens below or flips up.
- `frontend/src/pages/ChatPage.tsx` — `window.confirm` **removed**. New `pendingDelete: { id, title } | null` state: the sidebar's `onDelete(id)` only *records* the request (`handleDeleteRequest`, looking the title up in `conversations`), and `ConfirmDialog` asks. `confirmDelete` clears the pending target, runs `deleteConversation`, and calls `load('', [])` when the deleted chat was active (transcript returns to the empty state). Cancel/Escape/backdrop just null the pending target — nothing changes.
- `frontend/src/index.css` — `.conversation-item__row { position: relative }` (menu anchor); `.conversation-item__kebab` (revealed on hover / active item / `:focus-visible` / `[aria-expanded="true"]`); `.conversation-item--menu-open` (raised z-index); `.conversation-item__menu` + `--up` (absolute, `top/bottom: calc(100% - 2px)`, shadow); `.conversation-item__menu-item` + `--danger` (red text, red-tinted hover); the `.modal*` block (fixed inset-0 backdrop `rgba(15,22,38,.45)`, centered white panel 420px, title/message, right-aligned action row, primary + danger buttons).

**Deviations from plan & why**

- None of substance. Step 18's browser check added one case the plan didn't list — the **flip-up** path — because 8 chats don't overflow an 850px viewport; it needed a 26-chat list with the sidebar scrolled to the bottom to exercise.
- The flip geometry is `bottom: calc(100% - 2px)`, i.e. the menu's bottom edge sits 2px *below* the row's top edge (a deliberate 2px overlap so the menu doesn't float detached from the row). An early assertion of mine (`menuRect.bottom <= rowRect.top`) was therefore off by that 2px; the correct reading is `menuRect.top < rowRect.top && menuRect.bottom < rowRect.bottom` — verified true (row top 653 / bottom 691; menu top 587 / bottom 655, fully inside the 707px viewport).

**Tests run / results**

- `npm test` — 7 files, **54 passed** (was 44 before revision 2: −6 old pencil/× item tests, +9 rewritten menu tests, +6 new `ConfirmDialog` tests, +1 net elsewhere).
- `npm run build` (`tsc -b` + `vite build`) — clean; 389.82 kB (119.77 kB gzip).
- `npm run lint` (oxlint) — no warnings.
- Backend untouched this revision (no re-run needed; its 26 tests passed at the previous commit-state).

**Browser verification (headless Chromium, live app, 1280×850, 26-chat list)**

Scripts stubbed `window.confirm` to count calls and return `false`, so a surviving native call would both be recorded and visibly break the flow. Final consolidated run:

| Check | Result |
|---|---|
| Kebab opens menu | `menuOpened: true`, items `["Rename","Delete"]` |
| Opening never selects the chat | `selectedUnchanged: true` |
| Delete → modal | open, title `Delete conversation?`, Cancel + **danger** Delete present, message names the chat |
| Cancel dismisses | modal closed, chat still in the sidebar |
| Confirm deletes | row gone, modal closed, **server persisted** (`GET /api/chats` no longer lists it) |
| Rename via menu | sidebar updated **and** server persisted (`kebab-renamed-v2`) |
| Flip-up near viewport bottom | `menuFlipped: true`; menu top 587 / bottom 655 vs row top 653 / bottom 691 — above the row, fully in viewport |
| Native `window.confirm` | **never called** (`confirmNeverCalled: true`) |

Screenshot of the open modal confirmed visually: dimmed backdrop, centered 420×167 panel naming the chat in quotes, Cancel focused (outline), red Delete.

**Decisions made**

- The kebab is the only per-item control; Rename/Delete live in the menu (spec open question "Affordance shape" → resolved).
- Delete confirmation is the in-app `ConfirmDialog`; `window.confirm` no longer appears anywhere in the app (spec open question "Delete confirmation" → resolved).
- Focus-on-open goes to Cancel, not Delete — the destructive action is never one Enter away.
- Menu keyboard support: Tab reaches both items; roving arrow-key focus deliberately not implemented (spec open question, unchanged — revisit if the menu grows past two actions).

**Test data**

- Verification seeded 24 disposable chats (`kebab-*`, `filler-*`); all 24 deleted afterwards via the API. The only remaining chat is the user's own `test 1` (created 2026-09-27, 8 messages) — untouched.

**Progress**

- Plan steps 13–18 complete; all steps for feature 009 are now ticked. Acceptance criteria in `spec.md`: 11/11 checked. Status stays `Tested` (awaiting user review for `Accepted`).
