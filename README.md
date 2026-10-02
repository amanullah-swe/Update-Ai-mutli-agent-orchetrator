# rag-learning-platform

**A Modular AI Agent + RAG Learning Platform** — a system built to learn, implement, compare, evaluate, and test different RAG strategies.

The project's primary purpose is *experimentation*: every RAG strategy (chunking, retrieval, reranking, embeddings, evaluation) is a **replaceable component** behind a common interface, selected purely by configuration. Swapping `chunking.strategy: recursive` → `semantic` must run the identical pipeline with a different strategy — no code changes.

> **Status: specification-first.** This repository currently contains only the product specification (`CLAUDE.md`) and this README. No implementation code exists yet — the layout below is the contract to build against. See [Roadmap](#roadmap).

---

## Table of contents

- [The Core Idea](#the-core-idea)
- [Functional Requirements](#functional-requirements)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [RAG Pipeline Stages](#rag-pipeline-stages)
- [Common Interfaces](#common-interfaces)
- [Configuration Model](#configuration-model)
- [Backend API Surface](#backend-api-surface)
- [Evaluation & Experiments](#evaluation--experiments)
- [Getting Started](#getting-started)
- [Adding a New Strategy](#adding-a-new-strategy)
- [Roadmap](#roadmap)

---

## The Core Idea

> **Every RAG strategy must be implemented as a replaceable component behind a common interface. The core pipeline must depend on interfaces, not concrete implementations. Strategy selection must happen through configuration.**

This single rule overrides everything else in the project. Concretely:

- **No dispatch chains.** The RAG pipeline never contains `if <strategy>:` blocks and never imports a concrete implementation directly. No `recursive_chunking(...)` hard-wired into pipeline code.
- **Swapping = editing config.** Changing `chunking.strategy: recursive` to `semantic` must be sufficient to run the identical pipeline with another strategy.
- **One interface, many implementations.** Every swappable component implements exactly one of the [common interfaces](#common-interfaces), and implementations are selected by name at startup from configuration.
- **Independent, config-driven, observable components.** No single large service containing all strategies.

This is what makes experiments like *Recursive+Dense*, *Semantic+Dense*, *Semantic+Hybrid*, or *Semantic+Hybrid+CrossEncoder* possible without touching application code.

## Functional Requirements

- **Chat UI** — ChatGPT-like interface (React) with streaming, markdown rendering, and source/citation display.
- **Document ingestion** — upload, parse, clean, and chunk documents (PDF, DOCX, HTML, TXT).
- **RAG pipeline** — chunk → embed → store → retrieve (dense/sparse/hybrid) → rerank → build context → generate.
- **Swappable strategies** — at least two chunkers and two retrievers from day one; embedding and reranking toggled via config.
- **First-class evaluation** — retrieval, generation, and end-to-end metrics, plus a rerunnable **regression (golden) dataset**.
- **Experiment framework** — run config combinations (e.g. `chunking: [recursive, semantic]` × `retrieval: [dense]` × `reranking: [none, cross_encoder]`) and store per-run metrics, latency, cost, and answers.
- **End-to-end observability** — every request traceable by `request_id` through every pipeline stage.
- **AI Agent** — a separate `ai_agent/` package that may use RAG as one of its tools, but contains no RAG implementation details.

## Architecture

```
                    ┌─────────────────────┐
                    │      React UI       │
                    │   ChatGPT-like UI   │
                    └──────────┬──────────┘
                               │
                               │ HTTP + WebSocket
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

## Repository Layout

```
rag-learning-platform/
├── frontend/          React + TypeScript chat UI (components/, pages/, hooks/, services/, types/, utils/)
├── backend/           FastAPI — app/api/{routes,core,models,schemas,services}.py, app/main.py, tests/
│                      routes: chats (HTTP CRUD + WebSocket), health
├── ai_agent/          agent/{agent,state,planner,executor}.py, tools/, memory/, prompts/, guardrails/, tests/
├── rag/
│   ├── types/         document.py, chunk.py, retrieval.py, evaluation.py
│   ├── ingestion/     loaders/{base,pdf,docx,html,text}_loader.py, parsers/, cleaners/, pipeline.py
│   ├── chunking/      base.py + fixed_size, recursive, semantic, sentence, parent_child
│   ├── embeddings/    base.py + openai, sentence_transformer, local
│   ├── vectorstores/  base.py + pgvector
│   ├── retrieval/     base.py + dense, sparse, hybrid, metadata        (see decision #7 for filtering)
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
├── tests/             integration/, e2e/
├── docker/            Dockerfile.backend, Dockerfile.frontend, docker-compose.yml
├── .env.example, README.md, Makefile
```

## RAG Pipeline Stages

```text
Document → Loading → Parsing → Cleaning → Chunking → Embedding → Vector Storage
→ Query → Query Transformation → Retrieval → Filtering → Reranking
→ Context Construction → LLM → Response → Evaluation
```

Every stage is independently testable.

## Common Interfaces

Every swappable component implements exactly **one** of these interfaces:

```text
DocumentLoader   DocumentParser   DocumentCleaner   Chunker
EmbeddingModel   VectorStore      Retriever         Reranker
QueryTransformer ContextBuilder   Generator         Evaluator
```

Indexing a new variant means: implement the interface in a new file, **register it**, and reference it by name in config — the pipeline code itself is untouched.

## Configuration Model

All strategy selection happens through configuration, read at startup, never at component level. Example shape:

```yaml
llm:
  provider: openrouter
  model: qwen/qwen3.8-27b:free
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

## Backend API Surface (current — chat CRUD + WebSocket)

Document upload, evaluation, and experiment endpoints were de-scoped from the initial
build (feature 007 rescope) and return to the backlog with the RAG pipeline. The working
surface is the chat app:

```text
POST   /api/chats                 create a chat
GET    /api/chats                 list chats (most recent activity first)
GET    /api/chats/{id}            get a chat + its transcript
PATCH  /api/chats/{id}            rename a chat
WS     /api/chats/{id}/ws         send/receive messages (JSON frames)
GET    /api/health                liveness + database reachability
```

## Evaluation & Experiments

**Evaluation is a first-class component.** Evaluators are pluggable without changing the RAG pipeline (e.g. RAGAS behind an adapter).

- **Retrieval:** Recall@K, Precision@K, context relevance, context precision, context recall.
- **Generation:** faithfulness, answer relevance, correctness, hallucination detection.
- **End-to-end:** answer quality, citation correctness, latency, token usage, cost, error rate.

**Regression testing** maintains a golden dataset (`question`, `expected_answer`, `expected_documents`, `expected_evidence`, `metadata`), rerunnable after any change — to chunking, embeddings, retrieval, reranking, prompts, LLM, or data — to compare results.

**Experiments** runner executes config combinations and stores per run: configuration, metrics, latency, cost, retrieval results, generated answers, evaluation results, timestamp.

## Getting Started

Partially built: the **backend API (FastAPI + PostgreSQL)** and the **frontend chat UI** both run today; the RAG pipeline / AI agent / LLM integration are future features, so the assistant's reply is a deterministic **mock** streamed over a WebSocket (`chat.provider: mock`).

```sh
# 1. database — Docker, or a local PostgreSQL instance
make up                 # docker compose: postgres on :5432 (role rag / pass rag)

# 2. backend
cp backend/.env.example backend/.env   # optional overrides
make migrate            # apply Alembic migrations (source of truth for the schema)
make backend            # uvicorn on :8001 (http://localhost:8001/docs)

# 3. frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

- **Backend (dev):** `make backend`.  **Tests:** `cd backend && uv run pytest`.
- Chat returns mock data by design (`chat.provider: mock` in `configs/development.yaml`) — swap in a real provider without touching routes.
- See `backend/README.md` for the full API surface and mock-chat contract.

See the [Roadmap](#roadmap) for what's next.

## Adding a New Strategy

*Planned.* Once the interface + registry foundation lands, adding a strategy will mean:

1. Implement the relevant interface (e.g. `Chunker`) in a new file under the component's package.
2. Register it with the decorator: `@register("my_strategy")`.
3. Reference it in config: `chunking.strategy: my_strategy`.

The core pipeline code is not touched. A canonical worked example will be documented in this README once the foundation exists.

## Roadmap

1. **Foundation** — resolve the 10 open build decisions (registered in `CLAUDE.md`), scaffold the monorepo, tooling (`uv` + `pyproject.toml`), config loading, Docker, Makefile.
2. **RAG core** — `rag/types`, interfaces + registries for every component, at least two chunkers and two retrievers.
3. **Backend** — FastAPI app, PostgreSQL + pgvector integration, WebSocket chat messaging, document upload.
4. **Frontend** — Vite + React + TypeScript chat UI with streaming, markdown, and citations.
5. **Evaluation & experiments** — metric implementations, regression dataset, experiment runner.
6. **Agent** — `ai_agent/` with RAG as a tool.

---

*See [`CLAUDE.md`](CLAUDE.md) for the authoritative, detailed product specification (the original spec is preserved verbatim in `CLAUDE.md.spec-backup-2026-09-27.md`; if documents ever disagree, the backup is the source of truth for requirements).*