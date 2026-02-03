from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from supabase import Client

from src.core.config.settings import settings
from src.core.utils.logging import get_logger
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository

logger = get_logger(__name__)


class SupabaseVectorMemoryRepository(VectorMemoryRepository):
    """
    Repository for Semantic Memory (L3) using Supabase Vector (pgvector).
    """

    def __init__(self, supabase_client: Client):
        self.client = supabase_client
        self.embeddings = self._init_embeddings()
        self._disabled = False
        self._disabled_reason: str | None = None
        
        # Initialize SupabaseVectorStore
        # Note: table_name and query_name must match the SQL migration
        self.vector_store = SupabaseVectorStore(
            client=self.client,
            embedding=self.embeddings,
            table_name="message_embeddings",
            query_name="match_message_embeddings",
        )

    def _disable(self, reason: str) -> None:
        if self._disabled:
            return
        self._disabled = True
        self._disabled_reason = reason
        logger.warning(
            "Busca vetorial indisponível; desativando SupabaseVectorMemoryRepository",
            reason=reason,
        )

    def _init_embeddings(self):
        """Initialize embedding model based on settings."""
        if settings.embedding.provider == "openai":
            return OpenAIEmbeddings(
                model=settings.embedding.model_name,
                # dimensions=settings.embedding.dimensions # OpenAIEmbeddings might not support forcing dimensions in init, it depends on model
            )
        else:
            # Fallback to OpenAI for now
            logger.warning(f"Unsupported embedding provider: {settings.embedding.provider}. Using OpenAI.")
            return OpenAIEmbeddings(model="text-embedding-3-small")

    def search_relevant(
        self, query: str, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity.
        """
        return self.vector_search_relevant(query, limit=limit, match_threshold=None, filter=filter)

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Add texts to the vector store.
        """
        if self._disabled:
            return []
        
        try:
            return self.vector_store.add_texts(texts=texts, metadatas=metadatas)
        except Exception as e:
            error_text = str(e)
            if "PGRST202" in error_text or ("schema cache" in error_text):
                self._disable(error_text)
            logger.error(f"Error adding texts to Supabase vector store: {e}")
            raise e

    def vector_search_relevant(
        self,
        query: str,
        *,
        limit: int = 10,
        match_threshold: float | None = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self._disabled:
            return []

        try:
            if match_threshold is None:
                docs = self.vector_store.similarity_search(query, k=limit, filter=filter)
                return [{"content": d.page_content, "metadata": d.metadata} for d in docs]

            query_embedding = self.embeddings.embed_query(query)
            params = {
                "query_embedding": query_embedding,
                "match_threshold": float(match_threshold),
                "match_count": int(limit),
                "filter": filter or {},
            }
            result = self.client.rpc("match_message_embeddings", params).execute()
            data = result.data or []
            return [
                {
                    "content": row.get("content"),
                    "metadata": row.get("metadata"),
                    "score": row.get("similarity"),
                }
                for row in data
                if row.get("content")
            ]
        except Exception as e:
            error_text = str(e)
            if "PGRST202" in error_text or ("schema cache" in error_text):
                self._disable(error_text)
            return []
