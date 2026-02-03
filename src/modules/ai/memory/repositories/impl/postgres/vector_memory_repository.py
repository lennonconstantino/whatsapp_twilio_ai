import json
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from psycopg2.extras import RealDictCursor, execute_values

from src.core.config.settings import settings
from src.core.database.postgres_session import PostgresDatabase
from src.core.utils.logging import get_logger
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository

logger = get_logger(__name__)


class PostgresVectorMemoryRepository(VectorMemoryRepository):
    def __init__(self, db: PostgresDatabase):
        self.db = db
        self.embeddings = self._init_embeddings()
        self._disabled = False
        self._disabled_reason: str | None = None

    def _disable(self, reason: str) -> None:
        if self._disabled:
            return
        self._disabled = True
        self._disabled_reason = reason
        logger.warning(
            "Busca vetorial indisponível; desativando PostgresVectorMemoryRepository",
            reason=reason,
        )

    def _init_embeddings(self):
        if settings.embedding.provider == "openai":
            return OpenAIEmbeddings(model=settings.embedding.model_name)
        logger.warning(
            f"Unsupported embedding provider: {settings.embedding.provider}. Using OpenAI."
        )
        return OpenAIEmbeddings(model="text-embedding-3-small")

    @staticmethod
    def _vector_literal(embedding: List[float]) -> str:
        return "[" + ",".join(f"{float(x):.8f}" for x in embedding) + "]"

    def search_relevant(
        self, query: str, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        return self.vector_search_relevant(query, limit=limit, match_threshold=None, filter=filter)

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        if self._disabled:
            return []
        
        if not texts:
            return []

        try:
            embeddings = self.embeddings.embed_documents(texts)
            if metadatas is None:
                metadatas = [{} for _ in texts]
            
            values = []
            for i, text in enumerate(texts):
                metadata = metadatas[i] if i < len(metadatas) else {}
                embedding = embeddings[i]
                # Use _vector_literal to format the embedding vector
                values.append((text, json.dumps(metadata), self._vector_literal(embedding)))

            # Use execute_values for efficient bulk insert
            # Assuming message_embeddings table exists in the search path (usually public)
            # Casting string literal to vector
            insert_query = "INSERT INTO message_embeddings (content, metadata, embedding) VALUES %s RETURNING id"
            
            with self.db.connection() as conn:
                cur = conn.cursor()
                try:
                    # template defines how values are formatted. 
                    # %s for content, %s for metadata (json), %s::extensions.vector for embedding
                    # Note: We assume 'extensions' schema for vector type based on previous SQL
                    # but if vector extension is in public, it should be just vector.
                    # The code in vector_search_relevant used 'extensions.vector(1536)'.
                    execute_values(
                        cur, 
                        insert_query, 
                        values, 
                        template="(%s, %s, %s::extensions.vector)"
                    )
                    ids = [str(row[0]) for row in cur.fetchall()]
                    # Commit is handled by the context manager usually? 
                    # PostgresDatabase.connection() returns a context manager that yields connection.
                    # Usually we need to commit explicitly if autocommit is off.
                    conn.commit()
                    return ids
                finally:
                    cur.close()

        except Exception as e:
            logger.error(f"Error adding texts to Postgres vector store: {e}")
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
            query_embedding = self.embeddings.embed_query(query)
            vec = self._vector_literal(query_embedding)
            threshold = float(match_threshold) if match_threshold is not None else 0.0
            payload = json.dumps(filter or {})
            sql_query = (
                "SELECT content, metadata, similarity "
                "FROM app.match_message_embeddings(%s::extensions.vector(1536), %s, %s, %s::jsonb)"
            )
            with self.db.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur.execute(sql_query, (vec, threshold, int(limit), payload))
                    rows = cur.fetchall() or []
                    return [
                        {
                            "content": r.get("content"),
                            "metadata": r.get("metadata"),
                            "score": r.get("similarity"),
                        }
                        for r in rows
                        if r.get("content")
                    ]
                finally:
                    cur.close()
        except Exception as e:
            error_text = str(e)
            if "match_message_embeddings" in error_text or "does not exist" in error_text:
                self._disable(error_text)
                return []
            logger.error(f"Error searching vector store (postgres): {e}")
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
        # TODO: Implement text search if needed
        return []
