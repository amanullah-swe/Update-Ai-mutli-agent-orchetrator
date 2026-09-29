# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

- **Specification-first project.** As of 2026-09-27 this repository contains only this document plus a backup of the original spec (`CLAUDE.md.spec-backup-2026-09-27.md`). No implementation code exists yet: no `frontend/`, `backend/`, `rag/`, `ai_agent/`, no Makefile, no README, no git history.
- The sections below are the authoritative product requirements for a **Modular AI Agent + RAG Learning Platform** — a system whose primary purpose is to learn, implement, compare, evaluate, and test different RAG strategies. They were condensed from the original spec, which is preserved verbatim in the backup file; if this doc and the backup ever disagree, the backup is the source of truth for requirements.
- Until code exists there are no runnable commands. The Commands section is an honest placeholder to be completed as scaffolding lands.
- The **Core Architectural Rule** (below) is the single most important requirement in this project and overrides everything else.

## Core Architectural Rule (highest priority)

> **Every RAG strategy must be implemented as a replaceable component behind a common interface. The core pipeline must depend on interfaces, not concrete implementations. Strategy selection must happen through configuration.**

Consequences that always apply:

- The RAG pipeline must never contain `if <strategy>:` dispatch chains or import concrete implementations directly. No `recursive_chunking(...)` hard-wired into pipeline code.
- Swapping strategies means editing a config value — nothing else. Changing `chunking.strategy: recursive` to `semantic` must be sufficient to run the identical pipeline with another strategy.
- Every swappable component exposes one of the common interfaces (see Common Interfaces). Each interface has multiple implementations; implementations are selected by name at startup from configuration.
- Keep components independent, config-driven, interface-based, observable, and named clearly. Do not build one large service containing all strategies.

## Build decisions (open questions — resolve, then record here)

These decisions are NOT yet made because no code exists. Resolve each one during scaffolding and record the decision in this section so the whole project stays consistent. Recommended defaults are marked (→).

