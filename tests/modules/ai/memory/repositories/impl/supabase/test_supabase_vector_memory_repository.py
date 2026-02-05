
import pytest
from unittest.mock import MagicMock, patch
from src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository import SupabaseVectorMemoryRepository

class TestSupabaseVectorMemoryRepository:
    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def mock_embeddings(self):
        with patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.OpenAIEmbeddings") as mock:
            yield mock

    @pytest.fixture
    def mock_vector_store_cls(self):
        with patch("src.modules.ai.memory.repositories.impl.supabase.vector_memory_repository.SupabaseVectorStore") as mock:
            yield mock

    @pytest.fixture
    def repository(self, mock_client, mock_embeddings, mock_vector_store_cls):
        return SupabaseVectorMemoryRepository(mock_client)

    def test_search_relevant(self, repository, mock_vector_store_cls):
        mock_vector_store = mock_vector_store_cls.return_value
        
        # Mock similarity search result
        mock_doc = MagicMock()
        mock_doc.page_content = "Test content"
        mock_doc.metadata = {"role": "user"}
        mock_vector_store.similarity_search.return_value = [mock_doc]
        
        results = repository.search_relevant("owner_id", "query")
        
        assert len(results) == 1
        assert results[0]["content"] == "Test content"
        mock_vector_store.similarity_search.assert_called_once_with("query", k=5, filter={"owner_id": "owner_id"})

    def test_search_relevant_disables_on_missing_rpc(self, repository, mock_vector_store_cls):
        mock_vector_store = mock_vector_store_cls.return_value
        mock_vector_store.similarity_search.side_effect = Exception(
            "{'code': 'PGRST202', 'message': 'Could not find the function public.match_message_embeddings(query_embedding) in the schema cache'}"
        )

        first = repository.search_relevant("owner_id", "query")
        second = repository.search_relevant("owner_id", "query")

        assert first == []
        assert second == []
        assert mock_vector_store.similarity_search.call_count == 1
        assert repository._disabled is True

    def test_add_texts(self, repository, mock_vector_store_cls):
        mock_vector_store = mock_vector_store_cls.return_value
        mock_vector_store.add_texts.return_value = ["id1"]
        
        ids = repository.add_texts(["content"], [{"meta": "data"}])
        
        assert ids == ["id1"]
        mock_vector_store.add_texts.assert_called_once_with(texts=["content"], metadatas=[{"meta": "data"}])

    def test_vector_search_relevant_with_threshold(self, repository, mock_client, mock_embeddings):
        # Setup embeddings mock
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2]
        
        # Setup RPC call
        mock_response = MagicMock()
        mock_response.data = [
            {"content": "Match", "metadata": {"role": "user"}, "similarity": 0.9}
        ]
        mock_client.rpc.return_value.execute.return_value = mock_response

        results = repository.vector_search_relevant("owner_id", "query", limit=5, match_threshold=0.8)

        assert len(results) == 1
        assert results[0]["content"] == "Match"
        assert results[0]["score"] == 0.9
        
        mock_client.rpc.assert_called_with(
            "match_message_embeddings",
            {
                "query_embedding": [0.1, 0.2],
                "match_threshold": 0.8,
                "match_count": 5,
                "filter": {"owner_id": "owner_id"}
            }
        )

    def test_hybrid_search_relevant(self, repository, mock_client, mock_embeddings):
        # Setup embeddings mock
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2]
        
        # Setup RPC call
        mock_response = MagicMock()
        mock_response.data = [
            {"content": "Hybrid Match", "metadata": {"role": "user"}, "score": 0.85, "similarity": 0.8}
        ]
        mock_client.schema.return_value.rpc.return_value.execute.return_value = mock_response

        results = repository.hybrid_search_relevant("owner_id", "query")

        assert len(results) == 1
        assert results[0]["content"] == "Hybrid Match"
        assert results[0]["score"] == 0.85
        
        mock_client.schema.assert_called_with("app")
        mock_client.schema.return_value.rpc.assert_called_with(
            "search_message_embeddings_hybrid_rrf",
            {
                "query_text": "query",
                "query_embedding": [0.1, 0.2],
                "match_count": 10,
                "match_threshold": 0.5,
                "filter": {"owner_id": "owner_id"},
                "weight_vec": 1.5,
                "weight_text": 1.0,
                "rrf_k": 60,
                "fts_language": "portuguese"
            }
        )

    def test_hybrid_search_exception(self, repository, mock_client):
        mock_client.schema.return_value.rpc.side_effect = Exception("Supabase Error")
        
        results = repository.hybrid_search_relevant("owner_id", "query")
        
        assert results == []

    def test_add_texts_exception(self, repository, mock_vector_store_cls):
        mock_vector_store = mock_vector_store_cls.return_value
        mock_vector_store.add_texts.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            repository.add_texts(["content"])

    def test_add_texts_disabled(self, repository):
        repository._disabled = True
        ids = repository.add_texts(["content"])
        assert ids == []
