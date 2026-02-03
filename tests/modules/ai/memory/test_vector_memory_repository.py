import unittest
from unittest.mock import MagicMock, patch
from src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository import SupabaseVectorMemoryRepository

class TestVectorMemoryRepository(unittest.TestCase):
    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.SupabaseVectorStore")
    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.OpenAIEmbeddings")
    def test_search_relevant(self, mock_embeddings, mock_vector_store_cls):
        # Arrange
        mock_client = MagicMock()
        mock_vector_store = mock_vector_store_cls.return_value
        
        # Mock similarity search result
        mock_doc = MagicMock()
        mock_doc.page_content = "Test content"
        mock_doc.metadata = {"role": "user"}
        mock_vector_store.similarity_search.return_value = [mock_doc]
        
        repo = SupabaseVectorMemoryRepository(mock_client)
        
        # Act
        results = repo.search_relevant("query")
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Test content")
        mock_vector_store.similarity_search.assert_called_once_with("query", k=5, filter=None)

    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.SupabaseVectorStore")
    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.OpenAIEmbeddings")
    def test_search_relevant_disables_on_missing_rpc(self, mock_embeddings, mock_vector_store_cls):
        mock_client = MagicMock()
        mock_vector_store = mock_vector_store_cls.return_value
        mock_vector_store.similarity_search.side_effect = Exception(
            "{'code': 'PGRST202', 'message': 'Could not find the function public.match_message_embeddings(query_embedding) in the schema cache'}"
        )

        repo = SupabaseVectorMemoryRepository(mock_client)

        first = repo.search_relevant("query")
        second = repo.search_relevant("query")

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(mock_vector_store.similarity_search.call_count, 1)

    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.SupabaseVectorStore")
    @patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.OpenAIEmbeddings")
    def test_add_texts(self, mock_embeddings, mock_vector_store_cls):
        # Arrange
        mock_client = MagicMock()
        mock_vector_store = mock_vector_store_cls.return_value
        mock_vector_store.add_texts.return_value = ["id1"]
        
        repo = SupabaseVectorMemoryRepository(mock_client)
        
        # Act
        ids = repo.add_texts(["content"], [{"meta": "data"}])
        
        # Assert
        self.assertEqual(ids, ["id1"])
        mock_vector_store.add_texts.assert_called_once_with(texts=["content"], metadatas=[{"meta": "data"}])

if __name__ == '__main__':
    unittest.main()