1. **Strategy → class binding** — how config `chunking.strategy: semantic` resolves to `SemanticChunker`. → Use a per-component-type registry with a `@register("semantic")` class decorator and a `build_component(kind, name)` factory that raises a loud error listing known strategies. Avoid `importlib`-by-convention and avoid dispatch listings in the pipeline.
2. **Python tooling** — ✅ RESOLVED (ADR-002): `uv` + `pyproject.toml` with a committed `uv.lock`; Python `>=3.13`. Original `requirements.txt` note superseded.
3. **Config loading** — ✅ RESOLVED (ADR-003): `pydantic-settings` `Settings` + `configs/<env>.yaml` (YAML is the low-priority source; `RAG_*` env + `.env` override). Components get a typed `Settings` via dependency injection; nothing reads YAML or env directly.
4. **Framework dependence** — the folder layout (format-specific loaders/parsers/cleaners) implies hand-written implementations behind custom interfaces. → Keep custom interfaces and add thin adapters to third-party libraries (LangChain, LlamaIndex, RAGAS, etc.), so swappability never depends on a framework.
5. **Frontend tooling** — → Vite + React + TypeScript, chat messaging over a WebSocket client for `/api/chats/{id}/ws` (ADR-011 superseded the SSE `/api/chat` client — see decision #10).
6. **Sparse retrieval storage** — `rag/retrieval/sparse.py` needs a sparse index that pgvector cannot provide. → PostgreSQL FTS / `pg_search` alongside pgvector, or an in-memory BM25 index. Pick one.
7. **Filtering stage** — the pipeline stage list includes *Filtering*, but the folder layout has no `rag/filtering/` module (closest is `rag/context/deduplication.py`). → Either add a `rag/filtering/` package with an interface, or officially fold filtering into retrieval. Decide and keep the layout consistent with the pipeline stages.
8. **DB migrations** — ✅ RESOLVED (ADR-008): Alembic (`database/migrations/`) is the single source of truth; treat `database/schemas/` as reference DDL, never applied. Tests rebuild the schema via Alembic, not `create_all`.
9. **Config key vocabulary** — the spec mixes `provider` (for `llm`, `embedding`) and `strategy` (for `chunking`, `retrieval`, `reranking`). Keep both but document `strategy` as the general term; update all sample configs to match.
10. **Streaming transport** — ✅ RESOLVED (ADR-011, supersedes ADR-010): chat messaging runs over a **WebSocket** (`WS /api/chats/{chat_id}/ws`) with JSON frames — `user_message` in; `message_start → token* → sources → message_end`, plus in-band `error`, out. ADR-010's SSE choice is superseded for chat; its event vocabulary is preserved.

## Commands

Everything hangs off the root `Makefile` (run `make help` for the annotated list):

- **Full dev session:** `make dev` — ensures PostgreSQL (Docker if none is already listening on :5432, waits until ready), applies pending Alembic migrations, then backend + frontend together; Ctrl+C stops all.
- **Backend (dev):** `make backend` — `uvicorn app.main:app --reload --port 8001`. Needs the DB (`make db`) and, for real answers, `RAG_LLM_API_KEY` in `backend/.env`.
- **Frontend (dev):** `make frontend` — `npm run dev` (Vite on :5173, talks to the backend at :8001 via `frontend/.env.development`'s `VITE_API_BASE_URL`).
- **Database:** `make db` (or `up`) — `docker compose up -d db` + readiness wait; `down` stops it; `up-all` builds the containerized backend too.
- **First time on a fresh machine:** `make install-docker` (apt, needs sudo), `make db`, `make migrate`, `make seed`.
- **Migrations:** `make migrate` (upgrade) · `make migrate-make name="..."` (autogenerate). Alembic is the only DDL source.
- **Tests:** `make test` — `cd backend && uv run pytest`. Single test: `cd backend && uv run pytest tests/unit/chats/test_chat_provider_unit.py::test_name`.
- **Seed data:** `make seed` — loads `database/seed/dev.sql` into `rag_learning`.

## Architecture overview (as specified)

```
                    ┌─────────────────────┐
                    │      React UI       │
                    │   ChatGPT-like UI   │
                    └──────────┬──────────┘
                               │
                               │ HTTP / SSE
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI         │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       ┌───────────┐    ┌──────────────┐   ┌────────────┐
       │ AI Agent  │    │ RAG Pipeline │   │  Services  │
       └───────────┘    └──────────────┘   └────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ PostgreSQL          │
                    │ + pgvector          │
                    └─────────────────────┘
```

The `ai_agent/` package is deliberately separate from `rag/`. The agent may use RAG as one of its tools/capabilities (intent → tool selection → RAG tool → answer), but it must not contain RAG implementation details.

### Monorepo layout (contract to build against)

```text
rag-learning-platform/
├── frontend/          React + TypeScript chat UI (components/, pages/, hooks/, services/, types/, utils/)
├── backend/           FastAPI — modular, feature-sliced monolith: app/main.py, app/api/{deps,router}.py,
│                      app/shared/{core,database}/ (config, logging, exceptions, engine, base),
│                      app/modules/{chats,health,documents,evaluation,experiments}/ (one folder per feature:
│                      router.py, schemas.py, models.py, repository.py, provider.py, ws.py), tests/{unit,integration}/
├── ai_agent/          agent/{agent,state,planner,executor}.py, tools/, memory/, prompts/, guardrails/, tests/
├── rag/
│   ├── types/         document.py, chunk.py, retrieval.py, evaluation.py
│   ├── ingestion/     loaders/{base,pdf,docx,html,text}_loader.py, parsers/, cleaners/, pipeline.py
│   ├── chunking/      base.py + fixed_size, recursive, semantic, sentence, parent_child
│   ├── embeddings/    base.py + openai, sentence_transformer, local
│   ├── vectorstores/  base.py + pgvector
│   ├── retrieval/     base.py + dense, sparse, hybrid, metadata        (see decision #7 re: filtering)
│   ├── reranking/     base.py + cross_encoder, llm_reranker
│   ├── query/         rewriting.py, multi_query.py, hyde.py, decomposition.py
│   ├── context/       builder.py, compression.py, deduplication.py
│   ├── generation/    base.py + llm
│   ├── evaluation/    datasets/, retrieval/, generation/, end_to_end/, metrics/
│   ├── testing/       unit/, integration/, regression/, fixtures/
│   ├── monitoring/    tracing.py, metrics.py, logging.py
│   └── pipeline.py
├── database/          migrations/, schemas/, seed/
├── experiments/       configs/, results/, notebooks/
├── configs/           development.yaml, testing.yaml, production.yaml
├── specs/             spec-driven workflow — features/ (one per feature), templates/, decisions/
├── tests/             integration/, e2e/
├── docker/            Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
├── .env.example, README.md, Makefile
```

The most important architectural requirement is **swappability**. The system must allow changing, e.g.:

```python
chunker = RecursiveChunker()
# → to:
chunker = SemanticChunker()
```

without modifying the rest of the RAG pipeline — and the same for retrieval, embeddings, document loaders, evaluation methods, etc.

### RAG pipeline stages

```text
Document → Loading → Parsing → Cleaning → Chunking → Embedding → Vector Storage
→ Query → Query Transformation → Retrieval → Filtering → Reranking
→ Context Construction → LLM → Response → Evaluation
```

Every stage must be independently testable.

## Common interfaces

Every swappable component implements exactly one of:

```text
DocumentLoader   DocumentParser   DocumentCleaner   Chunker
EmbeddingModel   VectorStore      Retriever         Reranker
QueryTransformer ContextBuilder   Generator         Evaluator
```

Indexing a new variant means: implement the interface in a new file, register it, and reference it by name in config — the pipeline code itself is untouched. This is what enables experiments like *Recursive+Dense*, *Semantic+Dense*, *Semantic+Hybrid*, *Semantic+Hybrid+CrossEncoder* without changing application code.

## Backend API surface (current — 007 chat CRUD + WebSocket + 009 delete)

```text
POST   /api/chats                 create a chat
GET    /api/chats                 list chats (most recent activity first)
GET    /api/chats/{id}            get a chat + its transcript
PATCH  /api/chats/{id}            rename a chat
DELETE /api/chats/{id}            delete a chat (messages cascade) — 009
WS     /api/chats/{id}/ws         send/receive messages (JSON frames)
GET    /api/health                liveness + database reachability
```

Document upload, evaluation runs, and experiment runs were de-scoped from the initial
build (feature 007 rescope) and return to the backlog as their own features when the RAG
pipeline exists to produce real data. Chat messaging is the working transport, carried by
WebSockets (decision #10 → ADR-011).

Assistant replies come from the `ChatProvider` seam (feature 010): `chat.provider: mock`
(the canned test reply) or `openrouter` (a real LLM call, history-aware — prior turns are
fetched from PostgreSQL and sent to OpenRouter). Missing `RAG_LLM_API_KEY` surfaces as an
in-band `validation_error` frame; upstream failures as `llm_error`.

## Configuration model

All strategy selection happens through configuration, read at startup, never at component level. Example shape:

```yaml
llm:
  provider: openrouter        # consumed by the chat provider (010): llm.model + RAG_LLM_API_KEY
  model: deepseek/deepseek-v4-flash-0731
  api_key: ""                 # real key ONLY via env RAG_LLM_API_KEY (backend/.env)
embedding:
  provider: openrouter
  model: sentence-transformers/all-minilm-l6-v2
chunking:
  strategy: recursive
retrieval:
  strategy: hybrid
reranking:
  strategy: cross_encoder
query_transformation:
  strategy: none
evaluation:
  strategy: ragas
```

**Provider conventions:** All model traffic goes through **OpenRouter** — set `llm.provider: openrouter` and `embedding.provider: openrouter`, using OpenRouter model IDs (vendor-prefixed, e.g. `deepseek/deepseek-v4-flash-0731` for the LLM and `sentence-transformers/all-minilm-l6-v2` for embeddings, 384-dim).

**What is live today (feature 010):** `llm.provider`/`llm.model`/`llm.api_key` are wired into the
backend's `Settings` (ADR-003) and consumed by the chat provider seam. The *seam selector* is
`chat.provider` (`mock` | `openrouter`); `llm.provider` stays reserved for the future RAG
generator. `embedding:`/`chunking:`/`retrieval:`/`reranking:`/`query_transformation:`/`evaluation:`
remain inert until their pipeline features land. `configs/*.yaml` genuinely load (the Settings
`REPO_ROOT` resolves to the repo root); `RAG_*` env and `.env` still override YAML.

## Database (PostgreSQL + pgvector)

Entities to model: `documents`, `document_versions`, `chunks`, `embeddings`, `conversations`, `messages`, `evaluation_datasets`, `evaluation_results`, `experiments`, `experiment_runs`. Store enough metadata to trace any RAG answer back to its source document and chunk.

## Evaluation (first-class component)

- **Retrieval:** Recall@K, Precision@K, context relevance, context precision, context recall.
- **Generation:** faithfulness, answer relevance, correctness, hallucination detection.
- **End-to-end:** answer quality, citation correctness, latency, token usage, cost, error rate.

Evaluators must be pluggable without changing the RAG pipeline. (See decision #4 — RAGAS as an adapter.)

## Testing requirements

- **Unit:** each chunker, retriever, embedding model, reranker, query transformer, context builder.
- **Integration:** e.g. Retriever + PGVector, Embedding + PGVector, RAG Pipeline + LLM.
- **Regression:** maintain a golden dataset (`question`, `expected_answer`, `expected_documents`, `expected_evidence`, `metadata`). Rerunnable after any change to chunking, embeddings, retrieval, reranking, prompts, LLM, or data — to compare results.

## Experiment framework

An experiments runner executes config combinations, e.g. `chunking: [recursive, semantic]` × `retrieval: [dense]` × `reranking: [none, cross_encoder]`, and stores per run: configuration, metrics, latency, cost, retrieval results, generated answers, evaluation results, timestamp.

## Observability

Every RAG request must be traceable end-to-end through: request_id, query, retrieval strategy, embedding model, chunking strategy, retrieved chunks, retrieval scores, reranking scores, prompt/model version, LLM response, latency, token usage, errors. When an answer is wrong, it must be possible to identify which stage caused the problem.

## Frontend (minimal chat UI)

User/assistant message list, input box + send, streaming responses, markdown + code block rendering, loading/error states, new-conversation, and source/citation display. Keep it simple; do not overspend on visual customization.

## Spec-driven feature workflow

We build this project **feature by feature, spec first**. Behavior is specified before code is written, then planned, then implemented and logged. Each feature folder stores three documents so any change can be back-tracked:

- **`spec.md`** — *what* we're building (interfaces, behavior, acceptance criteria). The feature's `Status:` lives here.
- **`plan.md`** — *how* we'll build it (ordered steps, files, test strategy), written once the spec is `Specified`.
- **`implementation.md`** — *what actually happened* (append-only, dated log: files touched, deviations, test results, decisions). Never rewrite this file — add entries. This is the back-tracking trail.

- **Specs live in `specs/features/<NNN>-<slug>/`** with those three files. Templates live in `specs/templates/`; see `specs/README.md`.
- **Feature lifecycle:** `Draft → Specified → Planned → Implemented → Tested → Accepted`, tracked in the spec's `Status:` line. A feature ships only when its acceptance checklist is fully ticked and `plan.md`'s steps are done.
- **No code before `Planned`.** Spec must be `Specified` (`spec.md`) and `Planned` (`plan.md`) before behavior is implemented. Scaffolding folders is fine.
- **Spec-first on change:** behavior changes touch the spec first, then the plan, then the code.
- **One feature per working unit:** implement, test, and commit a single feature (or a coherent slice) at a time. Each must satisfy the Core Architectural Rule and this layout's contract.
- **Decisions:** resolving an open item in "Build decisions" produces an ADR under `specs/decisions/` and updates the item here.
- **Definition of Done:** a feature is Done when Implemented, Tested (unit + relevant integration/regression), logged in `implementation.md`, and Accepted against its acceptance criteria.

## Definition of Done (acceptance checklist for the initial build)

- React frontend runs; FastAPI backend runs; PostgreSQL + pgvector connected.
- Document upload and ingestion work.
- At least two chunking strategies and two retrieval strategies selectable; embedding strategy changeable via config; reranking toggleable via config.
- RAG pipeline executes end-to-end; chatbot answers from RAG with streamed responses.
- Evaluation runs against a dataset; unit/integration/regression tests exist.
- Experiments compare different configurations.
- Changing a strategy does **not** require modifying the core RAG pipeline.
- README explains how to add a new strategy.