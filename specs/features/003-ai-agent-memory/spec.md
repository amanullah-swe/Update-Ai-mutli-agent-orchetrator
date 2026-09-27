# 003 — Agent Memory

- **Status:** `Specified`
- **Last updated:** 2026-09-27
- **Depends on:** `001-ai-agent-core`
- **Source:** CLAUDE.md — Database (conversations, messages), Observability

## Problem / Motivation

Multi-turn conversations need state across turns: the agent must remember what was asked, what it retrieved, and which documents/chunks grounded each answer — so answers remain traceable back to sources.

## Scope

**In scope**

- `ai_agent/memory/base.py` — `Memory` interface
- `ai_agent/memory/conversation.py` — session-scoped conversation memory
- Persistence via the backend's `conversations` / `messages` tables (backend services own the DB)
- Trace linkage: record retrieved chunks + sources used per message

**Out of scope**

- Long-term / cross-conversation memory (user profiles, learned knowledge) — future feature
- Direct DB access from `ai_agent/` — persistence goes through backend services

## Behavioral contract

### Interface

```python
class Memory(Protocol):
    def get_session(self, conversation_id: str) -> Conversation: ...
    def append_user(self, conversation_id: str, message: Message) -> None: ...
    def append_assistant(self, conversation_id: str, message: Message, sources: list[Source]) -> None: ...
```

### Data flow

- Per turn: load conversation → append user message → agent runs → persist assistant message (with `sources` = chunks + documents used, so any answer can be traced back).

## Configuration

```yaml
# configs/development.yaml
agent:
  memory: conversation

memory:
  conversation:
    history_limit: 20          # turns sent to the model
    persist_chunks_used: true  # store trace of grounding sources per message
```

## Acceptance criteria

- [ ] `Memory` interface in `ai_agent/memory/base.py`
- [ ] `ConversationMemory` loads, appends, and persists turns through the backend message service
- [ ] Assistant messages record the chunks/documents that grounded the answer
- [ ] Memory is swappable by config name (`agent.memory: conversation`)
- [ ] Unit tests for `memory/conversation.py` with a fake message store

## Open questions

- [ ] History pruning strategy when `history_limit` is exceeded (drop oldest vs. summarize)?

## Notes / links

- DB entities `conversations` and `messages` are defined in CLAUDE.md's Database section.