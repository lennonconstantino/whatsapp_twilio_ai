from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorMemoryRepository(ABC):
    """
    Abstract Base Class for Vector Memory Repository.
    Defines the contract for semantic search operations.
    """

    @abstractmethod
    def search_relevant(
        self, owner_id: str, query: str, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            owner_id: ID of the owner (Tenant) - MANDATORY for security.
            query: The search query string.
            limit: Maximum number of results to return.
            filter: Optional metadata filter.
            
        Returns:
            List of documents with content and metadata.
        """
        pass

    @abstractmethod
    def hybrid_search_relevant(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 10,
        match_threshold: float = 0.5,
        filter: Optional[Dict[str, Any]] = None,
        weight_vector: float = 1.5,
        weight_text: float = 1.0,
        rrf_k: int = 60,
        fts_language: str = "portuguese",
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using Hybrid Search (Vector + FTS) with RRF fusion.

        Args:
            owner_id: ID of the owner (Tenant) - MANDATORY for security.
            query: The search query string.
            limit: Maximum number of results to return.
            match_threshold: Minimum similarity score threshold for vector search.
            filter: Optional metadata filter.
            weight_vector: Weight for vector search rank in RRF.
            weight_text: Weight for text search rank in RRF.
            rrf_k: RRF constant K.
            fts_language: Language for FTS (Full Text Search).

        Returns:
            List of documents with content, metadata, similarity and score.
        """
        pass

    @abstractmethod
    def vector_search_relevant(
        self,
        owner_id: str,
        query: str,
        *,
        limit: int = 15,
        match_threshold: float | None = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents with more control options.
        
        Args:
            owner_id: ID of the owner (Tenant) - MANDATORY for security.
            query: The search query string.
            limit: Maximum number of results to return.
            match_threshold: Minimum similarity score threshold.
            filter: Optional metadata filter.
            
        Returns:
            List of documents with content, metadata and score.
        """
        pass

    @abstractmethod
    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        Add texts to the vector store.

        Args:
            texts: List of text strings to add.
            metadatas: Optional list of metadata dictionaries associated with the texts.

        Returns:
            List of IDs of the added texts.
        """
        pass
