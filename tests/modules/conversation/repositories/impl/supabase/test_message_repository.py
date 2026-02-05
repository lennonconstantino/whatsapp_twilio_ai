import pytest
from unittest.mock import MagicMock
from src.modules.conversation.repositories.impl.supabase.message_repository import SupabaseMessageRepository
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_owner import MessageOwner
from src.core.utils.exceptions import DuplicateError

class TestSupabaseMessageRepository:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        return client

    @pytest.fixture
    def repository(self, mock_client):
        return SupabaseMessageRepository(mock_client)

    @pytest.fixture
    def mock_message_data(self):
        return {
            "msg_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "content": "Hello",
            "body": "Hello",
            "from_number": "+1234567890",
            "to_number": "+0987654321",
            "message_owner": "user",
            "timestamp": "2023-01-01T00:00:00+00:00",
            "metadata": {"message_sid": "SM123"}
        }

    def test_create_duplicate_error(self, repository, mock_client, mock_message_data):
        # Mock exception
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("duplicate key value violates unique constraint")
        
        with pytest.raises(DuplicateError):
            repository.create(mock_message_data)
            
    def test_find_by_conversation(self, repository, mock_client, mock_message_data):
        mock_response = MagicMock()
        mock_response.data = [mock_message_data]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_response
        
        result = repository.find_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)
        
    def test_find_by_external_id(self, repository, mock_client, mock_message_data):
        mock_response = MagicMock()
        mock_response.data = [mock_message_data]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = repository.find_by_external_id("SM123")
        
        assert isinstance(result, Message)
        assert result.msg_id == mock_message_data["msg_id"]
        
    def test_find_by_external_id_not_found(self, repository, mock_client):
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = repository.find_by_external_id("SM123")
        
        assert result is None

    def test_find_recent_by_conversation(self, repository, mock_client, mock_message_data):
        mock_response = MagicMock()
        mock_response.data = [mock_message_data]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        
        result = repository.find_recent_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)

    def test_find_user_messages(self, repository, mock_client, mock_message_data):
        mock_response = MagicMock()
        mock_response.data = [mock_message_data]
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_response
        
        result = repository.find_user_messages("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)
        
    def test_count_by_conversation(self, repository, mock_client):
        mock_response = MagicMock()
        mock_response.count = 5
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        result = repository.count_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result == 5
