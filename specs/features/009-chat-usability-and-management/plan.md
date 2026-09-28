# Plan — 009 Chat usability & conversation management

- **Status:** `Planned`
- **Last updated:** 2026-09-28
- **Spec:** `./spec.md`

> Written **after** the spec is `Specified` and **before** any code. The plan breaks the spec into concrete steps Claude Code can execute and tick off.

## Approach (one line)

A small, mostly-CSS layout fix (one grid-row root cause fixes issues 3–5, plus a composer row wrapper for 6) and two wired-up sidebar affordances (rename/delete) backed by one new backend route (`DELETE /api/chats/{id}`), each with unit tests.

## Steps (do these in order)

1. [x] **Backend: `DELETE /api/chats/{id}`** — add `delete_chat(db, chat_id)` to `conversation_service.py` (404 via `get_chat`, then `db.delete` + commit; messages cascade via the existing FK) and a `DELETE` route in `chats.py` (204). Touches: `backend/app/services/conversation_service.py`, `backend/app/api/routes/chats.py`
2. [x] **Backend: DELETE tests** — 204 + row gone (GET → 404), cascade removes the chat's messages, 404 for unknown id. Touches: `backend/tests/test_chats_crud.py`
3. [x] **Layout shell fix** — `.chat-layout { grid-template-rows: minmax(0, 1fr); overflow: hidden }`; `.chat-layout__main { min-height: 0; overflow: hidden }`. Touches: `frontend/src/index.css`
4. [x] **Composer width fix** — `.composer` becomes a block; textarea + Send move into `<div className="composer__row">` styled `display: flex; align-items: flex-end; gap: 10px; max-width: 760px; margin: 0 auto`. Touches: `frontend/src/components/Composer/Composer.tsx`, `frontend/src/index.css`
5. [x] **`chatApi.deleteChat`** — `DELETE /api/chats/{id}`, resolves on 204, same error contract as the other verbs. Touches: `frontend/src/services/chatApi.ts`
6. [x] **`useConversations.deleteConversation`** — call the API; on success remove from the list and clear `activeId` if active; return success/failure. Touches: `frontend/src/hooks/useConversations.ts`
7. [x] **`ConversationItem` affordances** — hover-revealed pencil (inline title editor: Enter/blur save, Escape cancel, blank cancels) and × (calls `onDelete`). New optional props `onRename`, `onDelete`. Touches: `frontend/src/components/Sidebar/ConversationItem.tsx`, `frontend/src/index.css`
8. [x] **`Sidebar` / `ChatPage` wiring** — `Sidebar` threads `onRename`/`onDelete` through; `ChatPage` passes `renameConversation` and a `handleDelete` (confirm → `deleteConversation`). Touches: `frontend/src/components/Sidebar/Sidebar.tsx`, `frontend/src/pages/ChatPage.tsx`
9. [x] **Frontend tests** — `chatApi.test.ts` delete cases; `useConversations.test.tsx` delete cases; new `ConversationItem.test.tsx` (rename save/cancel, delete confirm). Touches: `frontend/src/services/chatApi.test.ts`, `frontend/src/hooks/useConversations.test.tsx`, `frontend/src/components/Sidebar/ConversationItem.test.tsx`
10. [x] **Run the suites** — `npm test`, `npm run build`, `npm run lint` (frontend); `uv run pytest` (backend). Touches: none
11. [x] **Browser verification** — headless Chromium: long transcript + many chats → `bodyScrollHeight == innerHeight`, independent sidebar/transcript scroll, composer pinned, input ≈ message width, auto-scroll to bottom; delete a chat end-to-end against the live app.
12. [x] **Docs** — CLAUDE.md § Backend API surface gains `DELETE /api/chats/{id}`; 007 spec open question 1 marked resolved (pointer to 009); `implementation.md` log entry; spec status → `Tested`.

### Revision 2 — three-dot menu + custom delete modal (user review)

The first build's pencil/× controls and native `window.confirm` were rejected on review. Steps 13–17 replace them; the data contracts from steps 5–8 are unchanged.

