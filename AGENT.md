# AGENT.md (Architectural Specification & Agent Guidelines)

This file provides authoritative guidance to AI coding agents (Antigravity, Claude Code, etc.) when working with code in this repository.

## Project Status

- **Status:** Active, modular monolith with FastAPI backend, React frontend, PostgreSQL + pgvector storage, and a pluggable RAG subsystem.
- **Implemented Components:**
  - **`backend/`**: FastAPI service (`app.main:app`), feature-sliced structure (`app/features/chats/`, `app/features/health/`), WebSocket streaming (`/api/chats/{chat_id}/ws`), chat CRUD endpoints, Alembic database migrations, and typed settings.
  - **`orchestrator/`**: Dynamic chat orchestrator coordinating streaming events (`TokenEvent`, `SourcesEvent`), LLM clients (`MockLLMClient`, `OpenRouterLLMClient`), and RAG routing.
  - **`rag/`**: Modular RAG subsystem with swappable components:
    - Ingestion: PDF loader (`pymupdf`), PDF parser, text cleaner, ingestion pipeline.
    - Chunking: `OverlapChunker` (sliding window), `FixedSizeChunker`.
    - Embeddings: `OpenRouterEmbeddings` via OpenRouter remote API (`sentence-transformers/all-minilm-l6-v2`, 384 dimensions matching pgvector schema). *Local `sentence-transformers` and PyTorch dependencies were eliminated to keep Docker images lean (~1.1 GB savings).*
    - Vector Storage: `PGVectorStore` with PostgreSQL pgvector extension on the `chunks` table.
    - Retrieval: `DenseRetriever` using dense vector similarity search.
    - Reranking: `NoOpReranker` (pass-through).
    - Context Building: `DefaultContextBuilder`.
    - Generation: `OpenRouterGenerator` via OpenRouter API.
    - Pipeline: `RAGPipeline` orchestrator coordinating Query Transformation → Retrieval → Reranking → Context Construction → Generation.
  - **`frontend/`**: React + Vite + TypeScript application with Tailwind styling, WebSocket streaming message client, markdown rendering, and chat history management.
  - **`database/`**: PostgreSQL migrations via Alembic (`b2e9f1c4a5d6_initial_chat_schema.py`, `c3a4f2b1d0e9_add_chunks_pgvector_table.py`).
  - **`docker/`**: Containerized deployment with `Dockerfile.backend` (multi-stage BuildKit caching, `entrypoint.sh` auto-migrations), `Dockerfile.frontend` (Nginx + static build), and `docker-compose.yml`.

---

## Core Architectural Rule (Highest Priority)

> **Every RAG strategy must be implemented as a replaceable component behind a common interface. The core pipeline must depend on interfaces, not concrete implementations. Strategy selection must happen through configuration.**

Consequences that always apply:
- The RAG pipeline must never contain `if <strategy>:` dispatch chains or import concrete implementations directly.
- Swapping strategies means editing a configuration value — nothing else. Changing `retrieval: { strategy: dense }` to `hybrid` must be sufficient to run the identical pipeline with another strategy.
- Every swappable component registers with `@register(kind, name)` and is built via `build_component(kind, name, **kwargs)`.
- Components receive resolved settings through dependency injection; components never read raw YAML files or `os.environ` directly.

---

## Architecture & Monorepo Layout

