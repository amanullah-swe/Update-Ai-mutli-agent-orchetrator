# 010 — Simple LLM chat: real, history-aware OpenRouter provider

- **Status:** `Tested`
- **Last updated:** 2026-09-29
- **Depends on:** `007-backend-api` (chat CRUD + WebSocket transport, persisted transcript)
- **Source:** user direction 2026-09-29 ("simple llm orchestration — simple llm call to answer the question, persistent state, able to get chat history") · CLAUDE.md § Configuration model · § Backend API surface · § Core Architectural Rule

## Problem / Motivation

The chat backend answers every question with `MockChatProvider` — a canned reply, no model involved. The core chat experience is real (routes → services → PostgreSQL → WebSocket streaming), but the *answer* is fake. This feature makes the simplest real orchestration work end to end:

> a user sends a message; a **real LLM call (OpenRouter) produces the answer**, the conversation is **persisted**, and the **chat history is retrievable** — and, crucially, is **fed into each LLM call** so the model actually follows the conversation.

It removes the last mocked piece of the core chat flow while respecting the Core Architectural Rule: the answer still comes from a `ChatProvider` selected by config — `mock` stays, `openrouter` joins it. No dispatch chains in route or pipeline code.

Two pre-existing defects block a real provider and are fixed by this feature:

1. **The YAML config layer never loads.** `backend/app/shared/core/config.py` computes `REPO_ROOT = parents[3]`, which resolves to `backend/` (the file sits four levels deep). The layer looks for `backend/configs/*.yaml`, which does not exist, so every `configs/*.yaml` value is silently dropped. Any `llm:` keys added to YAML would be inert. This is masked today because defaults + env vars cover every field. Fixed to `parents[4]`.
2. **`ws.py` iterates the provider generator inline in the async handler.** Harmless while the mock sleeps zero, but a real HTTP provider would block the event loop per token. Fixed with a thread bridge that preserves streaming.

## Scope

**In scope**

- `OpenRouterChatProvider` implementing the `ChatProvider` seam — a real `POST https://openrouter.ai/api/v1/chat/completions` with `stream: true`, SSE-parsed into the existing `TokenEvent`/`SourcesEvent` stream, selected by `chat.provider: openrouter`.
- **History-aware conversation**: each turn sends the prior transcript (oldest→newest, from `messages`) as alternating `user`/`assistant` messages behind a system prompt; the current question is the final `user` message. Backed by PostgreSQL — no new tables, no migration (the state was already persisted in 007).
- Config plumbing: `llm.provider` / `llm.model` / `llm.api_key` Settings fields + YAML aliases, `configs/{development,testing,production}.yaml` `llm:` sections, `.env.example` (`RAG_LLM_API_KEY`). The **REPO_ROOT fix** so the YAML layer genuinely loads.
- `httpx` promoted to a runtime dependency (today it is dev-only).
- Correct error behavior on the socket: missing key → in-band `validation_error` frame naming `RAG_LLM_API_KEY`; upstream HTTP/network failure → in-band `llm_error` frame; socket stays open in both cases.
- Unit tests (no network — `httpx.MockTransport`) + integration tests (real PostgreSQL, fake recording provider) + a config regression test that would have caught the REPO_ROOT bug.
- Spec docs (this file, plan, implementation log) and ADR-012; CLAUDE.md § Configuration model updated.

**Out of scope** (future features)

- RAG sources/citations — real turns send an **empty** sources list (no pipeline exists yet); the mock keeps its two fake citations.
- Frontend changes — verified the UI already renders a transcript safely with `sources: []`.
- Token/usage accounting, retries, per-model routing, multi-provider (only OpenRouter).
- Agent orchestration (planner/tools), evaluation, experiments.
- Async provider protocol / multi-client WS manager.

## Behavioral contract

### Interfaces (from Common Interfaces — CLAUDE.md)

No Common Interface is involved (chat reply, not a RAG stage). The existing **service seam** governs: `ChatProvider` (in `app/modules/chats/provider.py`), extended with an optional history argument:

```python
class ChatProvider(Protocol):
    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
    ) -> Iterator[ProviderEvent]: ...
```

- `history` carries the **prior** turns (oldest→newest; roles alternate `user`/`assistant`). The current question is *always* `user_message`, not part of `history`.
- `MockChatProvider` gets the same keyword and ignores it (all existing behavior and tests unchanged).
- Provider selection stays config-only: `chat.provider` ∈ `{mock, openrouter}`; unknown names raise `ValidationError`. No `if provider == …` in the socket or router.

OpenRouter turns emit one `TokenEvent` per content delta, then exactly one `SourcesEvent(())` (empty citations — no retrievable documents in this session).

### Data flow

1. Client sends `user_message` on `WS /api/chats/{id}/ws` (007 contract unchanged).
2. Server loads the **prior transcript** from `messages` (`get_chat_history`, oldest→newest) *before* persisting the current message — so the LLM never sees the current turn as history.
3. Server persists the user message, sends the `message` ack (unchanged).
4. `build_chat_provider(settings)` → `OpenRouterChatProvider(model=llm.model, api_key=llm.api_key)` (per turn, so a config error surfaces in-band).
5. `_build_messages(history, user_message)` → `[{system}, …alternating turns…, {user: current}]`; provider streams OpenRouter SSE chunks through the thread bridge as `token*` frames.
6. On stream end a single empty `SourcesEvent` → `sources` frame (`sources: []`); the assistant message persists with that content, then `message_end`.
7. History remains retrievable exactly as before: `GET /api/chats/{id}` returns the full transcript; the socket never replays it.

