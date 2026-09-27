# 004 — Agent Prompts

- **Status:** `Specified`
- **Last updated:** 2026-09-27
- **Depends on:** `001-ai-agent-core`
- **Source:** CLAUDE.md — Observability (prompt/model version), Testing (golden dataset)

## Problem / Motivation

Prompt changes silently shift behavior. Prompts must be versioned artifacts that the agent loads, whose versions land in traces — so a bad answer can be traced to a specific prompt version, and prompt changes are regression-tested against the golden dataset.

## Scope

**In scope**

- `ai_agent/prompts/base.py` — `PromptTemplate` model + loading/rendering
- `ai_agent/prompts/system.py` — agent system prompt
- `ai_agent/prompts/task.py` — planner / tool-selection / generation prompts
- Version strings surfaced into the trace for every LLM call
- Prompt rendering must be reproducible (no nondeterminism)

**Out of scope**

- RAG generation prompts — owned by `rag/` (generation stage), not the agent
- External prompt-management services

## Behavioral contract

### Interface

```python
class PromptTemplate(BaseModel):
    name: str
    version: str          # e.g. "1.0.0" — lands in traces
    text: str             # with {placeholders}

    def render(self, **kwargs) -> str: ...
```

### Data flow

- At startup the prompts package loads all templates; the agent renders by name+version; every LLM call records `prompt: {name, version}` in the trace.

## Configuration

```yaml
# configs/development.yaml
prompts:
  system: agent/system/1.0.0
  planner: agent/planner/1.0.0
  generation: agent/generation/1.0.0
```

### Boundaries

- Templates are data, loaded via the prompts package — never string-built inline in agent code.

## Acceptance criteria

- [ ] `PromptTemplate` loads, validates placeholders, and renders reproducibly
- [ ] System + task prompts exist as versioned templates; `render` fails loudly on missing params
- [ ] Each LLM call records prompt name + version in the trace
- [ ] A prompt change bumps its version (visible in traces), and the regression suite reruns
- [ ] Unit tests for rendering, missing params, and version extraction

## Open questions

- [ ] Store templates as `.txt`/`.j2` files beside the package vs. inline constants?

## Notes / links

- Prompts are agent-side; `rag/` owns its own generation prompts (feature work in the rag package).