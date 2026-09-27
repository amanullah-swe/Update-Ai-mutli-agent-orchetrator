# ADR-002 — Python tooling: uv + pyproject.toml

- **Status:** Accepted
- **Date:** 2026-09-27
- **Related:** CLAUDE.md "Build decisions" #2

## Context

The original spec shows a `requirements.txt`. CLAUDE.md decision #2 prefers
`uv` + `pyproject.toml` unless a pip-only constraint exists. This feature is the
first to introduce Python code, so it must pick the toolchain.

Options: (a) `uv` + `pyproject.toml` — fast resolver, lockfile, native dep groups;
(b) plain `pip` + `venv` + `requirements.txt`.

## Decision

Use **uv** + `pyproject.toml` (`uv sync`, `uv runtime via `uv run`), with a
committed `uv.lock`. Python `>=3.13` (developed on 3.14). Dev/test deps are a
PEP 735 `[dependency-groups] dev` group so runtime and dev are separated.

## Consequences

- Reproducible installs across dev/CI/docker via the lockfile (`uv sync --frozen`).
- **uv itself must be installed** (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- Contributors who prefer pip can still `uv export` → `requirements.txt`, but uv is the maintained path.
- All `Makefile`/README commands use `uv run`.