```text
.
├── backend/                  FastAPI modular application
│   ├── app/
│   │   ├── core/             config.py (Settings), logging.py, exceptions.py
│   │   ├── database/         session.py, base.py
│   │   ├── features/
│   │   │   ├── chats/        router.py, schemas.py, models.py, repository.py, ws.py
│   │   │   └── health/       router.py, schemas.py
│   │   └── main.py           FastAPI factory, CORS, exception handlers, routers
│   ├── orchestrator/         ChatOrchestrator, LLMClient, events, rag_router
│   ├── rag/                  Modular RAG Subsystem
│   │   ├── core/             base.py, registry.py, exceptions.py
│   │   ├── types/            document.py, chunk.py, retrieval.py
│   │   ├── ingestion/        loaders/, parsers/, cleaners/, pipeline.py
│   │   ├── chunking/         base.py, overlap.py, fixed_size.py
│   │   ├── embeddings/       base.py, openrouter.py
│   │   ├── vectorstores/     base.py, pgvector.py, models.py
│   │   ├── retrieval/        base.py, dense.py
│   │   ├── reranking/        base.py, noop.py
│   │   ├── query/            base.py, passthrough.py
│   │   ├── context/          base.py, builder.py
│   │   ├── generation/       base.py, llm.py
│   │   └── pipeline.py       RAGPipeline coordinating all stages
│   ├── scripts/              index_document.py (PDF indexing utility)
│   ├── tests/                tests/unit/ (66 tests), tests/integration/ (23 tests)
│   ├── entrypoint.sh         Container startup script: runs Alembic migrations, starts Uvicorn
│   ├── pyproject.toml        Python >=3.13 dependencies (uv)
│   └── uv.lock               Deterministic dependency lockfile
├── configs/                  Environment YAML configs (development.yaml, testing.yaml, production.yaml)
├── database/                 Database schemas & migrations
│   ├── migrations/           alembic.ini, env.py, versions/
│   ├── schemas/              reference.sql
│   └── seed/                 dev.sql
├── frontend/                 React + TypeScript + Vite UI
│   ├── src/                  components/, hooks/, services/, types/
│   ├── package.json          npm dependencies
│   └── vite.config.ts        Vite build configuration
├── docker-compose.yml        Multi-container orchestration (db, backend, frontend)
├── Dockerfile.backend        Lean Python 3.13-slim image with BuildKit cache
├── Dockerfile.frontend       Multi-stage Node build + Nginx static server
├── Makefile                  Developer command shortcuts
└── AGENT.md                  Architectural specification & guidelines
```

---

## Common Interfaces & Component Registry

Every swappable component implements one of the abstract base classes in `rag/` and registers with `@register(kind, name)`:

| Component Kind | Base Interface | Active / Known Implementations |
| :--- | :--- | :--- |
| `loader` | `BaseLoader` | `pdf` (`PyMuPDFLoader`) |
| `parser` | `BaseParser` | `pdf` (`PDFParser`) |
| `cleaner` | `BaseCleaner` | `default`, `text` (`TextCleaner`) |
| `chunking` | `BaseChunker` | `overlap` (`OverlapChunker`), `fixed_size` |
| `embedding` | `BaseEmbeddingModel` | `openrouter`, `default`, `sentence_transformer` (OpenRouter alias) |
| `vectorstore` | `BaseVectorStore` | `pgvector` (`PGVectorStore`) |
| `query_transformation` | `BaseQueryTransformer` | `none`, `passthrough` (`PassThroughQueryTransformer`) |
| `retrieval` | `BaseRetriever` | `dense` (`DenseRetriever`) |
| `reranking` | `BaseReranker` | `none`, `noop` (`NoOpReranker`) |
| `context_builder` | `BaseContextBuilder` | `default` (`DefaultContextBuilder`) |
| `generator` | `BaseGenerator` | `openrouter`, `llm` (`OpenRouterGenerator`) |

---

## Model & Provider Conventions

All external model traffic is routed through **OpenRouter** to avoid local weights and excessive image sizes:

1. **LLM Generation**:
   - Provider: `openrouter`
   - Default Model: `deepseek/deepseek-v4-flash-0731` or `qwen/qwen3.8-27b:free`
   - Config field: `llm.model` / `RAG_LLM_MODEL`
   - API Key: `RAG_LLM_API_KEY` in `backend/.env`
2. **Dense Vector Embeddings**:
   - Provider: `openrouter`
   - Model: `sentence-transformers/all-minilm-l6-v2` via OpenRouter
   - Vector dimensionality: `384` (strictly matches PostgreSQL `chunks.embedding` `Vector(384)`)
   - Shared Credentials: Automatically uses `RAG_LLM_API_KEY` (or `RAG_EMBEDDING_API_KEY`)
   - Batching: `OpenRouterEmbeddings.embed_batch` automatically handles batch chunking (default 64 items per request).

---

## Database & Migration Lifecycle

1. **Single Source of Truth**:
   - Alembic (`database/migrations/`) is the sole DDL source.
   - Migrations are versioned and purely DDL (`CREATE TABLE`, `CREATE INDEX`, `CREATE EXTENSION`).
2. **Container Auto-Migration**:
   - `Dockerfile.backend` copies `database/` and `configs/` into `/app`.
   - `backend/entrypoint.sh` executes `alembic upgrade head` before `uvicorn` starts:
     ```bash
     uv run --no-sync alembic -c /app/database/migrations/alembic.ini upgrade head
     exec "$@"
     ```
   - **Idempotency**: Alembic tracks the applied version in `alembic_version` (`c3a4f2b1d0e9`). When the container reboots, Alembic checks the table, sees it is up to date, and exits in <50ms without touching existing data or duplicating rows.

