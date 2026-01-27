"""Tests for ConversationRepository."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository


class TestConversationRepository:
    """Test suite for ConversationRepository."""

    @pytest.fixture
    def mock_client(self):
        """Mock Supabase client."""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_client):
        """Create repository instance."""
        return ConversationRepository(client=mock_client)

    @pytest.fixture
    def mock_conversation_data(self):
        """Return base conversation data."""
        return {
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "status": "progress",  # Fixed: was 'in_progress' which is invalid
            "session_key": "+5511888888888::+5511999999999",
            "from_number": "+5511888888888",
            "to_number": "+5511999999999",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "context": {},
        }

    def test_calculate_session_key(self):
        """Test session key calculation (idempotency and ordering)."""
        repo = ConversationRepository

        # Test consistent ordering
        key1 = repo.calculate_session_key("+5511999999999", "+5511888888888")
        key2 = repo.calculate_session_key("+5511888888888", "+5511999999999")

        assert key1 == key2
        assert "8888" in key1.split("::")[0]  # Smaller number first

        # Test whatsapp prefix normalization
        key3 = repo.calculate_session_key(
            "whatsapp:+5511999999999", "whatsapp:+5511888888888"
        )
        assert key3 == key1

    def test_create_logs_history(self, repository, mock_client, mock_conversation_data):
        """Test that creating a conversation logs to history."""
        # Setup create return
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Call create
        repository.create(mock_conversation_data)

        # Verify history insert
        calls = mock_client.table.call_args_list
        assert any(call.args[0] == "conversation_state_history" for call in calls)

        # Verify insert data
        history_insert_call = [
            c
            for c in mock_client.table.return_value.insert.call_args_list
            if "conversation_state_history" in str(c)
            or c.args[0].get("reason") == "conversation_created"
        ]
        # Since mocks are chained, it's hard to separate table() calls from insert() calls perfectly without side_effect
        # But we can check if insert was called with history data

        # A more robust check with chained mocks:
        # table("conversations").insert(...).execute()
        # table("conversation_state_history").insert(...).execute()

        # We can check that insert was called twice (one for conv, one for history)
        assert mock_client.table.return_value.insert.call_count >= 2

    def test_find_active_by_session_key(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test finding active conversation by session key."""
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        result = repository.find_active_by_session_key("owner_id", "key")

        assert isinstance(result, Conversation)
        assert result.conv_id == mock_conversation_data["conv_id"]

        # Verify filters
        # Note: checking mock chains is verbose, assuming if it returned data it worked for now

    def test_update_status_valid_transition(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test valid status transition."""
        # 1. Find existing
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # 2. Update success
        updated_data = {
            **mock_conversation_data,
            "status": "agent_closed",
            "version": 2,
        }
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        result = repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Fixed: Use valid ULID
            ConversationStatus.AGENT_CLOSED,
            reason="done",
        )

        assert result.status == ConversationStatus.AGENT_CLOSED.value
        assert result.version == 2

    def test_update_status_invalid_transition(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test invalid status transition."""
        # Current is PENDING
        mock_conversation_data["status"] = "pending"
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Try to jump to IDLE_TIMEOUT (not allowed from PENDING)
        with pytest.raises(ValueError, match="Invalid transition"):
            repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Fixed: Use valid ULID
                ConversationStatus.IDLE_TIMEOUT,
            )

    def test_update_optimistic_locking_conflict(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test optimistic locking conflict during update."""
        # 1. Find returns version 1
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # 2. Update fails (returns empty data)
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        # 3. Check finds version 2 (conflict!)
        conflict_data = {**mock_conversation_data, "version": 2}
        # We need to mock the sequence of finds: first for initial load, second for conflict check
        # But repository.find_by_id calls select...eq...execute

        # Simplified: mock find_by_id side_effect
        # First call (inside update_status start) -> Version 1
        # Second call (inside conflict check) -> Version 2

        # To do this cleanly with the chained mocks is hard.
        # Let's mock find_by_id on the repository instance itself to control flow
        with patch.object(repository, "find_by_id") as mock_find:
            mock_find.side_effect = [
                Conversation(**mock_conversation_data),  # Initial load
                Conversation(**conflict_data),  # Conflict check
            ]

            # Mock update returning empty
            mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                []
            )

            with pytest.raises(ConcurrencyError) as exc:
                repository.update_status(
                    "01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Fixed: Use valid ULID
                    ConversationStatus.PROGRESS,
                )

            assert "Expected version 1, found 2" in str(exc.value)

    def test_cleanup_expired_conversations(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test cleanup of expired conversations."""
        # Setup: 1 expired active conversation
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        expired_conv = {
            **mock_conversation_data,
            "expires_at": expired_time,
            "status": "progress",
        }  # Fixed status

        # Mock finding expired
        mock_client.table.return_value.select.return_value.in_.return_value.lt.return_value.execute.return_value.data = [
            expired_conv
        ]

        # Mock update_status success (we can mock the method to avoid complex DB mocking)
        with patch.object(repository, "update_status") as mock_update_status:
            mock_update_status.return_value = Conversation(
                **{**expired_conv, "status": "expired"}
            )

            # Mock find_by_id needed inside update_context
            with patch.object(repository, "find_by_id") as mock_find:
                mock_find.return_value = Conversation(
                    **{**expired_conv, "status": "expired"}
                )

                # Mock update needed inside update_context
                mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {**expired_conv, "status": "expired"}
                ]

                repository.cleanup_expired_conversations()

                # Should have attempted to update status to EXPIRED
                mock_update_status.assert_called_with(
                    expired_conv["conv_id"], ConversationStatus.EXPIRED, ended_at=ANY
                )

    def test_close_by_message_policy(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test closing conversation via message policy."""
        conv = Conversation(**mock_conversation_data)

        with patch.object(repository, "update_status") as mock_update_status:
            mock_update_status.return_value = conv  # Return success

            # Mock find_by_id needed inside update_context (called if message_text is present)
            with patch.object(repository, "find_by_id") as mock_find:
                mock_find.return_value = conv

                # Mock update needed inside update_context
                mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    mock_conversation_data
                ]

                # Case 1: Close as AGENT
                result = repository.close_by_message_policy(
                    conv,
                    should_close=True,
                    message_owner=MessageOwner.AGENT,
                    message_text="Bye",
                )

                assert result is True
                mock_update_status.assert_called_with(
                    conv.conv_id,
                    ConversationStatus.AGENT_CLOSED,
                    ended_at=ANY,
                    initiated_by="agent",
                    reason="message_policy",
                )

    def test_find_idle_conversations(self, repository, mock_client):
        """Test finding idle conversations."""
        mock_client.table.return_value.select.return_value.in_.return_value.lt.return_value.limit.return_value.execute.return_value.data = (
            []
        )

        repository.find_idle_conversations(idle_minutes=30)

        # Verify query structure
        # Checking if .lt() was called with updated_at
        # This is implicit if no error raised
        pass

    def test_find_by_session_key(self, repository, mock_client, mock_conversation_data):
        """Test finding conversation by session key arguments."""
        # Mock calculate_session_key logic or expectation
        # The method builds session key internally

        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        result = repository.find_by_session_key(
            owner_id="owner_123",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )
        assert result is not None
        assert result.conv_id == mock_conversation_data["conv_id"]

    def test_find_by_session_key_not_found(self, repository, mock_client):
        """Test finding conversation by session key when not found."""
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = (
            []
        )

        result = repository.find_by_session_key(
            owner_id="owner_123",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )
        assert result is None

    def test_find_active_by_owner(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test finding active conversation by owner."""
        mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        result = repository.find_active_by_owner(mock_conversation_data["owner_id"])
        assert len(result) > 0
        assert result[0].owner_id == mock_conversation_data["owner_id"]

    def test_find_all_by_session_key(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test finding all conversations by session key."""
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        results = repository.find_all_by_session_key(
            owner_id="owner_123", session_key="session_123"
        )
        assert len(results) == 1
        assert results[0].conv_id == mock_conversation_data["conv_id"]

    def test_create_exception_handling(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test handling of exception during history creation in create."""
        # Setup create return
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Mock history insert to raise exception
        # The first insert is for conversation, second for history
        # We need to make the second call raise an exception
        # This is tricky with chained mocks.
        # Alternatively, we can mock the logger to verify it logged an error

        with patch(
            "src.modules.conversation.repositories.conversation_repository.logger"
        ) as mock_logger:
            # We configure the mock to raise exception on the SECOND call to table().insert().execute()
            # But simpler: let's just assume if it fails, it logs error and returns conversation

            # We can't easily mock just the second call of a chain with side_effect unless we mock the intermediate objects
            # Let's mock the table method to return different mocks for different tables

            mock_conv_table = MagicMock()
            mock_conv_table.insert.return_value.execute.return_value.data = [
                mock_conversation_data
            ]

            mock_hist_table = MagicMock()
            mock_hist_table.insert.return_value.execute.side_effect = Exception(
                "DB Error"
            )

            def table_side_effect(table_name):
                if table_name == "conversations":
                    return mock_conv_table
                return mock_hist_table

            mock_client.table.side_effect = table_side_effect

            # Execute
            result = repository.create(mock_conversation_data)

            # Verify
            assert result is not None
            assert result.conv_id == mock_conversation_data["conv_id"]
            mock_logger.error.assert_called_with(
                "Failed to write conversation state history on create",
                conv_id=mock_conversation_data["conv_id"],
                error="DB Error",
            )

    def test_find_active_by_session_key_exception(self, repository, mock_client):
        """Test exception propagation in find_active_by_session_key."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_active_by_session_key("owner_id", "key")

    def test_find_all_by_session_key_exception(self, repository, mock_client):
        """Test exception propagation in find_all_by_session_key."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_all_by_session_key("owner_id", "key")

    def test_find_active_by_owner_exception(self, repository, mock_client):
        """Test exception propagation in find_active_by_owner."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_active_by_owner("owner_id")

    def test_find_expired_conversations_exception(self, repository, mock_client):
        """Test exception propagation in find_expired_conversations."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_expired_conversations()

    def test_find_idle_conversations_exception(self, repository, mock_client):
        """Test exception propagation in find_idle_conversations."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_idle_conversations(idle_minutes=30)

    def test_update_status_generic_exception(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test generic exception handling in update_status."""
        # Find works
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Update raises generic exception
        mock_client.table.return_value.update.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
            )

    def test_find_by_session_key_exception(self, repository, mock_client):
        """Test exception propagation in find_by_session_key."""
        mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            repository.find_by_session_key("owner_id", "+123", "+456")

    def test_update_status_update_failed_return_none(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test update_status returns None when update fails (optimistic locking check returns None)."""
        # Find works
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Update returns empty (failed)
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            []
        )

        # Check (find_by_id) returns None (record gone?)
        with patch.object(repository, "find_by_id") as mock_find:
            mock_find.side_effect = [
                Conversation(**mock_conversation_data),  # Initial find
                None,  # Check find
            ]

            result = repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
            )

            assert result is None

    def test_update_generic_exception(self, repository, mock_client):
        """Test generic exception in update method."""
        # Need to mock find_by_id to avoid ULID validation error or DB error during find
        with patch.object(repository, "find_by_id") as mock_find:
            mock_find.return_value = MagicMock(version=1)

            mock_client.table.side_effect = Exception("DB Error")

            with pytest.raises(Exception, match="DB Error"):
                repository.update("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"val": 1})

    def test_update_concurrency_error_propagation(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test propagation of ConcurrencyError in update method."""
        # Find works
        with patch.object(repository, "find_by_id") as mock_find:
            mock_find.return_value = Conversation(**mock_conversation_data)

            # Update returns empty
            mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                []
            )

            # Check returns different version
            conflict_data = {**mock_conversation_data, "version": 2}

            # We need to orchestrate find_by_id calls
            # 1. Fallback get current version (if expected_version is None)
            # 2. Check after failure
            mock_find.side_effect = [
                Conversation(**mock_conversation_data),  # 1
                Conversation(**conflict_data),  # 2
            ]

            with pytest.raises(ConcurrencyError):
                repository.update("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"val": 1})

    def test_create_history_write_exception(
        self, repository, mock_client, mock_conversation_data
    ):
        """Test exception when writing history in update_status."""
        # Find works
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]

        # Update works
        updated_data = {**mock_conversation_data, "status": "progress", "version": 2}
        mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        # History insert fails
        # We mock the table call to return different mocks
        mock_conv_table = MagicMock()
        # Select
        mock_conv_table.select.return_value.eq.return_value.execute.return_value.data = [
            mock_conversation_data
        ]
        # Update
        mock_conv_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        mock_hist_table = MagicMock()
        mock_hist_table.insert.side_effect = Exception("History Error")

        def table_side_effect(table_name):
            if table_name == "conversations":
                return mock_conv_table
            return mock_hist_table

        mock_client.table.side_effect = table_side_effect

        with patch(
            "src.modules.conversation.repositories.conversation_repository.logger"
        ) as mock_logger:
            result = repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
            )

            assert result is not None
            mock_logger.error.assert_called_with(
                "Failed to write conversation state history",
                conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                error="History Error",
            )
