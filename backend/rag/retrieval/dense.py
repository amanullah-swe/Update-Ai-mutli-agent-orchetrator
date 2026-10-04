"""Dense vector retriever using embeddings and vector search."""

from __future__ import annotations

from typing import Any

from rag.core.registry import register
from rag.embeddings.base import BaseEmbeddingModel
from rag.embeddings.openrouter import OpenRouterEmbeddings
from rag.retrieval.base import BaseRetriever
from rag.types.retrieval import RetrievalQuery, RetrievedChunk
from rag.vectorstores.base import BaseVectorStore
from rag.vectorstores.pgvector import PGVectorStore


@register("retrieval", "dense")
class DenseRetriever(BaseRetriever):
    """Dense retriever that embeds the query and searches the vector store."""

    def __init__(
        self,
        vector_store: BaseVectorStore | None = None,
        embedding_model: BaseEmbeddingModel | None = None,
    ):
        self.vector_store = vector_store or PGVectorStore()
        self.embedding_model = embedding_model or OpenRouterEmbeddings()

    def retrieve(
        self,
        query: str | RetrievalQuery,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[RetrievedChunk]:
        query_text = query.text if isinstance(query, RetrievalQuery) else query
        query_filters = query.filters if isinstance(query, RetrievalQuery) else kwargs.get("filters")
        k = query.top_k if isinstance(query, RetrievalQuery) else top_k

        query_vector = self.embedding_model.embed_text(query_text)
        return self.vector_store.search(
            query_embedding=query_vector,
            top_k=k,
            filters=query_filters,
        )
