"""RAG routing — decides whether a user's question needs retrieved context.

The router is intentionally lightweight and heuristic-based by default so it
adds zero latency on the hot path.  A smarter implementation (e.g. ask the
LLM itself) can be swapped in by replacing ``needs_rag()``.

Design contract
---------------
- ``needs_rag(question)`` is **pure** — no I/O, no side-effects.
- Returns ``True``  → orchestrator should call the RAG pipeline first.
- Returns ``False`` → orchestrator calls the LLM directly.

The RAG pipeline itself is always injected by the caller; this module only
decides *whether* to use it.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Keyword sets that strongly suggest the question is about stored documents
# ---------------------------------------------------------------------------

_CONTEXT_SIGNALS: frozenset[str] = frozenset(
    {
        # document / knowledge-base references
        "document",
        "documents",
        "doc",
        "file",
        "files",
        "pdf",
        "uploaded",
        "indexed",
        "ingested",
        "knowledge base",
        "knowledge-base",
        # retrieval / RAG terminology
        "retrieve",
        "retrieval",
        "search",
        "find",
        "lookup",
        "look up",
        "fetch",
        "context",
        "sources",
        "citations",
        # temporal / recency signals (often refers to indexed material)
        "latest",
        "recent",
        "last",
        "new",
        "update",
        "changelog",
        # platform-specific
        "chunk",
        "chunks",
        "embedding",
        "embeddings",
        "vector",
        "pipeline",
    }
)

_BYPASS_PREFIXES: tuple[str, ...] = (
    "what is ",
    "what's ",
    "who is ",
    "who's ",
    "define ",
    "explain ",
    "how does ",
    "why does ",
    "tell me about ",
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
)


def needs_rag(question: str) -> bool:
    """Return ``True`` when the question likely requires retrieved context.

    Strategy (fast, zero-latency):

    1. Very short greetings / chitchat → **False** (bypass).
    2. Any context-signal keyword present → **True**.
    3. Question starts with a general-knowledge prefix → **False**.
    4. Default → **True** (conservative: prefer context over hallucination).
    """
    q = question.strip().lower()

    if not q:
        return False

    # 1. Pure chitchat / extremely short message
    if len(q) < 15 and any(q.startswith(p) for p in ("hi", "hey", "hello", "thanks", "thank")):
        return False

    # 2. Explicit context-signal keyword
    for signal in _CONTEXT_SIGNALS:
        if signal in q:
            return True

    # 3. Generic "explain X" / "what is X" → general knowledge, no RAG needed
    if any(q.startswith(prefix) for prefix in _BYPASS_PREFIXES):
        return False

    # 4. Conservative default — let RAG decide via retrieval score
    return True
