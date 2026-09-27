# RAG Learning Platform — developer command surface.

PY := uv run --project backend

.PHONY: backend test migrate migrate-make seed up down

## Backend (dev): uvicorn with reload on :8001
backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8001

## Tests: full suite (unit + integration against PostgreSQL)
test:
	cd backend && uv run pytest

## Apply Alembic migrations (the only DDL source)
migrate:
	$(PY) alembic -c database/migrations/alembic.ini upgrade head

## Autogenerate a migration: make migrate-make name="add column x"
migrate-make:
	$(PY) alembic -c database/migrations/alembic.ini revision --autogenerate -m "$(name)"

## Seed dev data
seed:
	PGPASSWORD=rag psql -h localhost -U rag -d rag_learning -f database/seed/dev.sql

## Docker Compose: bring up just PostgreSQL
up:
	docker compose -f docker/docker-compose.yml up -d db

## Docker Compose: bring up PostgreSQL + backend
up-all:
	docker compose -f docker/docker-compose.yml up --build

down:
	docker compose -f docker/docker-compose.yml down