---

## Runnable Commands

### 1. Docker Compose (Full Stack)
```bash
# Start all services (PostgreSQL 17, FastAPI backend, React frontend)
docker compose up --build -d

# View service status
docker compose ps

# Tail backend logs
docker compose logs -f backend

# Stop all services
docker compose down

# Stop all services and wipe database volume
docker compose down -v
```

### 2. Local Backend Development (without Docker)
```bash
# Install / sync backend dependencies
cd backend && uv sync

# Run backend development server (:8001)
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Run Alembic migrations against local/container DB
cd backend && uv run alembic -c ../database/migrations/alembic.ini upgrade head

# Index a document into the RAG vector store
cd backend && uv run python -m scripts.index_document path/to/document.pdf
```

### 3. Testing
```bash
# Run complete test suite (unit + integration tests, requires DB)
cd backend && uv run pytest

# Run pure unit tests (fast, no database required)
cd backend && uv run pytest tests/unit/

# Run specific test file
cd backend && uv run pytest tests/unit/rag/test_embeddings.py
```

### 4. Local Frontend Development
```bash
# Install frontend dependencies
cd frontend && npm install

# Start Vite development server (:5173)
cd frontend && npm run dev

# Run frontend tests
cd frontend && npm test
```

---

## Backend API Surface

```text
POST   /api/chats                 Create a new conversation
GET    /api/chats                 List conversations (most recent activity first)
GET    /api/chats/{id}            Get conversation details + message transcript
PATCH  /api/chats/{id}            Rename conversation title
DELETE /api/chats/{id}            Delete conversation (cascades messages)
WS     /api/chats/{id}/ws         Bidirectional WebSocket for streaming chat & RAG
GET    /api/health                System liveness and database reachability check
GET    /docs                      Interactive OpenAPI / Swagger UI
```

---

## Software Development Rules & Engineering Guidelines

All developers and AI coding agents working in this repository must strictly adhere to the following rules:

### 1. Function Design & Unit of Work (Unit Functions)
- **Single Responsibility per Function**: Every function must perform exactly **one unit of work** and do it well. If a function is validating input, fetching data, transforming data, and writing to a database, decompose it into discrete, single-purpose helper functions.
- **Short & Focused**: Aim for functions of 15–35 lines. A function that exceeds 40–50 lines is usually doing multiple things and must be refactored into smaller, cohesive units.
- **Separation of Pure Logic and I/O**:
  - Keep pure business logic (calculations, text parsing, formatting, filtering) completely free of I/O operations (HTTP calls, DB queries). Pure functions are trivial to test and reason about.
  - Keep orchestrators and controllers thin: they should only coordinate calling single-purpose domain functions.
- **Guard Clauses & Early Returns**:
  - Handle error cases, edge cases, and preconditions at the top of the function with early returns or raises.
  - Avoid deeply nested `if/else` ladders (keep cyclomatic complexity low, max 2–3 levels of indentation).
- **Descriptive, Intention-Revealing Names**:
  - Name functions with strong verb-noun pairings that precisely state their single action: `validate_chat_title()`, `extract_pdf_pages()`, `compute_similarity_score()`.
  - Avoid vague verbs like `process()`, `handle()`, or `manage()` when a specific verb is applicable (`sanitize_text()`, `persist_message()`).

### 2. Core Architectural & Coding Principles
- **SOLID Principles**:
  - **S (Single Responsibility)**: Modules, classes, and functions each have exactly one reason to change.
  - **O (Open/Closed)**: Extend RAG strategies via `@register` without altering core pipeline code.
  - **L (Liskov Substitution)**: Any subclass/implementation must satisfy the exact contract of its base interface (`BaseEmbeddingModel`, `BaseRetriever`, `BaseChunker`).
  - **I (Interface Segregation)**: Small, targeted interfaces over monolithic god-interfaces.
  - **D (Dependency Inversion)**: High-level modules depend on abstract interfaces, never on concrete implementation details.
