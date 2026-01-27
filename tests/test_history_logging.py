import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.modules.conversation.models.conversation import (Conversation,
                                                          ConversationStatus)
from src.modules.conversation.repositories.conversation_repository import \
    ConversationRepository


class TestHistoryLogging(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.repo = ConversationRepository(self.mock_client)
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="whatsapp:+1234567890",
            to_number="whatsapp:+0987654321",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc).isoformat(),
            context={},
        )
        self.repo.find_by_id = MagicMock(return_value=self.mock_conv)
        self.repo.update = MagicMock(return_value=self.mock_conv)
        self.repo.model_class = lambda **kwargs: self.mock_conv

    def test_update_status_logs_history(self):
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_execute = MagicMock()

        self.mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = mock_execute

        new_status = ConversationStatus.PROGRESS
        initiated_by = "agent"
        reason = "agent_acceptance"

        self.repo.update_status(
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
        self.assertTrue(
            len(history_calls) > 0,
            "Should have called table('conversation_state_history')",
        )

        call_args = mock_table.insert.call_args
        self.assertIsNotNone(call_args, "Insert should have been called")

        history_data = call_args[0][0]
        self.assertEqual(history_data["conv_id"], self.mock_conv.conv_id)
        self.assertEqual(
            history_data["from_status"],
            ConversationStatus.PENDING.value,
        )
        self.assertEqual(
            history_data["to_status"],
            ConversationStatus.PROGRESS.value,
        )
        self.assertEqual(history_data["changed_by"], "agent")
        self.assertEqual(history_data["reason"], "agent_acceptance")
        self.assertIn("metadata", history_data)

    def test_update_status_sanitizes_changed_by(self):
        mock_table = MagicMock()
        mock_insert = MagicMock()
        self.mock_client.table.return_value = mock_table
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock()

        self.repo.update_status(
            self.mock_conv.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="invalid_user_type",
            reason="testing",
        )

        call_args = mock_table.insert.call_args
        self.assertIsNotNone(call_args, "Insert should have been called")
        history_data = call_args[0][0]
        self.assertEqual(
            history_data["changed_by"],
            "system",
            "Should sanitize invalid user type to 'system'",
        )
        self.assertEqual(
            history_data["metadata"]["original_initiated_by"],
            "invalid_user_type",
        )

    def test_create_logs_history(self):
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

        self.repo.create(new_data)

        self.mock_client.table.assert_any_call("conversation_state_history")

        insert_calls = mock_table.insert.call_args_list
        self.assertTrue(
            len(insert_calls) >= 2,
            "Should have called insert at least twice (create + history)",
        )

        history_data = None
        for call in insert_calls:
            data = call[0][0]
            if isinstance(data, dict) and "to_status" in data:
                if "reason" in data:
                    if data["reason"] == "conversation_created":
                        history_data = data
                        break

        self.assertIsNotNone(history_data, "History log entry not found")
        self.assertEqual(history_data["conv_id"], created_data["conv_id"])
        self.assertIsNone(history_data["from_status"])
        self.assertEqual(history_data["to_status"], "pending")
        self.assertEqual(history_data["changed_by"], "system")


if __name__ == "__main__":
    unittest.main()
