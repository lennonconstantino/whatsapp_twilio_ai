import pytest
from unittest.mock import MagicMock, ANY, patch, AsyncMock
from datetime import datetime, timezone
from src.modules.conversation.repositories.impl.postgres.conversation_repository import PostgresConversationRepository
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.core.utils.exceptions import ConcurrencyError

@pytest.mark.asyncio
class TestPostgresConversationRepository:
    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_db):
        repo = PostgresConversationRepository(mock_db)
        repo._execute_query = AsyncMock()
        repo.find_by_id = AsyncMock() # Mock find_by_id for update logic
        repo.update = AsyncMock() # Mock update for update logic
        repo.create = AsyncMock(wraps=repo.create) # Keep create logic but allow mocking super().create if needed
        # Actually better to mock _execute_query and let create logic run
        # But create calls super().create which calls _execute_query
        return repo

    @pytest.fixture
    def mock_conversation_data(self):
        return {
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "status": "progress",
            "session_key": "whatsapp:+123::whatsapp:+456",
            "from_number": "whatsapp:+123",
            "to_number": "whatsapp:+456",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "context": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_calculate_session_key(self):
        repo = PostgresConversationRepository
        key = repo.calculate_session_key("+123", "+456")
        assert key == "whatsapp:+123::whatsapp:+456"
        
        key2 = repo.calculate_session_key("whatsapp:+456", "whatsapp:+123")
        assert key2 == "whatsapp:+123::whatsapp:+456"

    async def test_create(self, repository, mock_conversation_data):
        # We need to mock super().create or just _execute_query if super().create uses it.
        # Since we cannot easily mock super() call, we rely on _execute_query mock if possible.
        # But PostgresAsyncRepository.create likely calls _execute_query.
        
        # Let's mock create directly to simplify, or rely on internal implementation.
        # PostgresConversationRepository.create does extra logic (log history)
        
        # Mocking super().create logic via side_effect or patching is hard on instance.
        # Let's patch PostgresAsyncRepository.create
        
        with patch("src.core.database.postgres_async_repository.PostgresAsyncRepository.create", new_callable=AsyncMock) as mock_super_create:
            mock_super_create.return_value = Conversation(**mock_conversation_data)
            
            result = await repository.create(mock_conversation_data)
            
            assert isinstance(result, Conversation)
            assert result.conv_id == mock_conversation_data["conv_id"]
            
            # Verify history logging called
            # It calls self.log_transition_history -> _log_history -> _execute_query
            assert repository._execute_query.called
            args = repository._execute_query.call_args[0]
            assert "conversation_state_history" in str(args[0])

    async def test_find_by_session_key(self, repository, mock_conversation_data):
        repository._execute_query.return_value = mock_conversation_data
        
        result = await repository.find_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "+123", "+456")
        
        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]
        assert repository._execute_query.called

    async def test_find_active_by_owner(self, repository, mock_conversation_data):
        repository._execute_query.return_value = [mock_conversation_data]
        
        result = await repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)

    async def test_update_status(self, repository, mock_conversation_data):
        # 1. find_by_id (initial load) -> Mocked
        # 2. update (perform update) -> Mocked
        # 3. _log_history -> _execute_query
        
        updated_data = mock_conversation_data.copy()
        updated_data["status"] = "agent_closed"
        updated_data["version"] = 2
        
        repository.find_by_id.return_value = Conversation(**mock_conversation_data)
        repository.update.return_value = Conversation(**updated_data)
        
        result = await repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.AGENT_CLOSED,
            reason="done"
        )
        
        assert result is not None
        assert result.status == "agent_closed"
        assert result.version == 2
        
        # Verify history log
        assert repository._execute_query.called
        
    async def test_find_expired_candidates(self, repository, mock_conversation_data):
        repository._execute_query.return_value = [mock_conversation_data]
        
        result = await repository.find_expired_candidates()
        assert len(result) == 1

    async def test_cleanup_expired_conversations(self, repository, mock_conversation_data):
        with patch.object(repository, 'find_expired_candidates', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = [Conversation(**mock_conversation_data)]
            
            with patch.object(repository, 'update_status', new_callable=AsyncMock) as mock_update:
                mock_update.return_value = Conversation(**mock_conversation_data)
                
                count = await repository.cleanup_expired_conversations()
                
                assert count == 1
                mock_update.assert_called_once()

    async def test_find_active_by_session_key(self, repository, mock_conversation_data):
        repository._execute_query.return_value = mock_conversation_data
        
        result = await repository.find_active_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "whatsapp:+123::whatsapp:+456")
        
        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]

    async def test_find_all_by_session_key(self, repository, mock_conversation_data):
        repository._execute_query.return_value = [mock_conversation_data, mock_conversation_data]
        
        result = await repository.find_all_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "whatsapp:+123::whatsapp:+456")
        
        assert len(result) == 2
        assert isinstance(result[0], Conversation)

    async def test_find_idle_candidates(self, repository, mock_conversation_data):
        repository._execute_query.return_value = [mock_conversation_data]
        
        result = await repository.find_idle_candidates("2023-01-01T00:00:00+00:00")
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)

    async def test_close_by_message_policy(self, repository, mock_conversation_data):
        conv = Conversation(**mock_conversation_data)
        
        with patch.object(repository, 'update_status', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = conv
            with patch.object(repository, 'update_context', new_callable=AsyncMock) as mock_context:
                
                # Should close
                result = await repository.close_by_message_policy(
                    conv, should_close=True, message_owner=MessageOwner.USER
                )
                assert result is True
                mock_update.assert_called()
                
                # Should not close
                result = await repository.close_by_message_policy(
                    conv, should_close=False, message_owner=MessageOwner.USER
                )
                assert result is False

    async def test_find_by_status(self, repository, mock_conversation_data):
        repository._execute_query.return_value = [mock_conversation_data]
        
        result = await repository.find_by_status(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            status=ConversationStatus.PROGRESS
        )
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)

    async def test_update_context(self, repository, mock_conversation_data):
        updated_data = mock_conversation_data.copy()
        updated_data["context"] = {"foo": "bar"}
        repository.update.return_value = Conversation(**updated_data)
        
        result = await repository.update_context("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"foo": "bar"})
        
        assert result.context == {"foo": "bar"}
        repository.update.assert_called()

    async def test_update_timestamp(self, repository, mock_conversation_data):
        repository.update.return_value = Conversation(**mock_conversation_data)
        
        result = await repository.update_timestamp("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result is not None
        repository.update.assert_called()

    async def test_update_status_concurrency_error(self, repository, mock_conversation_data):
        current_data = mock_conversation_data.copy()
        current_data["version"] = 1
        
        updated_data_db = mock_conversation_data.copy()
        updated_data_db["version"] = 2 # Different version in DB
        
        # 1. find_by_id -> returns current
        # 2. update -> returns None (simulating update failure)
        # 3. find_by_id -> returns updated version (triggering ConcurrencyError)
        
        repository.update.return_value = None
        repository.find_by_id.side_effect = [
            Conversation(**current_data), # Initial fetch
            Conversation(**updated_data_db) # Fetch after update fail
        ]
        
        with pytest.raises(ConcurrencyError):
            await repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.AGENT_CLOSED
            )
