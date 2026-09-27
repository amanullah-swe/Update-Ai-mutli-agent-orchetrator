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
2. **Python tooling** — the original spec shows `requirements.txt`. → Prefer `uv` + `pyproject.toml` unless a pip-only constraint exists. Pin core dependencies.
3. **Config loading** — YAML files under `configs/` loaded once at startup into a typed config object (→ pydantic-settings), from which the app constructs all components via dependency injection. Components never read YAML or env vars themselves.
4. **Framework dependence** — the folder layout (format-specific loaders/parsers/cleaners) implies hand-written implementations behind custom interfaces. → Keep custom interfaces and add thin adapters to third-party libraries (LangChain, LlamaIndex, RAGAS, etc.), so swappability never depends on a framework.
5. **Frontend tooling** — → Vite + React + TypeScript, with an SSE client for `/api/chat` streaming.
6. **Sparse retrieval storage** — `rag/retrieval/sparse.py` needs a sparse index that pgvector cannot provide. → PostgreSQL FTS / `pg_search` alongside pgvector, or an in-memory BM25 index. Pick one.
7. **Filtering stage** — the pipeline stage list includes *Filtering*, but the folder layout has no `rag/filtering/` module (closest is `rag/context/deduplication.py`). → Either add a `rag/filtering/` package with an interface, or officially fold filtering into retrieval. Decide and keep the layout consistent with the pipeline stages.
8. **DB migrations** — `database/migrations/` and `database/schemas/` both exist in the layout. → Alembic migrations are the source of truth; treat `database/schemas/` as raw DDL / seed reference only.
9. **Config key vocabulary** — the spec mixes `provider` (for `llm`, `embedding`) and `strategy` (for `chunking`, `retrieval`, `reranking`). Keep both but document `strategy` as the general term; update all sample configs to match.
10. **Streaming transport** — the spec says SSE "where appropriate" and the chat API must stream. → Standardize on SSE (`text/event-stream`) for `/api/chat`.

## Commands

*None exist yet — this section is a placeholder. When the Makefile and per-package READMEs land, fill in (then delete this note):*

- Backend (dev): `make backend` — uvicorn app reload, plus migration/seed steps.
- Frontend (dev): `cd frontend && npm run dev`.
- Tests: `make test` / `pytest` — and the single-test invocation form, e.g. `pytest rag/chunking/test_recursive.py::test_name`.
- Lint/format: the agreed tool and target packages.

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
├── backend/           FastAPI — app/api/routes/{chat,documents,evaluation,experiments}.py, app/core/{config,logging,exceptions}.py,
│                      app/models/, app/schemas/, app/services/, app/main.py, tests/
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

## Backend API surface (minimum)

```text
POST /api/chat                    (SSE streaming responses)
POST /api/documents/upload
GET  /api/documents
DELETE /api/documents/{id}
POST /api/evaluation/run
GET  /api/evaluation/results
POST /api/experiments/run
GET  /api/experiments/{id}
GET  /api/health
```

## Configuration model

All strategy selection happens through configuration, read at startup, never at component level. Example shape:

```yaml
llm:
  provider: openrouter
  model: deepseek/deepseek-v4-flash-0731
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

## Definition of Done (acceptance checklist for the initial build)

- React frontend runs; FastAPI backend runs; PostgreSQL + pgvector connected.
- Document upload and ingestion work.
- At least two chunking strategies and two retrieval strategies selectable; embedding strategy changeable via config; reranking toggleable via config.
- RAG pipeline executes end-to-end; chatbot answers from RAG with streamed responses.
- Evaluation runs against a dataset; unit/integration/regression tests exist.
- Experiments compare different configurations.
- Changing a strategy does **not** require modifying the core RAG pipeline.
- README explains how to add a new strategy.