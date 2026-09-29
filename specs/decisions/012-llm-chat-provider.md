# ADR-012 — Chat answers: real OpenRouter provider, history-aware

- **Status:** Accepted
- **Date:** 2026-09-29
- **Related:** spec 010-simple-llm-chat · ADR-003 (config) · ADR-011 (WebSocket transport) · CLAUDE.md § Configuration model / § Core Architectural Rule

## Context

The chat backend answered every question with `MockChatProvider`. The user wanted the
simplest real orchestration — a real LLM call answers the question, conversation state
persists, and chat history is retrievable. Two facts shaped the design:

- **State already exists.** `conversations` + `messages` (PostgreSQL, 007) persist the
  transcript; `GET /api/chats/{id}` retrieves it. The missing piece was feeding that
  history into each LLM call.
- **Two defects blocked a real provider.** `Settings.REPO_ROOT` resolved to `backend/`
  (not the repo root), so the `configs/*.yaml` layer never loaded — any `llm:` config
  would be inert. And the WS handler iterated the sync provider generator inline in the
  async handler, which would block the event loop on network I/O.

Options for the answering engine: (a) real OpenRouter HTTP call behind the existing
`ChatProvider` seam; (b) a framework SDK (OpenAI/Anthropic client); (c) keep mock only.
OpenRouter was already the project's stated provider convention (CLAUDE.md), and `httpx`
(already a dev dependency) gives a plain, dependency-light streaming client — no vendor SDK.

## Decision

1. **`ChatProvider.stream` gains a `history` keyword** (prior turns, oldest→newest; the
   current question stays the `user_message` argument). `MockChatProvider` accepts and
   ignores it — no behavior change for the mock or existing tests.
2. **`OpenRouterChatProvider`** joins the seam: `httpx.Client.stream("POST",
   /api/v1/chat/completions)` with `stream: true`, SSE parsed per line into `TokenEvent`s
   (`choices[0].delta.content`), then one empty `SourcesEvent(())` (no RAG yet). Non-2xx
   and transport failures raise the new `LLMProviderError` (502, `code="llm_error"`).
3. **Selection stays `chat.provider`** (`mock` | `openrouter`); `llm.model` and
   `llm.api_key` configure the OpenRouter knobs. `llm.provider` remains reserved for the
   future RAG generator and is never branched on. Missing key is a build-time
   `ValidationError` naming `RAG_LLM_API_KEY`.
4. **History is loaded before the current message is persisted** each turn, so the model
   sees turns up to (not including) the current one, behind a fixed system prompt
   (module constant), skipping `error=True` rows.
5. **The socket never blocks the loop:** the sync provider generator is iterated via
   `run_in_executor` (`StopIteration` converted to a sentinel — Python ≥3.14 forbids it
   crossing the Future boundary), forwarding events one-by-one; `close()` in `finally`
   releases the upstream connection on mid-turn abort.
6. **Fix the config layer:** `REPO_ROOT` → `parents[4]` so `configs/*.yaml` genuinely
   load; `llm.provider`/`llm.model`/`llm.api_key` are real `Settings` fields with YAML
   aliases, env-overridable (`RAG_LLM_*`).

## Consequences

- **Real answers without RAG:** dev and prod default to `chat.provider: openrouter`;
  without a key a turn returns an in-band `validation_error` frame (no hang) and the
  fallback is `RAG_CHAT_PROVIDER=mock` in `backend/.env`. Tests stay deterministic
  (`testing.yaml` keeps `mock`; the OpenRouter provider is unit-tested via
  `httpx.MockTransport` — no real network anywhere in the suite).
- **History-aware by contract:** any future provider must accept `history`; the socket
  owns the threading, providers stay plain sync generators.
- **Empty citations for now:** real turns persist `sources: []`; the frontend already
  renders that safely. RAG sources will fill this when the pipeline lands — no contract
  change needed (the `Source`/`SourcesFrame` shape is unchanged).
- **`httpx` is now a runtime dependency** (was dev-only); `uv.lock` regenerated.
- **Config is real:** `configs/*.yaml` now load in every environment (dev gains
  `token_delay_ms: 25`, prod `debug: false` — matching the files' intent). Everything
  else that used to rely on the silent YAML no-op keeps working because env vars and
  defaults covered those fields.
- **Follow-ups:** system prompt is a constant (promote to `llm.system_prompt` if tuning);
  worker-pool starvation under many concurrent streams is a theoretical risk to revisit
  when RAG arrives; `llm.provider` vs `chat.provider` reconciliation when the RAG
  generator needs its own selection.