- **DRY (Don't Repeat Yourself)**: Extract duplicated logic into reusable utility functions, but balance DRY against premature coupling.
- **KISS (Keep It Simple, Stupid)**: Choose clear, obvious, readable implementations over clever meta-programming, complex inheritance trees, or obscure one-liners.
- **YAGNI (You Aren't Gonna Need It)**: Implement only what is specified for current requirements. Do not build speculative features, parameters, or abstract layers for imaginary future use cases.
- **Law of Demeter (Least Knowledge)**: An object should only communicate with its immediate collaborators. Avoid long method chains (`a.b.c.get_d()`).

### 3. Code Quality & Clean Code Standards
- **Strict Typing & Self-Documentation**:
  - Mandatory `from __future__ import annotations` in all Python files.
  - Provide full type hints on every parameter and return value.
  - Avoid `Any`; use explicit types, `Union`, `Literal`, or `Protocol`.
  - Write concise docstrings on public classes and functions explaining **why** (rationale, non-obvious constraints), not just restating the name.
- **Defensive Programming & Fail Fast**:
  - Validate parameters and boundaries early. If a required value is missing, raise a domain-specific exception immediately rather than propagating invalid state or returning silent `None`.
  - Use Pydantic models for boundary validation (HTTP payloads, configuration).
- **Immutability & State Safety**:
  - Prefer immutable data representations (`dataclass(frozen=True)`, `NamedTuple`, Pydantic models with frozen configs) where feasible.
  - Avoid mutating function arguments in place; return new collections or transformed objects instead.
- **Explicit Over Implicit**:
  - Never use wildcard imports (`from module import *`).
  - Be explicit with constants, timeouts, and error messages.

### 4. Python & Backend Standards
- **Error Handling Architecture**:
  - Raise domain-specific exceptions inheriting from platform bases (`RAGError`, `LLMProviderError`, `ChatNotFoundError`).
  - Never swallow exceptions with bare `except: pass` or catch generic `Exception` without context. Always use `except Exception as exc: raise DomainError(...) from exc`.
  - Global FastAPI exception handlers format domain errors into consistent JSON error responses.
- **Configuration & Dependency Injection**:
  - Business logic and RAG components must never read `os.environ` or YAML files directly.
  - Inject configuration via `Settings` (`app.core.config.get_settings()`).
  - Endpoints receive DB sessions via FastAPI dependency injection (`Depends(get_db)`).
- **Async & Threading Hygiene**:
  - Use `async def` for I/O-bound endpoints (WebSockets, async HTTP calls).
  - Delegate synchronous blocking operations (SQLAlchemy DB transactions, CPU-heavy parsing) to worker threadpools (`run_in_threadpool`) to keep the async event loop responsive.
- **Lean Dependencies**:
  - Keep containers lightweight. Never introduce heavy binary libraries (e.g. PyTorch, CUDA toolkits) without explicit architectural review. Prefer remote API integrations (OpenRouter) for model execution.

### 5. Frontend & TypeScript Standards
- **Type Safety**:
  - Strict TypeScript with `noImplicitAny: true`.
  - Never use `any`; use `unknown` with type guards or define explicit interfaces.
- **Component Hygiene**:
  - Small, modular components. Separate presentation from data fetching and state hooks.
  - Explicitly handle all 4 UI states: `idle`, `loading`, `success`, and `error`.
  - Centralize API calls in service classes; do not sprinkle raw `fetch()` calls across components.

### 6. Database & Migration Governance
- **Alembic Exclusivity**:
  - Alembic (`database/migrations/`) is the sole DDL authority.
  - Never run manual DDL (`ALTER TABLE`, `CREATE TABLE`) directly in production or call `Base.metadata.create_all()` in application code.
  - All migrations must be transactional, reversible (`downgrade` implemented), and idempotent.
- **Data Integrity**:
  - Never embed seed or mock data inside DDL migrations. Migrations must alter schema only.
  - Use foreign keys with cascade constraints where appropriate (`ondelete="CASCADE"`).

### 7. Testing & Quality Assurance
- **Hermetic Unit Tests**:
  - Unit tests in `backend/tests/unit/` must execute in < 2 seconds and require **zero network and zero database**.
  - Always mock external APIs (OpenRouter, external endpoints) using `httpx.MockTransport`.
- **Integration Tests**:
  - Integration tests in `backend/tests/integration/` verify database sessions and WebSocket flows against a real PostgreSQL test database.
- **Test Before Completing**:
  - Every change or feature must be verified with `uv run pytest tests/unit/`.
  - Never leave failing or skipped tests unaddressed.

### 8. Security & Repository Hygiene
- **Zero Committed Secrets**:
  - Never commit API keys, passwords, private tokens, or `.env` files.
  - Keep `.env.example` up to date with empty dummy values for newly introduced environment variables.
- **Preserve Unrelated Code**:
  - Do not delete, reformat, or alter comments, docstrings, or unrelated files unless explicitly requested.