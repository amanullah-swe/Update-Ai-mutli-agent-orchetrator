# ──────────────────────────────────────────────────────────────────────────────
# Makefile – Development shortcuts for the RAG Learning Platform
# ──────────────────────────────────────────────────────────────────────────────
.DEFAULT_GOAL := help
SHELL         := /bin/bash

# ── Docker ────────────────────────────────────────────────────────────────────

.PHONY: up
up: ## Start all services (db + backend + frontend) in the foreground
	docker compose up --build

.PHONY: up-d
up-d: ## Start all services in the background (detached)
	docker compose up --build -d

.PHONY: down
down: ## Stop and remove all containers, networks
	docker compose down

.PHONY: down-v
down-v: ## Stop all containers and delete volumes (⚠️  wipes DB data)
	docker compose down -v

.PHONY: restart
restart: down up ## Restart all services

.PHONY: logs
logs: ## Tail logs from all running services
	docker compose logs -f

.PHONY: logs-backend
logs-backend: ## Tail logs from the backend service only
	docker compose logs -f backend

.PHONY: logs-frontend
logs-frontend: ## Tail logs from the frontend service only
	docker compose logs -f frontend

.PHONY: ps
ps: ## Show status of all services
	docker compose ps

.PHONY: build
build: ## Build all Docker images without starting
	docker compose build

# ── Local dev (no Docker) ─────────────────────────────────────────────────────

.PHONY: install
install: install-backend install-frontend ## Install all dependencies locally

.PHONY: install-backend
install-backend: ## Install backend Python dependencies via uv
	cd backend && uv sync

.PHONY: install-frontend
install-frontend: ## Install frontend npm dependencies
	cd frontend && npm ci

.PHONY: dev
dev: ## Run backend + frontend locally in parallel (needs local Postgres)
	@echo "Starting backend and frontend in parallel…"
	@$(MAKE) -j2 dev-backend dev-frontend

.PHONY: dev-backend
dev-backend: ## Run the FastAPI backend locally (uvicorn, port 8001)
	cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server locally (port 5173)
	cd frontend && npm run dev

# ── Database ──────────────────────────────────────────────────────────────────

.PHONY: db
db: ## Start only the database container
	docker compose up -d db

.PHONY: db-shell
db-shell: ## Open a psql shell inside the running db container
	docker compose exec db psql -U rag -d rag_learning

.PHONY: migrate
migrate: ## Run Alembic migrations (head)
	cd database/migrations && alembic upgrade head

.PHONY: migrate-down
migrate-down: ## Rollback one Alembic migration
	cd database/migrations && alembic downgrade -1

# ── Testing ───────────────────────────────────────────────────────────────────

.PHONY: test
test: test-backend test-frontend ## Run all tests

.PHONY: test-backend
test-backend: ## Run backend tests via pytest
	cd backend && uv run pytest

.PHONY: test-frontend
test-frontend: ## Run frontend unit/component tests via vitest
	cd frontend && npm test

.PHONY: test-frontend-unit
test-frontend-unit: ## Run frontend unit/component tests via vitest
	cd frontend && npm run test:unit

.PHONY: test-frontend-coverage
test-frontend-coverage: ## Run frontend tests with coverage report
	cd frontend && npm run test:coverage

.PHONY: test-frontend-e2e
test-frontend-e2e: ## Run frontend end-to-end browser automation tests via Playwright
	cd frontend && npm run test:e2e

.PHONY: test-frontend-all
test-frontend-all: ## Run all frontend tests (unit + e2e)
	cd frontend && npm run test:all

.PHONY: test-frontend-watch
test-frontend-watch: ## Run frontend tests in watch mode
	cd frontend && npm run test:watch

# ── Linting ───────────────────────────────────────────────────────────────────

.PHONY: lint
lint: lint-frontend ## Run all linters

.PHONY: lint-frontend
lint-frontend: ## Lint frontend with oxlint
	cd frontend && npm run lint

# ── Cleanup ───────────────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf frontend/dist frontend/node_modules/.vite
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/rag_learning_backend.egg-info

.PHONY: clean-all
clean-all: clean down-v ## Clean artifacts + destroy Docker volumes (⚠️  full reset)
	docker image rm $$(docker compose config --images) 2>/dev/null || true

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
