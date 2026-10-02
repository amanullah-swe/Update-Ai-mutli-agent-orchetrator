# 001 — AI Agent Core

- **Status:** `Specified`
- **Last updated:** 2026-09-27
- **Depends on:** `none`
- **Source:** CLAUDE.md — Architecture overview, Common Interfaces, Observability

## Problem / Motivation

The AI agent is the front door between the chat UI and the platform's capabilities. It must decide intent, choose tools (RAG among them), and produce an answer — while staying **deliberately separate from `rag/`**: the agent uses RAG as a tool, never as an implementation detail.

## Scope

**In scope**

- `ai_agent/agent/` package: `base.py`, `state.py`, `planner.py`, `executor.py`, `agent.py`
- The agent loop: message in → guardrails → plan → execute (tool calls) → guardrails → answer
- Streaming support so the backend's `/api/chat` SSE can drive token-by-token output
- Tracing: request_id, tool calls, latency, model/token usage (per Observability)
- `ai_agent/tests/` scaffolding with unit tests for state, planner, executor

**Out of scope**

- Concrete tools (feature 002), memory (003), prompts (004), guardrails (005)
- Any RAG implementation — `rag/` is consumed through its public interfaces only

## Behavioral contract

### Interfaces

- `Agent` protocol in `base.py` — the contract any agent implementation exposes (run + stream).
- `AgentState` in `state.py` — conversation id, messages, current plan, tool results, trace ids.
- `Planner` in `planner.py` — intent → plan (tool selection from the tools registry, config-driven).
- `Executor` in `executor.py` — runs the plan; enforces `max_iterations`; surfaces tool errors as agent-visible failures.
- Default `Agent` in `agent.py` — composes planner + executor + tools + memory + guardrails from config.

### Data flow

`message → input guardrail → state.update → plan (planner) → execute (executor → tool registry → tool) → state.update → output guardrail → answer (streamed)` — each step emits a trace event.

### Boundaries

- `ai_agent/agent/` must never `import rag.*` internals; only the public RAG interfaces (via the RAG tool, feature 002).
- Components are selected by name from config — no `if <strategy>:` in agent core.

## Configuration

```yaml
# configs/development.yaml
agent:
  model:
    provider: openrouter            # all model traffic via OpenRouter
    model: qwen/qwen3.8-27b:free
  max_iterations: 5
  max_tool_calls: 10
```

## Acceptance criteria

- [ ] `Agent` protocol defined in `ai_agent/agent/base.py`
- [ ] `AgentState` carries conversation id, messages, plan, tool results, and trace ids
- [ ] Default `Agent` runs the full loop end-to-end with a stub tool
- [ ] `Planner` selects tools from the tools registry by config name
- [ ] `Executor` enforces `max_iterations` and converts tool errors into agent-visible failures
- [ ] Agent exposes a streaming iteration the chat API can drive over SSE
- [ ] Every step records a trace event (request_id, latency, tool, model, token usage)
- [ ] Unit tests for `state`, `planner`, `executor` under `ai_agent/tests/unit/`
- [ ] No `import rag` anywhere in `ai_agent/agent/`

## Open questions

- [ ] Tool selection: single-shot planner (choose all tools up front) vs. reactive loop (choose per step)?

## Notes / links

- Monorepo contract: `ai_agent/agent/{base,agent,state,planner,executor}.py`
- CLAUDE.md: "The agent may use RAG as one of its tools/capabilities (intent → tool selection → RAG tool → answer)"