# 005 — Agent Guardrails

- **Status:** `Specified`
- **Last updated:** 2026-09-27
- **Depends on:** `001-ai-agent-core`
- **Source:** CLAUDE.md — Configuration model, Observability

## Problem / Motivation

The agent must not act on garbage input or emit unsourced/harmful output. Guardrails are named, swappable components on both sides of the loop, hooked in by config.

## Scope

**In scope**

- `ai_agent/guardrails/base.py` — `Guardrail` interface + chain runner
- `ai_agent/guardrails/input.py` — input validation (length, malformed payloads, obvious prompts)
- `ai_agent/guardrails/output.py` — output checks (citation requirement, safety, format)
- Failure policy: reject → clear fallback answer, recorded in the trace
- Config: `agent.guardrails: [input_basic]`, `guardrails.enabled`

**Out of scope**

- Filtering inside `rag/` — that is the RAG pipeline's concern (see Build decision #7).

## Behavioral contract

### Interface

```python
class Guardrail(Protocol):
    name: str

    def check_input(self, message: Message, state: AgentState) -> CheckResult: ...
    def check_output(self, answer: str, sources: list[Source], state: AgentState) -> CheckResult: ...
```

`CheckResult = {allowed: bool, reason?: str, action: Allow | Reject | Repair}`.

### Failure policy

- Input rejected → short, honest message back to the user (no LLM call).
- Output rejected → re-generate once; if still failing, return a fallback answer marked `ungrounded`.
- Every rejection writes to the trace with `guardrail: <name>, action, reason`.

## Configuration

```yaml
# configs/development.yaml
guardrails:
  enabled: true
  active:
    input: [input_basic]
    output: [output_citations]
```

## Acceptance criteria

- [ ] `Guardrail` interface + chain runner (all active guardrails run; any reject stops the flow)
- [ ] `input_basic` rejects empty/oversized/malformed input without an LLM call
- [ ] `output_citations` rejects answers lacking sources unless explicitly allowed
- [ ] Failure-policy paths (reject, repair, fallback) behave per spec and are traced
- [ ] Guardrails activate/deactivate by config name; unit tests cover each guardrail + the chain

## Open questions

- [ ] Should `output_citations` be on by default for the initial build, or opt-in per experiment?

## Notes / links

- Guardrails are agent-side; they complement, never replace, RAG-side evaluation.