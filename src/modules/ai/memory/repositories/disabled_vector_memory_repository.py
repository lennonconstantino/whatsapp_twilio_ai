from typing import Any, Dict, List, Optional

from src.core.utils.logging import get_logger

logger = get_logger(__name__)


class DisabledVectorMemoryRepository:
    def __init__(self, reason: str = "vector_store_disabled"):
        self._reason = reason
        logger.warning(
            "VectorMemoryRepository desativado",
            reason=reason,
        )

    def search_relevant(
        self, query: str, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        return []

    def vector_search_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
        match_threshold: float | None = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return []

    def text_search_relevant(
        self,
        query: str,
        *,
        limit: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        fts_language: str | None = None,
    ) -> List[Dict[str, Any]]:
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
        return []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        return None
