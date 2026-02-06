import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from src.modules.conversation.repositories.impl.postgres.message_repository import PostgresMessageRepository
from src.modules.conversation.models.message import Message
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.enums.message_direction import MessageDirection

@pytest.mark.asyncio
class TestPostgresMessageRepository:
    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_db):
        repo = PostgresMessageRepository(mock_db)
        repo._execute_query = AsyncMock()
        # Mock super().create
        # Since super().create calls self.db.execute usually, or self._execute_query if overriden?
        # PostgresAsyncRepository.create likely calls _execute_query or db directly.
        # Let's mock create directly for creation test or patch super().create
        return repo

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

    async def test_create(self, repository, mock_message_data):
        with patch("src.core.database.postgres_async_repository.PostgresAsyncRepository.create", new_callable=AsyncMock) as mock_super_create:
            mock_super_create.return_value = Message(**mock_message_data)
            
            result = await repository.create(mock_message_data)
            
            assert isinstance(result, Message)
            assert result.msg_id == mock_message_data["msg_id"]
            mock_super_create.assert_called_once()

    async def test_find_by_conversation(self, repository, mock_message_data):
        repository._execute_query.return_value = [mock_message_data]
        
        result = await repository.find_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)
        repository._execute_query.assert_called()
        
    async def test_count_by_conversation(self, repository):
        repository._execute_query.return_value = {"count": 42}
        
        result = await repository.count_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result == 42
        
    async def test_find_recent_by_conversation(self, repository, mock_message_data):
        msg1 = mock_message_data.copy()
        msg2 = mock_message_data.copy()
        msg2["msg_id"] = "01ARZ3NDEKTSV4RRFFQ69G5FAW"
        
        # Mock returns in descending order (newest first)
        repository._execute_query.return_value = [msg2, msg1]
        
        result = await repository.find_recent_by_conversation("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 2
        # Method reverses the list to chronological order
        assert result[0].msg_id == msg1["msg_id"]
        assert result[1].msg_id == msg2["msg_id"]
        
    async def test_find_by_external_id(self, repository, mock_message_data):
        repository._execute_query.return_value = mock_message_data
        
        result = await repository.find_by_external_id("sid_123")
        
        assert isinstance(result, Message)
        assert result.msg_id == mock_message_data["msg_id"]

    async def test_find_user_messages(self, repository, mock_message_data):
        repository._execute_query.return_value = [mock_message_data]
        
        result = await repository.find_user_messages("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Message)
