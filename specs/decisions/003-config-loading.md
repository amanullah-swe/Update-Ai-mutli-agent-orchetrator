# ADR-003 — Config loading: pydantic-settings + configs/*.yaml

- **Status:** Accepted
- **Date:** 2026-09-27
- **Related:** CLAUDE.md "Build decisions" #3

## Context

Configuration must be loaded once at startup into a typed object from which the
app constructs all components; components must never read YAML or env vars
themselves. The spec keeps config files under `configs/`.

Options: (a) pydantic-settings `BaseSettings` with env + `.env`;
(b) raw YAML → dataclass; (c) pydantic-settings with a YAML source layered below env.

## Decision

`pydantic-settings` `Settings` in `backend/app/core/config.py`, populated from
three priority layers (highest last): init kwargs → `RAG_*` env vars + `backend/.env`
→ `configs/<RAG_ENVIRONMENT>.yaml` (a low-priority custom source). A typed
`Settings` object is injected via FastAPI dependencies (`get_app_settings()`).
Nested YAML keys map to flat fields through an explicit alias table, so future
CLAUDE.md strategy sections (`chunking:`, `retrieval:`) parse without error and are
typo-guarded once the RAG feature consumes them.

## Consequences

- One canonical config object; components only depend on `Settings`.
- Env vars (e.g. `RAG_DATABASE_URL`) always override the YAML file → tests and Docker
  override cleanly without editing committed configs.
- Adding a config knob = one field + one YAML key (and an alias row if nested).