import pytest
from unittest.mock import MagicMock, ANY, patch
from datetime import datetime, timezone
from src.modules.conversation.repositories.impl.postgres.conversation_repository import PostgresConversationRepository
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.core.utils.exceptions import ConcurrencyError

class TestPostgresConversationRepository:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        # Mock connection context manager
        conn = MagicMock()
        db.connection.return_value.__enter__.return_value = conn
        
        # Mock cursor: NOT used as context manager in PostgresRepository
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        
        return db

    @pytest.fixture
    def repository(self, mock_db):
        return PostgresConversationRepository(mock_db)

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

    def test_create(self, repository, mock_db, mock_conversation_data):
        # Mock the execute for create (INSERT)
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_conversation_data

        result = repository.create(mock_conversation_data)
        
        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]
        
        # Verify calls:
        # 1. INSERT into conversations
        # 2. INSERT into conversation_state_history (log_transition_history)
        assert cursor.execute.call_count >= 2
        
        # Check history insert
        history_call = cursor.execute.call_args_list[1]
        query_str = str(history_call[0][0]) # simplified check
        assert "conversation_state_history" in query_str or "conversation_state_history" in str(history_call)

    def test_find_by_session_key(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_conversation_data
        
        result = repository.find_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "+123", "+456")
        
        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]
        
        # Check query
        assert cursor.execute.called

    def test_find_active_by_owner(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_conversation_data]
        
        result = repository.find_active_by_owner("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)

    def test_update_status(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        # 1. find_by_id (initial load)
        # 2. update (perform update)
        # 3. _log_history (insert history)
        
        updated_data = mock_conversation_data.copy()
        updated_data["status"] = "agent_closed"
        updated_data["version"] = 2
        
        cursor.fetchone.side_effect = [
            mock_conversation_data, # find_by_id
            updated_data # update returning clause
        ]
        
        result = repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.AGENT_CLOSED,
            reason="done"
        )
        
        assert result is not None
        assert result.status == "agent_closed"
        assert result.version == 2
        
    def test_find_expired_candidates(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_conversation_data]
        
        result = repository.find_expired_candidates()
        assert len(result) == 1

    def test_cleanup_expired_conversations(self, repository, mock_db, mock_conversation_data):
        # This calls find_expired_candidates -> update_status
        # We need to mock find_expired_candidates to return one conv
        # And update_status to return success
        
        with patch.object(repository, 'find_expired_candidates') as mock_find:
            mock_find.return_value = [Conversation(**mock_conversation_data)]
            
            with patch.object(repository, 'update_status') as mock_update:
                mock_update.return_value = Conversation(**mock_conversation_data)
                
                count = repository.cleanup_expired_conversations()
                
                assert count == 1
                mock_update.assert_called_once()

    def test_find_active_by_session_key(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_conversation_data
        
        result = repository.find_active_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "whatsapp:+123::whatsapp:+456")
        
        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]
        assert cursor.execute.called

    def test_find_all_by_session_key(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_conversation_data, mock_conversation_data]
        
        result = repository.find_all_by_session_key("01ARZ3NDEKTSV4RRFFQ69G5FAV", "whatsapp:+123::whatsapp:+456")
        
        assert len(result) == 2
        assert isinstance(result[0], Conversation)
        assert cursor.execute.called

    def test_find_idle_candidates(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_conversation_data]
        
        result = repository.find_idle_candidates("2023-01-01T00:00:00+00:00")
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)
        assert cursor.execute.called

    def test_close_by_message_policy(self, repository, mock_db, mock_conversation_data):
        conv = Conversation(**mock_conversation_data)
        
        with patch.object(repository, 'update_status') as mock_update:
            mock_update.return_value = conv
            with patch.object(repository, 'update_context') as mock_context:
                
                # Should close
                result = repository.close_by_message_policy(
                    conv, should_close=True, message_owner=MessageOwner.USER
                )
                assert result is True
                mock_update.assert_called()
                
                # Should not close
                result = repository.close_by_message_policy(
                    conv, should_close=False, message_owner=MessageOwner.USER
                )
                assert result is False

    def test_find_by_status(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchall.return_value = [mock_conversation_data]
        
        result = repository.find_by_status(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            status=ConversationStatus.PROGRESS
        )
        
        assert len(result) == 1
        assert isinstance(result[0], Conversation)
        assert cursor.execute.called

    def test_update_context(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        updated_data = mock_conversation_data.copy()
        updated_data["context"] = {"foo": "bar"}
        cursor.fetchone.return_value = updated_data
        
        result = repository.update_context("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"foo": "bar"})
        
        assert result.context == {"foo": "bar"}
        assert cursor.execute.called

    def test_update_timestamp(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        cursor.fetchone.return_value = mock_conversation_data
        
        result = repository.update_timestamp("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        
        assert result is not None
        assert cursor.execute.called

    def test_update_status_concurrency_error(self, repository, mock_db, mock_conversation_data):
        cursor = mock_db.connection.return_value.__enter__.return_value.cursor.return_value
        
        # find_by_id returns current
        cursor.fetchone.side_effect = [
            mock_conversation_data, # find_by_id (initial)
            None, # update (returns None if no rows updated due to version mismatch logic in DB usually, but here repository checks version after)
            mock_conversation_data # find_by_id (check after)
        ]
        
        # If update returns None, the repository logic tries to find_by_id again to check version
        # Let's simulate that the update returns None (not updated)
        # And then the subsequent find_by_id returns a record with different version
        
        current_data = mock_conversation_data.copy()
        current_data["version"] = 1
        
        updated_data_db = mock_conversation_data.copy()
        updated_data_db["version"] = 2 # Different version in DB
        
        # Reset side effect for more precise control
        # 1. find_by_id -> returns current
        # 2. update -> returns None (simulating update failure or empty result if using RETURNING)
        # But wait, PostgresRepository.update implementation usually returns None if 0 rows affected.
        # However, to test ConcurrencyError in update_status, we need to reach lines 382+
        
        # Mocking update to return None
        with patch.object(repository, 'update', return_value=None):
             # Mocking find_by_id to return current first, then updated version later
             with patch.object(repository, 'find_by_id') as mock_find:
                 mock_find.side_effect = [
                     Conversation(**current_data), # Initial fetch
                     Conversation(**updated_data_db) # Fetch after update fail
                 ]
                 
                 with pytest.raises(ConcurrencyError):
                     repository.update_status(
                        "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                        ConversationStatus.AGENT_CLOSED
                     )
