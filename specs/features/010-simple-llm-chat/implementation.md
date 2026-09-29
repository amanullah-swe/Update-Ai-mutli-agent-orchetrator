# Implementation Log — 010: Simple LLM chat (real, history-aware OpenRouter provider)

- **Status:** `Tested`
- **Spec:** `./spec.md`
- **Plan:** `./plan.md`

> **Append-only.** Each build session adds a dated entry and never edits older ones. This is the back-tracking record: it shows what was done, what changed, and why. Newest entry goes at the bottom.

## Log

---

### 2026-09-29 — Initial build: real, history-aware OpenRouter chat provider

**Session scope:** the full feature 010 (config layer, provider, repository helper, WebSocket threading, tests, docs).

**What was done**

- **Config:** fixed `Settings.REPO_ROOT` (`parents[3]` → `parents[4]`) — the `configs/*.yaml` layer was silently inert (it looked under `backend/configs/`); added `llm_provider`/`llm_model`/`llm_api_key` fields + three `_YAML_ALIASES` rows. `configs/{development,testing,production}.yaml` gained `llm:` sections; dev + prod flipped `chat.provider` to `openrouter`, testing stays `mock`. `backend/.env.example` documents `RAG_CHAT_PROVIDER=openrouter`, `RAG_LLM_MODEL`, `RAG_LLM_API_KEY`.
- **Dependencies:** moved `httpx` from the dev group to runtime `dependencies`; `uv.lock` regenerated.
- **Exceptions:** added `LLMProviderError` (502, `code="llm_error"`).
- **Provider** (`app/modules/chats/provider.py`): widened `ChatProvider`/`MockChatProvider.stream` with a `history: Sequence[MessageOut] | None = None` keyword (mock ignores it); added `LLM_SYSTEM_PROMPT`, `_build_messages` (system + alternating turns, skips `error=True` rows, coalesces same-role adjacents, current question last), `OpenRouterChatProvider` (httpx `Client.stream` → SSE per-line parse with content-guard, `SourcesEvent(())` at end, non-2xx/transport → `LLMProviderError`), and `build_chat_provider` branches `mock`|`openrouter` (missing key → `ValidationError` naming `RAG_LLM_API_KEY`; unknown names list both).
- **Repository:** added `get_chat_history(db, conversation_id, limit=None)` — oldest→newest `MessageOut` rows (`created_at`, `id` tiebreak), pure read.
- **Socket** (`app/modules/chats/ws.py`): history is loaded **before** the current user message is persisted (so the LLM sees prior turns only); the provider is built per turn (config errors surface in-band); the sync generator streams through a thread bridge (`run_in_executor(None, _next_provider_event, iterator)` with a sentinel instead of `StopIteration`, `close()` in `finally`); three exception tiers → `validation_error` (config) / `llm_error` / `internal_error` frames, socket stays open.
- **Tests:** new `tests/unit/config/test_config_yaml.py` (YAML-loads regression + llm fields + env override), `tests/unit/chats/test_openrouter_provider_unit.py` (`httpx.MockTransport` canned SSE, history mapping, auth header, 429/ConnectError, per-delta delay, empty stream), extended `test_chat_provider_unit.py` (openrouter selection, missing key, unknown-name listing, mock accepts history), new `tests/integration/chats/test_chat_history.py` (history ordering incl. `error=True` row; WS turn fed by a fake recording provider proving prior turns reach the provider).
- **Docs:** CLAUDE.md § Configuration model + § Backend API surface updated; ADR-012 written.

**Deviations from plan & why**

- `OpenRouterChatProvider.stream` breaks (not returns) on `data: [DONE]` so the trailing `SourcesEvent(())` always emits — the WS contract needs `sources` before `message_end`.
- The thread bridge uses a sentinel wrapper (`_next_provider_event`) instead of bare `next` + `except StopIteration`: Python ≥3.14 raises `RuntimeError: StopIteration interacts badly with generators…` when `StopIteration` crosses the `run_in_executor` Future boundary — discovered live (first bridge attempt hung the WS integration suite).

**Tests run / results**

- `uv run pytest` — **42 passed** (26 pre-existing stayed green + 16 new; no real network anywhere; integration suite runs against real PostgreSQL `rag_learning_test` rebuilt via Alembic).
- Manual WS smoke (dev env, `chat.provider: openrouter`, no key): turn returns `message → message_start → error(validation_error)` naming the key, socket stays open for the next turn.

**Decisions made** (link ADR if one was written)

- ADR-012 (`specs/decisions/012-llm-chat-provider.md`) — history-aware provider, OpenRouter via httpx, config plumbing, thread bridge, REPO_ROOT fix.
- Seam selector stays `chat.provider`; `llm.provider` reserved for the future RAG generator.

**Progress**

- Plan steps: all ticked.
- Acceptance criteria now true (`spec.md`): all ticked — feature `Tested`.