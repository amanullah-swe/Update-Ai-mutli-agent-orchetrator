"""Orchestrator package — LLM routing layer with conditional RAG integration.

Sub-modules
-----------
- ``events``           — shared TokenEvent / SourcesEvent dataclasses
- ``llm_client``       — MockLLMClient and OpenRouterLLMClient
- ``rag_router``       — lightweight needs_rag() heuristic
- ``chat_orchestrator``— top-level ChatOrchestrator + build_chat_orchestrator factory

Import directly from the sub-modules to avoid circular dependencies:

    from orchestrator.chat_orchestrator import ChatOrchestrator, build_chat_orchestrator
    from orchestrator.events import TokenEvent, SourcesEvent, ProviderEvent
"""