### Configuration

```yaml
# configs/development.yaml  (and testing.yaml, production.yaml — same llm: block)
chat:
  provider: openrouter     # dev + prod; testing keeps mock (deterministic CI)
llm:
  provider: openrouter     # CLAUDE.md provider convention (reserved for the future RAG generator)
  model: qwen/qwen3.8-27b:free
  api_key: ""              # real key ONLY via env: RAG_LLM_API_KEY (backend/.env)
```

```env
# backend/.env.example
RAG_CHAT_PROVIDER=openrouter
RAG_LLM_MODEL=qwen/qwen3.8-27b:free
RAG_LLM_API_KEY=            # <your OpenRouter key> — no default, never committed
```

- `llm.provider` stays reserved per CLAUDE.md's provider conventions; the *seam selector* is `chat.provider`. `build_chat_provider` inspects only `chat.provider` and passes `llm.model`/`llm.api_key` through — no behavior branches on `llm.provider`.
- Missing/empty `llm.api_key` is a **build-time config error**: `ValidationError` naming `RAG_LLM_API_KEY`. Dev fallback: `RAG_CHAT_PROVIDER=mock` in `backend/.env`.
- `RAG_*` env and `.env` still override YAML (ADR-003 priority unchanged).

### Errors

- New `LLMProviderError(AppError)` — `status_code=502`, `code="llm_error"` — for upstream HTTP failures (401/402/429/5xx with `status_code` + truncated body in `details`) and transport failures (`httpx.HTTPError` wrapped).
- On the socket, three tiers map to in-band `error` frames (socket stays open; close codes unchanged):
  - config error (missing key) → `code: "validation_error"`, message names `RAG_LLM_API_KEY`;
  - `LLMProviderError` → `code: "llm_error"`;
  - anything else → existing `code: "internal_error"`.
- HTTP side: an `LLMProviderError` leaking out of a non-WS path becomes a 502 with the standard error body shape.

### Message-history mapping (`_build_messages`)

- `[{role: "system", content: LLM_SYSTEM_PROMPT}]` (module constant — an extension point, not a setting).
- Prior turns appended in order; rows with `error=true` are skipped (failed turns never feed the model).
- Defensive coalescing: adjacent same-role messages merge (content joined with `\n`).
- Current `user_message` appended last as `{"role": "user", ...}`.

### Database contract

**Unchanged.** `conversations` + `messages` only; no migration, `alembic upgrade head` idempotent and identical to 007. Real turns persist `sources: []` (empty list, not null).

## Acceptance criteria

- [x] `chat.provider: openrouter` selects `OpenRouterChatProvider` using `llm.model` and `RAG_LLM_API_KEY`; `mock` unchanged; unknown names raise `ValidationError` listing `mock, openrouter`.
- [x] Every turn is history-aware: prior turns (oldest→newest, fetched from PostgreSQL before the current message is persisted) are sent as alternating user/assistant messages behind the system prompt; error rows skipped; the current question is the final `user` message.
- [x] Real turns stream over the existing WS frame contract (`message_start` → `token*` → `sources` `[]` → `message_end`); the event loop is never blocked by provider or DB I/O.
- [x] Missing API key → in-band `validation_error` frame naming `RAG_LLM_API_KEY` (no hang, socket stays open); upstream HTTP/network failures → in-band `llm_error` frame.
- [x] `sources: []` is persisted for real turns and the frontend renders/transforms it without error.
- [x] `REPO_ROOT` fixed; `configs/*.yaml` genuinely load; `llm.*` plumbed through `Settings` + `_YAML_ALIASES`; the three config files + `.env.example` updated; `httpx` is a runtime dependency with a regenerated `uv.lock`.
- [x] No new tables/migration; schema unchanged and `alembic upgrade head` idempotent.
- [x] Tests: full existing suite stays green (mock provider, no real network anywhere); new unit tests (SSE parsing via `httpx.MockTransport`, history mapping, auth header, selection, errors) and integration tests (real PostgreSQL; WS turn fed by a fake recording provider proving history reaches the provider) pass.
- [x] CLAUDE.md § Configuration model reflects the real provider; ADR-012 written; feature logged in `implementation.md`; status reaches `Tested`.

## Open questions

- [ ] **Zero-content turns:** if OpenRouter returns no content (empty answer), the assistant message persists as an empty string. Acceptable for now; revisit with evaluation.
- [ ] **System prompt as config:** the system prompt is a module constant. Promote to `llm.system_prompt` config if tuning it becomes routine.
- [ ] **Provider name vs. `llm.provider`:** for now `chat.provider` alone selects the WS answering engine; `llm.provider` is reserved. If a future RAG generator needs its own provider selection, reconcile the two keys then.

## Notes / links

- Defect fixes are part of this feature because a real provider is blocked by both: the YAML layer must load (`llm:` keys), and the socket must not block on network I/O.
- **ADR-012** (`specs/decisions/012-llm-chat-provider.md`) records the provider/history/config/thread-bridge decisions.
- OpenRouter verified contract: `POST https://openrouter.ai/api/v1/chat/completions`, `Authorization: Bearer <key>`, SSE chunks normalized to OpenAI shape (`choices[0].delta.content`), stream ends `data: [DONE]`; role-only/usage/comment chunks carry no content and are skipped; non-2xx returns an ErrorResponse body.