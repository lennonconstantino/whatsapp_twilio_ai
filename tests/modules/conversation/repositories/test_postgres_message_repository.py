import pytest
from unittest.mock import MagicMock, ANY
from datetime import datetime, timezone
from psycopg2.extras import Json
from src.modules.conversation.repositories.impl.postgres.message_repository import PostgresMessageRepository
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.enums.message_direction import MessageDirection

class TestPostgresMessageRepository:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        conn = MagicMock()
        db.connection.return_value.__enter__.return_value = conn
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return PostgresMessageRepository(mock_db)

    @pytest.fixture
    def mock_message_data(self):
        return {
            "msg_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "body": "Hello",
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456",
            "message_type": MessageType.TEXT,
            "message_owner": MessageOwner.USER,
            "direction": MessageDirection.INBOUND,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {"sid": "123"},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_create(self, repository, mock_db, mock_message_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_message_data

        result = repository.create(mock_message_data)
        
        assert isinstance(result, Message)
        assert result.msg_id == mock_message_data["msg_id"]
        assert cursor.execute.called

    def test_find_by_conversation(self, repository, mock_db, mock_message_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_message_data]
        
        result = repository.find_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)
        
    def test_count_by_conversation(self, repository, mock_db):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = {"count": 42}
        
        result = repository.count_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result == 42
        
    def test_find_recent_by_conversation(self, repository, mock_db, mock_message_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        # Mock returning 2 messages
        msg1 = mock_message_data.copy()
        msg2 = mock_message_data.copy()
        msg2["msg_id"] = "01ARZ3NDEKTSV4RRFFQ69G5FAW"
        
        cursor.fetchall.return_value = [msg1, msg2]
        
        result = repository.find_recent_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 2
        # Should be reversed
        assert result[0].msg_id == msg2["msg_id"]
        assert result[1].msg_id == msg1["msg_id"]
        
    def test_find_by_external_id(self, repository, mock_db, mock_message_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_message_data
        
        result = repository.find_by_external_id("sid_123")
        
        assert isinstance(result, Message)
