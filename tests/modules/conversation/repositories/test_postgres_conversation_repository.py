import pytest
from unittest.mock import MagicMock, ANY, patch
from datetime import datetime, timezone
from src.modules.conversation.repositories.impl.postgres.conversation_repository import PostgresConversationRepository
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus

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
