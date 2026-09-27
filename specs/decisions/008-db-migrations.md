# ADR-008 — DB migrations: Alembic is the single source of truth

- **Status:** Accepted
- **Date:** 2026-09-27
- **Related:** CLAUDE.md "Build decisions" #8

## Context

The monorepo layout has both `database/migrations/` and `database/schemas/`.
CLAUDE.md decision #8 asks which is authoritative.

Options: (a) Alembic migrations are the source of truth, `schemas/` is reference
DDL; (b) hand-written DDL in `schemas/` is authoritative, migrations mirror it.

## Decision

**Alembic (`database/migrations/`, revision `a37a02c9694e` initial) is the only DDL
source.** `database/schemas/reference.sql` is a human-readable reference /
`pg_dump` target, never applied, and never edited by hand to chase the schema.
Migrations read the URL from the app's `Settings` (`env.py`), so the same path
works in dev, tests (`rag_learning_test`), and Docker (`db:5432`). Tests rebuild
the schema exclusively through Alembic (`command.upgrade`) — no `create_all` on
PostgreSQL.

## Consequences

- Schema drift between code and DB is caught by autogenerate diffs.
- Tests prove migration idempotence by rerunning `upgrade head`.
- Contributors must know: to change the schema, edit a model, run
  `make migrate-make`, review the revision, then `make migrate`.