13. [x] **`ConfirmDialog` component** — reusable controlled modal (`open`, `title`, `message`, `confirmLabel`, `cancelLabel`, `danger`, `onConfirm`, `onCancel`); portal to `document.body`; `role="dialog"` + `aria-modal`; Escape and backdrop dismiss; focus lands on Cancel (the safe action). Touches: `frontend/src/components/ConfirmDialog/ConfirmDialog.tsx` (new)
14. [x] **`ConfirmDialog` styles** — backdrop, panel, title/message, action row, primary + danger button variants. Touches: `frontend/src/index.css`
15. [x] **`ConversationItem`: three-dot menu** — replace the pencil + × with one kebab button (`aria-haspopup="menu"`, `aria-expanded`) opening a Rename/Delete menu; closes on action, Escape, and outside click; opening never selects the chat. Touches: `frontend/src/components/Sidebar/ConversationItem.tsx`, `frontend/src/index.css`
16. [x] **`ChatPage`: pending-delete state** — `onDelete(id)` from the menu records the target chat and opens `ConfirmDialog` (replacing `window.confirm`); confirm runs `deleteConversation` and clears the transcript if it was active; cancel/Escape/backdrop change nothing. Touches: `frontend/src/pages/ChatPage.tsx`
17. [x] **Tests** — rewrite `ConversationItem.test.tsx` around the menu (open → Rename/Delete, action closes the menu, outside click closes, Escape cancels rename, blank cancels, delete calls `onDelete`); new `ConfirmDialog.test.tsx` (renders title/message, confirm/cancel callbacks, Escape cancels, backdrop cancels, closed renders nothing). Touches: `frontend/src/components/Sidebar/ConversationItem.test.tsx`, `frontend/src/components/ConfirmDialog/ConfirmDialog.test.tsx` (new)
18. [x] **Re-verify + log** — `npm test`, `npm run build`, `npm run lint`; browser check of the kebab menu and the modal end-to-end; append a revision-2 entry to `implementation.md`. Touches: `specs/features/009-chat-usability-and-management/implementation.md`

## Files to create / modify

| File | Purpose |
| ---- | ------- |
| `backend/app/services/conversation_service.py` | `delete_chat` (404 → delete, cascade via FK) |
| `backend/app/api/routes/chats.py` | `DELETE /{chat_id}` route (204) |
| `backend/tests/test_chats_crud.py` | DELETE: 204, cascade, 404 |
| `frontend/src/index.css` | grid-row fix, main-pane min-height, composer row, item actions |
| `frontend/src/components/Composer/Composer.tsx` | wrap input + Send in `.composer__row` |
| `frontend/src/services/chatApi.ts` | `deleteChat` |
| `frontend/src/hooks/useConversations.ts` | `deleteConversation` |
| `frontend/src/components/Sidebar/ConversationItem.tsx` | rename editor + delete control |
| `frontend/src/components/ConfirmDialog/ConfirmDialog.tsx` | reusable confirm modal (revision 2, new) |
| `frontend/src/components/ConfirmDialog/ConfirmDialog.test.tsx` | modal tests (revision 2, new) |
| `frontend/src/components/Sidebar/Sidebar.tsx` | thread `onRename` / `onDelete` |
| `frontend/src/pages/ChatPage.tsx` | `handleDelete` (confirm), pass handlers |
| `frontend/src/services/chatApi.test.ts` | deleteChat cases |
| `frontend/src/hooks/useConversations.test.tsx` | deleteConversation cases |
| `frontend/src/components/Sidebar/ConversationItem.test.tsx` | rename + delete flows |
| `CLAUDE.md` | API surface `DELETE` line |
| `specs/features/007-backend-api/spec.md` | resolve open question 1 |
| `specs/features/009-chat-usability-and-management/implementation.md` | build log |

## Test strategy

- **Unit (frontend):** `chatApi.deleteChat` (204 resolves, error detail throws), `deleteConversation` (success removes + clears active, failure keeps state), `ConversationItem` (rename edit → `onRename`, Escape/blank cancel; delete → `onDelete` after confirm).
- **Integration (backend):** DELETE 204 + GET 404 after, message cascade count, 404 unknown.
- **Layout (#3–#5, #6):** not unit-testable in jsdom (no layout engine) — verified with headless Chromium against the live app (scroll geometry + composer pinning + input width), and documented in `implementation.md`.
- **Regression:** golden-dataset record needed? no (no RAG behavior touched).

## Risks / dependencies

- Depends on: 008's `renameConversation` (already wired), the existing cascade FK, and both dev servers running for browser verification.
- Risks: jsdom cannot assert scrolling — layout verification must be browser-based (covered by step 11). `window.confirm` must be mocked in tests (`vi.spyOn(window, 'confirm')`).

## Definition of Done for this plan

- [x] All steps ticked
- [x] Spec acceptance criteria ticked in `spec.md`
- [x] `implementation.md` log written for the build session(s)
- [x] Status in `spec.md` moved to `Tested` (then `Accepted` after review)
