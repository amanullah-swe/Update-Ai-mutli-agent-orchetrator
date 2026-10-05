"""Chat Orchestrator — the top-level answer-generation entry point.

Architecture
------------

                        user_message
                             │
                    ┌────────▼────────┐
                    │  rag_router     │  needs_rag(question)?
                    └────────┬────────┘
                 YES  ◄──────┴──────► NO
                  │                    │
      ┌───────────▼──────────┐         │
      │  RAGPipeline.query() │         │
      │  (dynamic dep.)      │         │
      └───────────┬──────────┘         │
            context + sources          │
                  │                    │
           ┌──────▼────────────────────▼──────┐
           │   LLM Client  (Mock / OpenRouter) │
           │   stream(msg, context=...) →      │
           │   TokenEvent* + SourcesEvent      │
           └────────────────────────────────── ┘

Key design decisions
--------------------
- ``rag_pipeline`` is injected at construction time (or ``None`` for direct LLM).
  The orchestrator never imports or instantiates RAGPipeline itself.
- When ``rag_pipeline`` is ``None`` *and* ``needs_rag()`` returns ``True``,
  the orchestrator falls back gracefully to direct LLM (logs a warning).
- Sources come from the RAG pipeline's ``ranked_chunks`` when available;
  otherwise an empty SourcesEvent is emitted.
- The public API intentionally mirrors the old ``ChatProvider.stream()``
  signature so ``ws.py`` needs minimal changes.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.features.chats.schemas import MessageOut, Source
from orchestrator.events import ProviderEvent, SourcesEvent, TokenEvent
from orchestrator.llm_client import MockLLMClient, OpenRouterLLMClient
from orchestrator.rag_router import needs_rag

if TYPE_CHECKING:
    pass

log = logging.getLogger("rag.platform.orchestrator")


# ---------------------------------------------------------------------------
# Minimal RAG pipeline protocol — avoids a hard import of rag.pipeline so
# the orchestrator package has no direct coupling to the rag package.
# Any object with a ``query(user_query, top_k)`` method qualifies.
# ---------------------------------------------------------------------------


@runtime_checkable
class RAGPipelineProtocol(Protocol):
    """Structural type for any RAG pipeline injected into the orchestrator."""

    def query(self, user_query: str, top_k: int = 5) -> dict: ...  # pragma: no cover


# ---------------------------------------------------------------------------
# LLM client protocol (internal) — both Mock and OpenRouter satisfy this
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMClientProtocol(Protocol):
    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None,
        token_delay_ms: int,
        context: str | None,
    ) -> Iterator[ProviderEvent]: ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class ChatOrchestrator:
    """Routes one chat turn through (optional) RAG then the LLM.

    Parameters
    ----------
    llm_client:
        A ``MockLLMClient`` or ``OpenRouterLLMClient`` instance (or any object
        satisfying ``LLMClientProtocol``). Built by ``build_chat_orchestrator``.
    rag_pipeline:
        An optional RAG pipeline.  When ``None`` the orchestrator always calls
        the LLM directly regardless of ``needs_rag()`` routing.  Inject a real
        ``RAGPipeline`` instance to enable context-augmented answers.
    """

    def __init__(
        self,
        llm_client: LLMClientProtocol,
        *,
        rag_pipeline: RAGPipelineProtocol | None = None,
    ) -> None:
        self._llm = llm_client
        self._rag = rag_pipeline

    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
    ) -> Iterator[ProviderEvent]:
        """Produce assistant events for one user turn.

        Flow
        ----
        1. Ask ``needs_rag()`` whether this question needs retrieved context.
        2. If YES and a pipeline is available → run RAG, collect context +
           ranked sources.
        3. Call the LLM client with the (optional) context string.
        4. When the LLM finishes streaming tokens, emit a ``SourcesEvent``
           carrying the RAG sources (or empty if none were retrieved).
        """
        context: str | None = None
        rag_sources: list[Source] = []

        if needs_rag(user_message):
            if self._rag is not None:
                try:
                    result = self._rag.query(user_message)
                    context = result.get("context")
                    # RAGPipeline returns RetrievedChunk objects; convert to Source
                    for chunk in result.get("sources", []):
                        chunk_id = getattr(chunk, "chunk_id", None) or getattr(getattr(chunk, "chunk", None), "id", None) or str(id(chunk))
                        rag_sources.append(
                            Source(
                                document_id=getattr(chunk, "document_id", ""),
                                chunk_id=chunk_id,
                                snippet=getattr(chunk, "content", ""),
                                score=float(getattr(chunk, "score", 0.0)),
                                metadata=getattr(chunk, "metadata", {}) or {},
                            )
                        )
                    log.info(
                        "RAG pipeline returned %d source(s) for query %r",
                        len(rag_sources),
                        user_message[:60],
                    )
                except Exception:  # noqa: BLE001
                    log.warning(
                        "RAG pipeline failed for query %r — falling back to direct LLM",
                        user_message[:60],
                        exc_info=True,
                    )
                    context = None
                    rag_sources = []
            else:
                log.debug(
                    "needs_rag=True but no pipeline injected — using direct LLM for %r",
                    user_message[:60],
                )

        # --- Stream LLM tokens -------------------------------------------
        for event in self._llm.stream(
            user_message,
            history=history,
            token_delay_ms=token_delay_ms,
            context=context,
        ):
            if isinstance(event, SourcesEvent):
                # Prefer RAG sources over the LLM client's empty SourcesEvent
                yield SourcesEvent(tuple(rag_sources) if rag_sources else event.sources)
            else:
                yield event


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_chat_orchestrator(
    settings: Settings,
    *,
    rag_pipeline: RAGPipelineProtocol | None = None,
) -> ChatOrchestrator:
    """Resolve ``settings.chat_provider`` to a concrete orchestrator.

    Parameters
    ----------
    settings:
        App settings (reads ``chat_provider``, ``llm_model``, ``llm_api_key``).
    rag_pipeline:
        Optional RAG pipeline injected at call-site.  Pass ``None`` (default)
        for direct-LLM mode; pass a ``RAGPipeline`` instance to enable
        context-augmented answers.
    """
    name = settings.chat_provider
    if name == "mock":
        return ChatOrchestrator(MockLLMClient(), rag_pipeline=rag_pipeline)
    if name == "openrouter":
        if not settings.llm_api_key:
            raise ValidationError(
                "llm.api_key is not configured — set RAG_LLM_API_KEY "
                "(and backend/.env) to use the OpenRouter chat provider.",
                details={"providers": ["mock", "openrouter"]},
            )
        llm = OpenRouterLLMClient(model=settings.llm_model, api_key=settings.llm_api_key)
        return ChatOrchestrator(llm, rag_pipeline=rag_pipeline)
    raise ValidationError(
        f"Unknown chat provider {name!r}. Known providers: mock, openrouter",
        details={"providers": ["mock", "openrouter"]},
    )
