from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorMemoryRepository(ABC):
    """
    Abstract Base Class for Vector Memory Repository.
    Defines the contract for semantic search operations.
    """

    @abstractmethod
    def search_relevant(
        self, query: str, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity.
        
        Args:
            query: The search query string.
            limit: Maximum number of results to return.
            filter: Optional metadata filter.
            
        Returns:
            List of documents with content and metadata.
        """
        pass

    @abstractmethod
    def vector_search_relevant(
        self,
        query: str,
        *,
        limit: int = 15,
        match_threshold: float | None = None,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents with more control options.
        
        Args:
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
