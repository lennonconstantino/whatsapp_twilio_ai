import unittest
from unittest.mock import MagicMock, patch, ANY
import json
from src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository import PostgresVectorMemoryRepository

class TestPostgresVectorMemoryRepository(unittest.TestCase):
    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    def test_hybrid_search_relevant(self, mock_embeddings_cls):
        # Arrange
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_db.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock embeddings
        mock_embeddings = mock_embeddings_cls.return_value
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        # Mock fetchall result
        # The repository expects RealDictCursor behavior (dict-like rows)
        mock_cursor.fetchall.return_value = [
            {
                "content": "Test content", 
                "metadata": {"role": "user"}, 
                "similarity": 0.9, 
                "score": 0.85
            }
        ]
        
        repo = PostgresVectorMemoryRepository(mock_db)
        
        # Act
        results = repo.hybrid_search_relevant("query", limit=5)
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Test content")
        self.assertEqual(results[0]["score"], 0.85)
        self.assertEqual(results[0]["similarity"], 0.9)
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql = args[0]
        params = args[1]
        
        self.assertIn("app.search_message_embeddings_hybrid_rrf", sql)
        
        # Check params
        # (query, vec, limit, match_threshold, payload, weight_vector, weight_text, rrf_k, fts_language)
        self.assertEqual(params[0], "query")
        self.assertTrue(params[1].startswith("[")) # Vector string
        self.assertEqual(params[2], 5) # limit
        self.assertEqual(params[3], 0.5) # default match_threshold
        self.assertEqual(params[4], "{}") # default filter
        
    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    def test_text_search_relevant(self, mock_embeddings_cls):
        # Arrange
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_db.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchall result
        mock_cursor.fetchall.return_value = [
            {
                "content": "Text match", 
                "metadata": {"role": "user"}, 
                "score": 0.75
            }
        ]
        
        repo = PostgresVectorMemoryRepository(mock_db)
        
        # Act
        results = repo.text_search_relevant("query", limit=3)
        
        # Assert
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "Text match")
        self.assertEqual(results[0]["score"], 0.75)
        
        # Verify SQL execution
        mock_cursor.execute.assert_called_once()
        args, _ = mock_cursor.execute.call_args
        sql = args[0]
        params = args[1]
        
        self.assertIn("app.search_message_embeddings_text", sql)
        
        # Check params: (query, limit, payload, lang)
        self.assertEqual(params[0], "query")
        self.assertEqual(params[1], 3)
        self.assertEqual(params[2], "{}")
        self.assertEqual(params[3], "portuguese")

if __name__ == '__main__':
    unittest.main()
