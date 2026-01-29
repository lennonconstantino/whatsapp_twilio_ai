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
        
        # Initialize SupabaseVectorStore
        # Note: table_name and query_name must match the SQL migration
        self.vector_store = SupabaseVectorStore(
            client=self.client,
            embedding=self.embeddings,
            table_name="message_embeddings",
            query_name="match_message_embeddings",
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
        try:
            docs = self.vector_store.similarity_search(query, k=limit, filter=filter)
            return [{"content": d.page_content, "metadata": d.metadata} for d in docs]
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
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
