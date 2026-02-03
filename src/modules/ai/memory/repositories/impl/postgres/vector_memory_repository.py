import json
from typing import Any, Dict, List, Optional

from langchain_openai import OpenAIEmbeddings
from psycopg2.extras import RealDictCursor, execute_values

from src.core.config.settings import settings
from src.core.database.postgres_session import PostgresDatabase
from src.core.utils.logging import get_logger

logger = get_logger(__name__)


class PostgresVectorMemoryRepository:
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
        try:
            payload = json.dumps(filter or {})
            language = fts_language or settings.memory.fts_language
            sql_query = (
                "SELECT content, metadata, score "
                "FROM app.search_message_embeddings_text(%s, %s, %s::jsonb, %s)"
            )
            with self.db.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur.execute(sql_query, (query, int(limit), payload, language))
                    rows = cur.fetchall() or []
                    return [
                        {
                            "content": r.get("content"),
                            "metadata": r.get("metadata"),
                            "score": r.get("score"),
                        }
                        for r in rows
                        if r.get("content")
                    ]
                finally:
                    cur.close()
        except Exception as e:
            error_text = str(e)
            if "search_message_embeddings_text" in error_text or "does not exist" in error_text:
                self._disable(error_text)
                return []
            logger.error(f"Error searching text index (postgres): {e}")
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
            vec = self._vector_literal(query_embedding)
            payload = json.dumps(filter or {})
            language = fts_language or settings.memory.fts_language
            sql_query = (
                "SELECT content, metadata, similarity, score "
                "FROM app.search_message_embeddings_hybrid_rrf("
                "%s, %s::extensions.vector(1536), %s, %s, %s::jsonb, %s, %s, %s, %s)"
            )
            with self.db.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur.execute(
                        sql_query,
                        (
                            query,
                            vec,
                            int(limit),
                            float(match_threshold),
                            payload,
                            float(weight_vector),
                            float(weight_text),
                            int(rrf_k),
                            language,
                        ),
                    )
                    rows = cur.fetchall() or []
                    return [
                        {
                            "content": r.get("content"),
                            "metadata": r.get("metadata"),
                            "score": r.get("score"),
                            "similarity": r.get("similarity"),
                        }
                        for r in rows
                        if r.get("content")
                    ]
                finally:
                    cur.close()
        except Exception as e:
            error_text = str(e)
            if "search_message_embeddings_hybrid_rrf" in error_text or "does not exist" in error_text:
                self._disable(error_text)
                return []
            logger.error(f"Error searching hybrid index (postgres): {e}")
            return []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        if self._disabled:
            return
        if not texts:
            return
        if len(texts) != len(metadatas):
            raise ValueError("texts e metadatas devem ter o mesmo tamanho")
        try:
            embeddings = self.embeddings.embed_documents(texts)
            rows = []
            for text, metadata, emb in zip(texts, metadatas, embeddings):
                rows.append(
                    (
                        text,
                        json.dumps(metadata or {}),
                        self._vector_literal(emb),
                    )
                )
            insert_sql = (
                "INSERT INTO app.message_embeddings (content, metadata, embedding) VALUES %s"
            )
            template = "(%s, %s::jsonb, %s::extensions.vector(1536))"
            with self.db.connection() as conn:
                cur = conn.cursor()
                try:
                    execute_values(cur, insert_sql, rows, template=template)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    cur.close()
        except Exception as e:
            error_text = str(e)
            if "message_embeddings" in error_text or "does not exist" in error_text:
                self._disable(error_text)
                return
            logger.error(f"Error adding texts to vector store (postgres): {e}")

