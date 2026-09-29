# RAG Learning Platform — developer command surface.

PY := uv run --project backend

.PHONY: help backend frontend dev db test migrate migrate-make seed up up-all down install-docker

## Show this help and exit
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## //'

## Backend (dev): uvicorn with reload on :8001
backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8001

## Frontend (dev): Vite dev server on :5173 (talks to backend on :8001 via VITE_API_BASE_URL)
frontend:
	cd frontend && npm run dev

## Everything (dev): PostgreSQL + migrations + backend + frontend in one Ctrl+C-able session
dev:
	@$(MAKE) db
	@$(MAKE) migrate
	@printf '\n=== backend  → http://localhost:8001   (API + WebSocket)\n'
	@printf '=== frontend → http://localhost:5173   (Vite dev server)\n'
	@printf '=== Ctrl+C stops both.\n'
	@sh -c 'trap "kill 0 2>/dev/null" EXIT; \
		(cd backend && uv run uvicorn app.main:app --reload --port 8001) & \
		(cd frontend && npm run dev) & \
		wait'

## Database: start PostgreSQL via Docker and wait until it accepts connections
db:
	docker compose -f docker/docker-compose.yml up -d db
	@printf 'Waiting for PostgreSQL on localhost:5432…\n'
	@for i in $$(seq 1 30); do \
		docker compose -f docker/docker-compose.yml exec -T db pg_isready -U rag -d rag_learning >/dev/null 2>&1 && { printf 'PostgreSQL ready.\n'; exit 0; }; \
		sleep 1; \
	done; \
	printf 'PostgreSQL not ready after 30s — check:\n  docker compose -f docker/docker-compose.yml logs db\n' >&2; \
	exit 1

## Tests: full suite (unit + integration against PostgreSQL)
test:
	cd backend && uv run pytest

## Apply Alembic migrations (the only DDL source)
migrate:
	$(PY) alembic -c database/migrations/alembic.ini upgrade head

## Autogenerate a migration: make migrate-make name="add column x"
migrate-make:
	$(PY) alembic -c database/migrations/alembic.ini revision --autogenerate -m "$(name)"

## Seed dev data (through the Docker PostgreSQL — there is no host psql)
seed:
	docker compose -f docker/docker-compose.yml exec -T db psql -U rag -d rag_learning -f - < database/seed/dev.sql

## Docker Compose: bring up just PostgreSQL (alias for db)
up: db

## Docker Compose: bring up PostgreSQL + backend
up-all:
	docker compose -f docker/docker-compose.yml up --build

## Stop all Docker Compose services
down:
	docker compose -f docker/docker-compose.yml down

## Install Docker Engine + Compose plugin (Ubuntu/Debian, official repo); needs sudo
install-docker:
	@if command -v docker >/dev/null 2>&1; then echo "Docker already installed: $$(docker --version)"; exit 0; fi
	sudo apt-get update
	sudo apt-get install -y ca-certificates curl
	sudo install -m 0755 -d /etc/apt/keyrings
	sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
	sudo chmod a+r /etc/apt/keyrings/docker.asc
	printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$$(dpkg --print-architecture)" "$$(. /etc/os-release && printf '%s' "$$VERSION_CODENAME")" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
	sudo apt-get update
	sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	@printf '\nDone. To run docker without sudo:  sudo usermod -aG docker $$USER   (then log out/in).\n'
