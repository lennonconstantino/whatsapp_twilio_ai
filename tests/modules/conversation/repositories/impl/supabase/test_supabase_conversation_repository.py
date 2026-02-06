"""Tests for ConversationRepository."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import ANY, MagicMock, Mock, patch, AsyncMock

import pytest

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.repositories.impl.supabase.conversation_repository import \
    SupabaseConversationRepository


@pytest.mark.asyncio
class TestConversationRepository:
    """Test suite for ConversationRepository."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Mock Supabase client."""
        self.mock_client = MagicMock()
        self.repository = SupabaseConversationRepository(client=self.mock_client)
        
        self.mock_conversation_data = {
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

    async def test_find_by_status(self):
        """Test finding conversations by status."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        result = await self.repository.find_by_status(
            owner_id="owner_123",
            status=ConversationStatus.PROGRESS
        )
        assert len(result) == 1
        assert result[0].status == "progress"

    async def test_find_by_status_with_agent(self):
        """Test finding conversations by status and agent_id."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        result = await self.repository.find_by_status(
            owner_id="owner_123",
            status=ConversationStatus.PROGRESS,
            agent_id="agent_1"
        )
        assert len(result) == 1

    async def test_update_context(self):
        """Test updating context."""
        updated_data = {**self.mock_conversation_data, "context": {"new": "val"}, "version": 2}
        
        # Mock update returning data
        self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        result = await self.repository.update_context(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            {"new": "val"},
            expected_version=1
        )
        assert result.context == {"new": "val"}

    async def test_update_timestamp(self):
        """Test updating timestamp."""
        # Mock find_by_id used in update override
        with patch.object(self.repository, "find_by_id") as mock_find:
            mock_find.return_value = Conversation(**self.mock_conversation_data)
            
            # Chain: table().update().eq().execute()
            # Note: update_timestamp does not enforce version check in the update call itself (current_version=None)
            self.mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                self.mock_conversation_data
            ]

            result = await self.repository.update_timestamp("01ARZ3NDEKTSV4RRFFQ69G5FAV")
            assert result is not None

    async def test_update_status_force(self):
        """Test update status with force=True skipping validation."""
        # Current is PENDING
        self.mock_conversation_data["status"] = "pending"
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # Update success
        updated_data = {**self.mock_conversation_data, "status": "idle_timeout", "version": 2}
        self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]
        
        # Should succeed despite invalid transition PENDING -> IDLE_TIMEOUT
        result = await self.repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.IDLE_TIMEOUT,
            force=True
        )
        assert result.status == "idle_timeout"

    async def test_update_status_with_expires_at(self):
        """Test update status with expires_at."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]
        
        updated_data = {**self.mock_conversation_data, "version": 2}
        self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        result = await self.repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.PROGRESS,
            expires_at=expires_at
        )
        assert result is not None

    async def test_update_status_not_found(self):
        """Test update status when conversation not found."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        result = await self.repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            ConversationStatus.PROGRESS
        )
        assert result is None

    async def test_find_by_status_exception(self):
        """Test exception in find_by_status."""
        self.mock_client.table.side_effect = Exception("DB Error")
        with pytest.raises(Exception):
            await self.repository.find_by_status("owner", ConversationStatus.PROGRESS)

    def test_calculate_session_key(self):
        """Test session key calculation (idempotency and ordering)."""
        repo = SupabaseConversationRepository

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

    async def test_create_logs_history(self):
        """Test that creating a conversation logs to history."""
        # Setup create return
        self.mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # Call create
        await self.repository.create(self.mock_conversation_data)

        # Verify history insert
        calls = self.mock_client.table.call_args_list
        assert any(call.args[0] == "conversation_state_history" for call in calls)

        # Verify insert data
        assert self.mock_client.table.return_value.insert.call_count >= 2

    async def test_find_active_by_session_key(self):
        """Test finding active conversation by session key."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        result = await self.repository.find_active_by_session_key("owner_id", "key")

        assert isinstance(result, Conversation)
        assert result.conv_id == self.mock_conversation_data["conv_id"]

    async def test_update_status_valid_transition(self):
        """Test valid status transition."""
        # 1. Find existing
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # 2. Update success
        updated_data = {
            **self.mock_conversation_data,
            "status": "agent_closed",
            "version": 2,
        }
        self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        result = await self.repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Fixed: Use valid ULID
            ConversationStatus.AGENT_CLOSED,
            reason="done",
        )

        assert result.status == ConversationStatus.AGENT_CLOSED.value
        assert result.version == 2

    async def test_update_status_invalid_transition(self):
        """Test invalid status transition."""
        # Current is PENDING
        self.mock_conversation_data["status"] = "pending"
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # Try to jump to IDLE_TIMEOUT (not allowed from PENDING)
        with pytest.raises(ValueError, match="Invalid transition"):
            await self.repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Fixed: Use valid ULID
                ConversationStatus.IDLE_TIMEOUT,
            )

    async def test_update_optimistic_locking_conflict(self):
        """Test optimistic locking conflict during update."""
        # Setup mocks for the sequence of calls
        
        # 1. First find_by_id call (initial load)
        mock_find_resp_1 = MagicMock()
        mock_find_resp_1.data = [self.mock_conversation_data]
        
        # 2. Update call (fails/empty)
        mock_update_resp = MagicMock()
        mock_update_resp.data = []
        
        # 3. Second find_by_id call (conflict check)
        conflict_data = {**self.mock_conversation_data, "version": 2}
        mock_find_resp_2 = MagicMock()
        mock_find_resp_2.data = [conflict_data]

        # Configure mocks
        # We need to distinguish select vs update chains.
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        
        # Setup select chain for find_by_id
        mock_query.select.return_value.eq.return_value.execute.side_effect = [
            mock_find_resp_1,
            mock_find_resp_2
        ]
        
        # Setup update chain
        mock_query.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update_resp

        with pytest.raises(ConcurrencyError) as exc:
            await self.repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                ConversationStatus.PROGRESS,
            )

        assert "Expected version 1, found 2" in str(exc.value)

    async def test_cleanup_expired_conversations(self):
        """Test cleanup of expired conversations."""
        # Setup: 1 expired active conversation
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        expired_conv = {
            **self.mock_conversation_data,
            "expires_at": expired_time,
            "status": "progress",
        }  # Fixed status

        # Mock finding expired
        self.mock_client.table.return_value.select.return_value.in_.return_value.lt.return_value.limit.return_value.execute.return_value.data = [
            expired_conv
        ]

        # Mock update_status success (we can mock the method to avoid complex DB mocking)
        with patch.object(self.repository, "update_status") as mock_update_status:
            mock_update_status.return_value = Conversation(
                **{**expired_conv, "status": "expired"}
            )

            with patch.object(self.repository, "find_by_id") as mock_find:
                mock_find.return_value = Conversation(
                    **{**expired_conv, "status": "expired"}
                )
                
                # Mock update needed inside update_context
                self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {**expired_conv, "status": "expired"}
                ]

                await self.repository.cleanup_expired_conversations()

                # Should have attempted to update status to EXPIRED
                mock_update_status.assert_called_with(
                    expired_conv["conv_id"],
                    ConversationStatus.EXPIRED,
                    ended_at=ANY,
                    initiated_by="system",
                    reason="ttl_expired",
                )

    async def test_close_by_message_policy(self):
        """Test closing conversation via message policy."""
        conv = Conversation(**self.mock_conversation_data)

        with patch.object(self.repository, "update_status") as mock_update_status:
            mock_update_status.return_value = conv  # Return success

            with patch.object(self.repository, "find_by_id") as mock_find:
                mock_find.return_value = conv

                # Mock update needed inside update_context
                self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    self.mock_conversation_data
                ]
                self.mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
                    self.mock_conversation_data
                ]

                # Case 1: Close as AGENT
                result = await self.repository.close_by_message_policy(
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

    async def test_find_idle_conversations(self):
        """Test finding idle conversations."""
        self.mock_client.table.return_value.select.return_value.in_.return_value.lt.return_value.limit.return_value.execute.return_value.data = (
            []
        )

        await self.repository.find_idle_conversations(idle_minutes=30)

    async def test_find_by_session_key(self):
        """Test finding conversation by session key arguments."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        result = await self.repository.find_by_session_key(
            owner_id="owner_123",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )
        assert result is not None
        assert result.conv_id == self.mock_conversation_data["conv_id"]

    async def test_find_by_session_key_not_found(self):
        """Test finding conversation by session key when not found."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.in_.return_value.limit.return_value.execute.return_value.data = (
            []
        )

        result = await self.repository.find_by_session_key(
            owner_id="owner_123",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )
        assert result is None

    async def test_find_active_by_owner(self):
        """Test finding active conversation by owner."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        result = await self.repository.find_active_by_owner(self.mock_conversation_data["owner_id"])
        assert len(result) > 0
        assert result[0].owner_id == self.mock_conversation_data["owner_id"]

    async def test_find_all_by_session_key(self):
        """Test finding all conversations by session key."""
        self.mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        results = await self.repository.find_all_by_session_key(
            owner_id="owner_123", session_key="session_123"
        )
        assert len(results) == 1
        assert results[0].conv_id == self.mock_conversation_data["conv_id"]

    async def test_create_exception_handling(self):
        """Test handling of exception during history creation in create."""
        # Setup create return
        self.mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        mock_conv_table = MagicMock()
        mock_conv_table.insert.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        mock_hist_table = MagicMock()
        mock_hist_table.insert.return_value.execute.side_effect = Exception(
            "DB Error"
        )

        def table_side_effect(table_name):
            if table_name == "conversations":
                return mock_conv_table
            return mock_hist_table

        self.mock_client.table.side_effect = table_side_effect

        with patch(
            "src.modules.conversation.repositories.impl.supabase.conversation_repository.logger"
        ) as mock_logger:
            result = await self.repository.create(self.mock_conversation_data)

            assert result is not None
            assert result.conv_id == self.mock_conversation_data["conv_id"]
            mock_logger.error.assert_called_with(
                "Failed to write conversation state history on create",
                conv_id=self.mock_conversation_data["conv_id"],
                error="DB Error",
            )

    async def test_find_active_by_session_key_exception(self):
        """Test exception propagation in find_active_by_session_key."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_active_by_session_key("owner_id", "key")

    async def test_find_all_by_session_key_exception(self):
        """Test exception propagation in find_all_by_session_key."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_all_by_session_key("owner_id", "key")

    async def test_find_active_by_owner_exception(self):
        """Test exception propagation in find_active_by_owner."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_active_by_owner("owner_id")

    async def test_find_expired_conversations_exception(self):
        """Test exception propagation in find_expired_conversations."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_expired_conversations()

    async def test_find_idle_conversations_exception(self):
        """Test exception propagation in find_idle_conversations."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_idle_conversations(idle_minutes=30)

    async def test_update_status_generic_exception(self):
        """Test generic exception handling in update_status."""
        # Find works
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # Update raises generic exception
        self.mock_client.table.return_value.update.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
            )

    async def test_find_by_session_key_exception(self):
        """Test exception propagation in find_by_session_key."""
        self.mock_client.table.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.find_by_session_key("owner_id", "+123", "+456")

    async def test_update_status_update_failed_return_none(self):
        """Test update_status returns None when update fails (optimistic locking check returns None)."""
        # 1. Initial find
        mock_find_resp_1 = MagicMock()
        mock_find_resp_1.data = [self.mock_conversation_data]
        
        # 2. Update empty
        mock_update_resp = MagicMock()
        mock_update_resp.data = []
        
        # 3. Check find returns empty (gone)
        mock_find_resp_2 = MagicMock()
        mock_find_resp_2.data = []

        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        
        mock_query.select.return_value.eq.return_value.execute.side_effect = [
            mock_find_resp_1,
            mock_find_resp_2
        ]
        mock_query.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update_resp

        result = await self.repository.update_status(
            "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
        )

        assert result is None

    async def test_update_generic_exception(self):
        """Test generic exception in update method."""
        # 1. Initial find success
        mock_find_resp = MagicMock()
        mock_find_resp.data = [self.mock_conversation_data]
        
        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        
        mock_query.select.return_value.eq.return_value.execute.return_value = mock_find_resp
        
        # 2. Update raises exception
        mock_query.update.side_effect = Exception("DB Error")

        with pytest.raises(Exception, match="DB Error"):
            await self.repository.update("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"val": 1})

    async def test_update_concurrency_error_propagation(self):
        """Test propagation of ConcurrencyError in update method."""
        # Setup mocks
        mock_find_resp_1 = MagicMock()
        mock_find_resp_1.data = [self.mock_conversation_data]
        
        mock_update_resp = MagicMock()
        mock_update_resp.data = []
        
        conflict_data = {**self.mock_conversation_data, "version": 2}
        mock_find_resp_2 = MagicMock()
        mock_find_resp_2.data = [conflict_data]

        mock_query = MagicMock()
        self.mock_client.table.return_value = mock_query
        
        # Select chain
        mock_query.select.return_value.eq.return_value.execute.side_effect = [
            mock_find_resp_1,
            mock_find_resp_2
        ]
        
        # Update chain (generic update signature might vary, so matching broad)
        mock_query.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_update_resp
        mock_query.update.return_value.eq.return_value.execute.return_value = mock_update_resp

        with pytest.raises(ConcurrencyError):
            await self.repository.update("01ARZ3NDEKTSV4RRFFQ69G5FAV", {"val": 1})

    async def test_create_history_write_exception(self):
        """Test exception when writing history in update_status."""
        # Find works
        self.mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]

        # Update works
        updated_data = {**self.mock_conversation_data, "status": "progress", "version": 2}
        self.mock_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        mock_conv_table = MagicMock()
        mock_conv_table.select.return_value.eq.return_value.execute.return_value.data = [
            self.mock_conversation_data
        ]
        mock_conv_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            updated_data
        ]

        mock_hist_table = MagicMock()
        mock_hist_table.insert.side_effect = Exception("History Error")

        def table_side_effect(table_name):
            if table_name == "conversations":
                return mock_conv_table
            return mock_hist_table

        self.mock_client.table.side_effect = table_side_effect

        with patch(
            "src.modules.conversation.repositories.impl.supabase.conversation_repository.logger"
        ) as mock_logger:
            result = await self.repository.update_status(
                "01ARZ3NDEKTSV4RRFFQ69G5FAV", ConversationStatus.PROGRESS
            )

            assert result is not None
            mock_logger.error.assert_called_with(
                "Failed to write conversation state history",
                conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                error="History Error",
            )
