# Plan — 010: Simple LLM chat (real, history-aware OpenRouter provider)

- **Status:** `Complete`
- **Last updated:** 2026-09-29
- **Spec:** `./spec.md`

> Written **after** the spec is `Specified` and **before** any code.

## Approach (one line)

Widen the existing `ChatProvider` seam with a `history` argument and add an `OpenRouterChatProvider` (config-selected by `chat.provider`, `httpx` SSE streaming) that each WS turn feeds the persisted transcript into; fix the `REPO_ROOT`/YAML-loading defect so `llm.*` config is real, and bridge the sync provider stream through a thread so the event loop never blocks.

## Steps (do these in order)

1. [x] **Spec docs** — `spec.md` `Specified`, `implementation.md` scaffold. Touches: `specs/features/010-simple-llm-chat/{spec,implementation}.md`
2. [x] **Config layer** — fix `REPO_ROOT` to `parents[4]` + stale comment; add `llm_provider`/`llm_model`/`llm_api_key` fields + 3 `_YAML_ALIASES` rows. Touches: `backend/app/shared/core/config.py`
3. [x] **Config files** — `llm:` sections in `configs/{development,testing,production}.yaml`; dev+prod flip `chat.provider` to `openrouter`, testing stays `mock`. Touches: `configs/*.yaml`
4. [x] **Env example** — `RAG_CHAT_PROVIDER=openrouter`, `RAG_LLM_MODEL`, `RAG_LLM_API_KEY=` placeholder. Touches: `backend/.env.example`
5. [x] **Dependencies** — move `httpx` to runtime `dependencies`; run `uv lock`, `uv sync`. Touches: `backend/pyproject.toml`, `backend/uv.lock`
6. [x] **Exception** — add `LLMProviderError(AppError)` (502, `code="llm_error"`). Touches: `backend/app/shared/core/exceptions.py`
7. [x] **Verify mid-point** — existing suite still green once YAML loads for real. Touches: run `uv run pytest`
8. [x] **Provider** — widen `ChatProvider`/`MockChatProvider.stream` with `history` kwarg; add `LLM_SYSTEM_PROMPT`, `_build_messages`, `OpenRouterChatProvider` (httpx SSE client, content-guard filtering, `SourcesEvent(())` at end); extend `build_chat_provider` (`mock`|`openrouter`, missing key → `ValidationError` naming `RAG_LLM_API_KEY`, unknown names list both). Touches: `backend/app/modules/chats/provider.py`
9. [x] **Repository** — add `get_chat_history(db, conversation_id, limit=None) -> list[MessageOut]` (oldest→newest, `Message.id` tiebreak). Touches: `backend/app/modules/chats/repository.py`
10. [x] **Socket** — load history before persisting the user message; build provider inside the turn try; stream events via `_stream_events` thread bridge (`run_in_executor(None, _next_provider_event, iterator)` sentinel bridge + `close()` in finally); three-tier exception → error-frame mapping. Touches: `backend/app/modules/chats/ws.py`
11. [x] **Unit tests** — `test_config_yaml.py` (YAML-loads regression + llm fields), `test_openrouter_provider_unit.py` (`httpx.MockTransport` canned SSE, history mapping, auth header, 429/ConnectError mapping), extend `test_chat_provider_unit.py` (openrouter selection, missing key, mock accepts history). Touches: `backend/tests/unit/{config,chats}/`
12. [x] **Integration tests** — `test_chat_history.py`: repository helper ordering (incl. an `error=True` row) + WS turn with a fake recording provider proving history reaches the stream call (no network). Touches: `backend/tests/integration/chats/test_chat_history.py`
13. [x] **Full suite** — `uv run pytest` green. Touches: run tests
14. [x] **Docs + close** — CLAUDE.md § Configuration model/API surface; ADR-012; `implementation.md` entry; spec status → `Tested`. Touches: `CLAUDE.md`, `specs/decisions/012-llm-chat-provider.md`, `implementation.md`, `spec.md`

## Files to create / modify

| File | Purpose |
| ---- | ------- |
| `specs/features/010-simple-llm-chat/{spec,plan,implementation}.md` | spec-driven workflow docs |
| `backend/app/shared/core/config.py` | fix `REPO_ROOT`; `llm_*` fields + YAML aliases |
| `backend/app/shared/core/exceptions.py` | `LLMProviderError` (502, `llm_error`) |
| `backend/app/modules/chats/provider.py` | history kwarg; `_build_messages`; `OpenRouterChatProvider`; builder |
| `backend/app/modules/chats/repository.py` | `get_chat_history` |
| `backend/app/modules/chats/ws.py` | history load; thread-bridged streaming; error tiers |
| `configs/{development,testing,production}.yaml` | `llm:` section; provider flips |
| `backend/.env.example` | `RAG_LLM_*` + provider |
| `backend/pyproject.toml` + `backend/uv.lock` | httpx → runtime deps |
| `backend/tests/unit/config/test_config_yaml.py` | **new** — YAML-loads regression |
| `backend/tests/unit/chats/test_openrouter_provider_unit.py` | **new** — SSE parsing, history, errors |
| `backend/tests/unit/chats/test_chat_provider_unit.py` | extend — selection/keyest/mock-history |
| `backend/tests/integration/chats/test_chat_history.py` | **new** — history helper + WS fake-provider turn |
| `CLAUDE.md` | § Configuration model; provider note |
| `specs/decisions/012-llm-chat-provider.md` | **new** — decision record |

## Test strategy

- **Unit:** OpenRouter SSE parsing against `httpx.MockTransport` canned chunks (role-only, content, `: ping`, `[DONE]`) → tokens then one empty `SourcesEvent`; request capture asserts message list (system + alternating turns + current last, error rows skipped), `Authorization: Bearer …`, `model`, `stream: true`; 429/ConnectError → `LLMProviderError`; builder selection + missing-key + unknown-name; mock accepts `history`; `test_config_yaml.py` proves `configs/testing.yaml` loads (`environment`, `chat_provider`, `llm_model`).
- **Integration:** real PostgreSQL — repository `get_chat_history` ordering incl. an `error` row; WS turn with `build_chat_provider` monkeypatched to a recording fake: turn 2's recorded `history == [turn1-user, turn1-assistant]` exactly (no network, mock still the config default).
- **Regression:** golden-dataset record needed? **No** — no RAG data exists yet (matches 007/009 practice).

## Risks / dependencies

- Depends on: `007-backend-api` (transport + persistence), OpenRouter API (live smoke needs a key — tests need none).
- Risks: SSE shape variations (role-only/usage/comment chunks — content-guard filters all); `Client.stream()` does not raise on non-2xx (explicit status check); `uv.lock` regen must not be skipped; REPO_ROOT fix changes all environments (verify boot + tests right after step 7).
- Gotcha: pydantic-name collision in `ws.py` — import the app `ValidationError` aliased `AppValidationError`.

## Definition of Done for this plan

- [x] All steps ticked
- [x] Spec acceptance criteria ticked in `spec.md`
- [x] `implementation.md` log written for the build session(s)
- [x] Status in `spec.md` moved to `Tested` (then `Accepted` after review)