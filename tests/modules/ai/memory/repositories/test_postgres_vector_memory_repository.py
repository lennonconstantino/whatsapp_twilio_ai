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
        results = repo.hybrid_search_relevant("owner_id", "query", limit=5)
        
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
        self.assertEqual(params[4], '{"owner_id": "owner_id"}') # default filter with owner_id
        
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

    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    def test_vector_search_relevant(self, mock_embeddings_cls):
        # Arrange
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_db.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_embeddings = mock_embeddings_cls.return_value
        mock_embeddings.embed_query.return_value = [0.1, 0.2]
        
        mock_cursor.fetchall.return_value = [
            {"content": "C1", "metadata": {}, "similarity": 0.9}
        ]
        
        repo = PostgresVectorMemoryRepository(mock_db)
        
        # Act
        results = repo.vector_search_relevant("owner_id", "query", limit=2)
        
        # Assert
        self.assertEqual(len(results), 1)
        mock_cursor.execute.assert_called_once()
        self.assertIn("app.match_message_embeddings", mock_cursor.execute.call_args[0][0])

    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.execute_values")
    def test_add_texts(self, mock_execute_values, mock_embeddings_cls):
        # Arrange
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_db.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_embeddings = mock_embeddings_cls.return_value
        mock_embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        mock_cursor.fetchall.return_value = [("1",), ("2",)]
        
        repo = PostgresVectorMemoryRepository(mock_db)
        
        # Act
        ids = repo.add_texts(["t1", "t2"], [{"m": 1}, {"m": 2}])
        
        # Assert
        self.assertEqual(ids, ["1", "2"])
        mock_execute_values.assert_called_once()
        # Verify commit
        mock_conn.commit.assert_called_once()

    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    def test_add_texts_empty(self, mock_embeddings_cls):
        repo = PostgresVectorMemoryRepository(MagicMock())
        ids = repo.add_texts([])
        self.assertEqual(ids, [])

    @patch("src.modules.ai.memory.repositories.impl.postgres.vector_memory_repository.OpenAIEmbeddings")
    def test_search_exception_handling(self, mock_embeddings_cls):
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.execute.side_effect = Exception("DB Error")
        
        repo = PostgresVectorMemoryRepository(mock_db)
        
        # Should not raise
        results = repo.vector_search_relevant("owner_id", "query")
        self.assertEqual(results, [])
        
        # Check disable logic if function missing
        mock_cursor.execute.side_effect = Exception("function match_message_embeddings does not exist")
        repo.vector_search_relevant("owner_id", "query")
        self.assertTrue(repo._disabled)

if __name__ == '__main__':
    unittest.main()
