import unittest
from unittest.mock import MagicMock, patch
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository

class TestVectorMemoryRepository(unittest.TestCase):
    @patch("src.modules.ai.memory.repositories.vector_memory_repository.SupabaseVectorStore")
    @patch("src.modules.ai.memory.repositories.vector_memory_repository.OpenAIEmbeddings")
    def test_search_relevant(self, mock_embeddings, mock_vector_store_cls):
        # Arrange
        mock_client = MagicMock()
        mock_vector_store = mock_vector_store_cls.return_value
        
        # Mock similarity search result
        mock_doc = MagicMock()
        mock_doc.page_content = "Test content"
        mock_doc.metadata = {"role": "user"}
        mock_vector_store.similarity_search.return_value = [mock_doc]
        
        repo = VectorMemoryRepository(mock_client)
        
        # Act
        results = repo.search_relevant("query")
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Test content")
        mock_vector_store.similarity_search.assert_called_once_with("query", k=5, filter=None)

    @patch("src.modules.ai.memory.repositories.vector_memory_repository.SupabaseVectorStore")
    @patch("src.modules.ai.memory.repositories.vector_memory_repository.OpenAIEmbeddings")
    def test_add_texts(self, mock_embeddings, mock_vector_store_cls):
        # Arrange
        mock_client = MagicMock()
        mock_vector_store = mock_vector_store_cls.return_value
        repo = VectorMemoryRepository(mock_client)
        
        texts = ["hello"]
        metadatas = [{"id": 1}]
        
        # Act
        repo.add_texts(texts, metadatas)
        
        # Assert
        mock_vector_store.add_texts.assert_called_once_with(texts=texts, metadatas=metadatas)

if __name__ == '__main__':
    unittest.main()
