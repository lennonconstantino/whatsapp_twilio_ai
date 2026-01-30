from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_openai import OpenAIEmbeddings
from supabase import Client

from src.core.config.settings import settings
from src.core.utils.logging import get_logger

logger = get_logger(__name__)


class VectorMemoryRepository:
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
            "Busca vetorial indisponível; desativando VectorMemoryRepository",
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

    def vector_search_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
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
            logger.error(f"Error searching vector store: {e}")
            return []

    def text_search_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        fts_language: str | None = None,
    ) -> List[Dict[str, Any]]:
        if self._disabled:
            return []

        try:
            params = {
                "query_text": query,
                "match_count": int(limit),
                "filter": filter or {},
                "fts_language": fts_language or settings.memory.fts_language,
            }
            result = self.client.rpc("search_message_embeddings_text", params).execute()
            data = result.data or []
            return [
                {
                    "content": row.get("content"),
                    "metadata": row.get("metadata"),
                    "score": row.get("score"),
                }
                for row in data
                if row.get("content")
            ]
        except Exception as e:
            error_text = str(e)
            if "PGRST202" in error_text or ("schema cache" in error_text):
                self._disable(error_text)
                return []
            logger.error(f"Error searching text index: {e}")
            return []

    def hybrid_search_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
        match_threshold: float = 0.0,
        filter: Optional[Dict[str, Any]] = None,
        weight_vector: float = 1.5,
        weight_text: float = 1.0,
        rrf_k: int = 60,
        fts_language: str | None = None,
    ) -> List[Dict[str, Any]]:
        if self._disabled:
            return []

        try:
            query_embedding = self.embeddings.embed_query(query)
            params = {
                "query_text": query,
                "query_embedding": query_embedding,
                "match_count": int(limit),
                "match_threshold": float(match_threshold),
                "filter": filter or {},
                "weight_vec": float(weight_vector),
                "weight_text": float(weight_text),
                "rrf_k": int(rrf_k),
                "fts_language": fts_language or settings.memory.fts_language,
            }
            result = self.client.rpc("search_message_embeddings_hybrid_rrf", params).execute()
            data = result.data or []
            return [
                {
                    "content": row.get("content"),
                    "metadata": row.get("metadata"),
                    "score": row.get("score"),
                }
                for row in data
                if row.get("content")
            ]
        except Exception as e:
            error_text = str(e)
            if "PGRST202" in error_text or ("schema cache" in error_text):
                self._disable(error_text)
                return []
            logger.error(f"Error searching hybrid index: {e}")
            return []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Add texts and metadata to the vector store.
        """
        try:
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Added {len(texts)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding texts to vector store: {e}")
