# <NNN> — <Feature name>

- **Status:** `Draft`
- **Last updated:** YYYY-MM-DD
- **Depends on:** `none` (or `<NNN>-<feature>`)
- **Source:** CLAUDE.md § <section> · spec-backup § <section>

## Problem / Motivation

What gap does this feature fill, and why now? Tie it to the product requirements in CLAUDE.md.

## Scope

**In scope**

- ...

**Out of scope** (future features)

- ...

## Behavioral contract

### Interfaces (from Common Interfaces — CLAUDE.md)

- Defines/uses one of: `DocumentLoader` / `DocumentParser` / `DocumentCleaner` / `Chunker` / `EmbeddingModel` / `VectorStore` / `Retriever` / `Reranker` / `QueryTransformer` / `ContextBuilder` / `Generator` / `Evaluator` — or a new agent-side interface.

### Data flow

1. ...

### Configuration

```yaml
# configs/development.yaml
attachable:
  strategy: ...
```

## Acceptance criteria

- [ ] ...
- [ ] ...

## Open questions

- [ ] ...

## Notes / links

- ...