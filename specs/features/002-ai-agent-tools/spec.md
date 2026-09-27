# 002 — Agent Tools

- **Status:** `Specified`
- **Last updated:** 2026-09-27
- **Depends on:** `001-ai-agent-core`
- **Source:** CLAUDE.md — Common Interfaces, "Build decisions" #1, Architecture overview

## Problem / Motivation

Tools are the agent's only way to touch the outside world (RAG retrieval first; more later). They must be pluggable like every other component: implement an interface, register it, name it in config — no touching agent core.

## Scope

**In scope**

- `ai_agent/tools/base.py` — `Tool` interface + registry
- `ai_agent/tools/rag.py` — `RagTool`: query → retrieved chunks (+ scores, sources)
- Registration decorator + `build_component("tool", name)` factory (Build decision #1)
- Config: `tools.active: [rag]`
- Unit tests `ai_agent/tests/unit/test_tools.py`

**Out of scope**

- The RAG pipeline itself — `rag/` is a separate project package consumed through its public interfaces
- Non-RAG tools (web search, calculators, …) — future feature files

## Behavioral contract

### Interface

```python
class Tool(Protocol):
    name: str
    description: str
    parameters: JSONSchema | None

    def run(self, **kwargs) -> ToolResult: ...
```

`ToolResult` = `{output, chunks?, sources?, metadata(tool, latency, tokens)}` — sent downstream, cross-checkable against citations.

### Registration

- `@register("rag")` class decorator on `RagTool`; `build_component("tool", name)` returns the instance from config and raises a loud error listing known tools for an unknown name.

## Configuration

```yaml
# configs/development.yaml
tools:
  active: [rag]

rag_tool:
  top_k: 5
  retrieval_strategy: hybrid     # delegates to rag/ config
```

### Boundaries

- `rag.py` calls the `rag` package's public pipeline interface only; never chunkers/retrievers directly.

## Acceptance criteria

- [ ] `Tool` interface in `ai_agent/tools/base.py`
- [ ] Registry + `@register` + `build_component("tool", name)` work; unknown name raises an error listing known tools
- [ ] `RagTool` returns chunks with scores and source document refs
- [ ] Adding a tool = new file + `@register` + add to `tools.active` — no agent-core edits
- [ ] Unit tests covering registration, unknown-name error, and `RagTool` against a stub retriever

## Open questions

- [ ] Tool result size caps (max chunks returned to the LLM) — decide with context-building limits.

## Notes / links

- Mirrors Build decision #1 (per-component-type registry) so tools and RAG components share the same plugin mechanism.