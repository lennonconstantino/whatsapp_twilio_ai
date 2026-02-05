
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.modules.conversation.repositories.impl.supabase.message_repository import SupabaseMessageRepository
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.core.utils.exceptions import DuplicateError

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def repository(mock_client):
    return SupabaseMessageRepository(mock_client)

@pytest.fixture
def mock_message_data():
    return {
        "msg_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "from_number": "+1234567890",
        "to_number": "+0987654321",
        "body": "Hello World",
        "direction": "inbound",
        "timestamp": datetime.utcnow().isoformat(),
        "sent_by_ia": False,
        "message_owner": "user",
        "message_type": "text",
        "content": "Hello World",
        "metadata": {"message_sid": "SM12345"}
    }

def test_create_duplicate_error(repository, mock_client, mock_message_data):
    # Setup mock to raise duplicate error
    mock_error = Exception("Duplicate key")
    mock_error.code = "23505"
    mock_client.table.side_effect = mock_error

    # Execute and Verify
    with pytest.raises(DuplicateError):
        repository.create(mock_message_data)

def test_find_by_conversation(repository, mock_client, mock_message_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.range.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_message_data]
    mock_query.execute.return_value = mock_response

    # Execute
    messages = repository.find_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=10, offset=0)

    # Verify
    assert len(messages) == 1
    assert isinstance(messages[0], Message)
    assert messages[0].msg_id == mock_message_data["msg_id"]
    
    # Verify calls
    mock_client.table.assert_called_with("messages")
    mock_query.eq.assert_called_with("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    mock_query.order.assert_called_with("timestamp", desc=False)
    mock_query.range.assert_called_with(0, 9)

def test_create_success(repository, mock_client, mock_message_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.insert.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_message_data]
    mock_query.execute.return_value = mock_response

    # Execute
    result = repository.create(mock_message_data)

    # Verify
    assert isinstance(result, Message)
    assert result.msg_id == mock_message_data["msg_id"]

def test_find_by_external_id(repository, mock_client, mock_message_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_message_data]
    mock_query.execute.return_value = mock_response

    # Execute
    message = repository.find_by_external_id("SM12345")

    # Verify
    assert message is not None
    assert isinstance(message, Message)
    assert message.metadata["message_sid"] == "SM12345"
    
    # Verify calls
    mock_query.eq.assert_called_with("metadata->>message_sid", "SM12345")

def test_find_by_external_id_not_found(repository, mock_client):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = []
    mock_query.execute.return_value = mock_response

    # Execute
    message = repository.find_by_external_id("SM_NOT_FOUND")

    # Verify
    assert message is None

def test_find_recent_by_conversation(repository, mock_client, mock_message_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    # Return 2 messages
    mock_response.data = [mock_message_data, mock_message_data]
    mock_query.execute.return_value = mock_response

    # Execute
    messages = repository.find_recent_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=5)

    # Verify
    assert len(messages) == 2
    # The method reverses the list
    assert isinstance(messages[0], Message)
    
    # Verify calls
    mock_query.order.assert_called_with("timestamp", desc=True)
    mock_query.limit.assert_called_with(5)

def test_find_user_messages(repository, mock_client, mock_message_data):
    # Setup mock chain
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.data = [mock_message_data]
    mock_query.execute.return_value = mock_response

    # Execute
    messages = repository.find_user_messages("01ARZ3NDEKTSV4RRFFQ69G5FAV", limit=50)

    # Verify
    assert len(messages) == 1
    assert messages[0].message_owner == MessageOwner.USER.value
    
    # Verify calls
    # Note: order of eq calls might vary
    mock_query.eq.assert_any_call("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")
    mock_query.eq.assert_any_call("message_owner", MessageOwner.USER.value)
    mock_query.order.assert_called_with("timestamp", desc=False)
    mock_query.limit.assert_called_with(50)

def test_count_by_conversation(repository, mock_client):
    # Setup mock chain for count
    mock_query = MagicMock()
    mock_client.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    
    mock_response = MagicMock()
    mock_response.count = 42
    mock_query.execute.return_value = mock_response

    # Execute
    count = repository.count_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")

    # Verify
    assert count == 42
    
    # Verify calls
    mock_query.select.assert_called_with("*", count="exact")
    mock_query.eq.assert_called_with("conv_id", "01ARZ3NDEKTSV4RRFFQ69G5FAV")

def test_find_by_conversation_error(repository, mock_client):
    mock_client.table.side_effect = Exception("Supabase Error")
    with pytest.raises(Exception):
        repository.find_by_conversation("conv_id")

def test_find_by_external_id_error(repository, mock_client):
    mock_client.table.side_effect = Exception("Supabase Error")
    with pytest.raises(Exception):
        repository.find_by_external_id("SM123")

def test_find_recent_by_conversation_error(repository, mock_client):
    mock_client.table.side_effect = Exception("Supabase Error")
    with pytest.raises(Exception):
        repository.find_recent_by_conversation("conv_id")

def test_find_user_messages_error(repository, mock_client):
    mock_client.table.side_effect = Exception("Supabase Error")
    with pytest.raises(Exception):
        repository.find_user_messages("conv_id")
