import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from src.modules.conversation.models.conversation import (Conversation,
                                                          ConversationStatus)
from src.modules.conversation.repositories.impl.supabase.conversation_repository import \
    SupabaseConversationRepository


@pytest.mark.asyncio
class TestHistoryLogging:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.mock_client = MagicMock()
        self.repo = SupabaseConversationRepository(self.mock_client)
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="whatsapp:+1234567890",
            to_number="whatsapp:+0987654321",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc).isoformat(),
            context={},
        )
        # find_by_id is sync in SupabaseRepository base, but we might need to check if it's async in base
        # SupabaseRepository.find_by_id is likely sync because it calls client directly without run_in_threadpool in base?
        # Let's check SupabaseRepository later if needed. But assuming find_by_id is sync for now or handled by repo wrapper.
        # Actually in SupabaseConversationRepository code: 
        # current = self.find_by_id(conv_id, id_column="conv_id") inside _update (sync)
        # So find_by_id is sync.
        
        self.repo.find_by_id = MagicMock(return_value=self.mock_conv)
        
        # update is async in SupabaseConversationRepository, but the sync logic is in _update.
        # However, we are testing update_status which calls _update.
        # _update calls self.find_by_id (mocked above) and super().update
        # create calls super().create
        
        # We need to ensure super().update and super().create don't fail or are mocked if they are complex.
        # Since we are testing logging, we can rely on mocks on client.
        
        # We need to mock model_class for create return
        self.repo.model_class = lambda **kwargs: self.mock_conv

    async def test_update_status_logs_history(self):
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_execute = MagicMock()
        mock_update = MagicMock()

        self.mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute
        
        # Mock update call response
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_update
        mock_update.execute.return_value = MagicMock(data=[self.mock_conv.model_dump()])

        new_status = ConversationStatus.PROGRESS
        initiated_by = "agent"
        reason = "agent_acceptance"

        await self.repo.update_status(
            self.mock_conv.conv_id,
            new_status,
            initiated_by=initiated_by,
            reason=reason,
        )

        self.mock_client.table.assert_any_call("conversation_state_history")

        history_calls = [
            call
            for call in self.mock_client.table.mock_calls
            if call.args == ("conversation_state_history",)
        ]
        assert len(history_calls) > 0, "Should have called table('conversation_state_history')"

        call_args = mock_table.insert.call_args
        assert call_args is not None, "Insert should have been called"

        history_data = call_args[0][0]
        assert history_data["conv_id"] == self.mock_conv.conv_id
        assert history_data["from_status"] == ConversationStatus.PENDING.value
        assert history_data["to_status"] == ConversationStatus.PROGRESS.value
        assert history_data["changed_by"] == "agent"
        assert history_data["reason"] == "agent_acceptance"
        assert "metadata" in history_data

    async def test_update_status_sanitizes_changed_by(self):
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_update = MagicMock()
        
        self.mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock()
        
        # Mock update call response
        mock_table.update.return_value = mock_update
        mock_update.eq.return_value = mock_update
        mock_update.execute.return_value = MagicMock(data=[self.mock_conv.model_dump()])

        await self.repo.update_status(
            self.mock_conv.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="invalid_user_type",
            reason="testing",
        )

        call_args = mock_table.insert.call_args
        assert call_args is not None, "Insert should have been called"
        history_data = call_args[0][0]
        assert history_data["changed_by"] == "system", "Should sanitize invalid user type to 'system'"
        assert history_data["metadata"]["original_initiated_by"] == "invalid_user_type"

    async def test_create_logs_history(self):
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_execute = MagicMock()

        self.mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute

        created_data = {
            "conv_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "from_number": "whatsapp:+1234567890",
            "to_number": "whatsapp:+0987654321",
            "status": "pending",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "context": {},
        }
        mock_execute.data = [created_data]

        new_data = {
            "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            "from_number": "whatsapp:+1234567890",
            "to_number": "whatsapp:+0987654321",
            "status": "pending",
        }

        await self.repo.create(new_data)

        self.mock_client.table.assert_any_call("conversation_state_history")

        insert_calls = mock_table.insert.call_args_list
        assert len(insert_calls) >= 2, "Should have called insert at least twice (create + history)"

        history_data = None
        for call in insert_calls:
            data = call[0][0]
            if isinstance(data, dict) and "to_status" in data:
                if "reason" in data:
                    if data["reason"] == "conversation_created":
                        history_data = data
                        break

        assert history_data is not None, "History log entry not found"
        assert history_data["conv_id"] == created_data["conv_id"]
        assert history_data["from_status"] is None
        assert history_data["to_status"] == "pending"
        assert history_data["changed_by"] == "system"


if __name__ == "__main__":
    unittest.main()
