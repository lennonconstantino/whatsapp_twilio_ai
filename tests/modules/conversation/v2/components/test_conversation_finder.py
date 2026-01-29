"""
Unit tests for Conversation Finder Component (V2).
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, ANY

from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.v2.components.conversation_finder import ConversationFinder

class TestConversationFinder(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.finder = ConversationFinder(self.repo)
        
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="whatsapp:+123",
            to_number="whatsapp:+456",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value,
            started_at=datetime.now(timezone.utc),
            session_key="whatsapp:+123::whatsapp:+456",
            version=1
        )

    def test_calculate_session_key(self):
        """Test session key calculation."""
        # Order independence
        key1 = self.finder.calculate_session_key("whatsapp:+123", "whatsapp:+456")
        key2 = self.finder.calculate_session_key("whatsapp:+456", "whatsapp:+123")
        self.assertEqual(key1, key2)
        
        # Normalization
        key3 = self.finder.calculate_session_key("+123", "+456")
        self.assertEqual(key3, key1)

    def test_find_active(self):
        """Test finding active conversation."""
        self.repo.find_active_by_session_key.return_value = self.mock_conv
        
        result = self.finder.find_active("OWNER", "+123", "+456")
        
        self.assertEqual(result, self.mock_conv)
        self.repo.find_active_by_session_key.assert_called_with(
            "OWNER",
            "whatsapp:+123::whatsapp:+456"
        )

    def test_find_last_conversation(self):
        """Test finding last conversation."""
        self.repo.find_all_by_session_key.return_value = [self.mock_conv]
        
        result = self.finder.find_last_conversation("OWNER", "+123", "+456")
        
        self.assertEqual(result, self.mock_conv)
        self.repo.find_all_by_session_key.assert_called_with(
            "OWNER",
            "whatsapp:+123::whatsapp:+456",
            limit=1
        )

    def test_create_new(self):
        """Test creating new conversation."""
        self.repo.create.return_value = self.mock_conv
        
        result = self.finder.create_new(
            "OWNER",
            "+123",
            "+456",
            "whatsapp",
            metadata={"source": "test"}
        )
        
        self.assertEqual(result, self.mock_conv)
        self.repo.create.assert_called()
        args = self.repo.create.call_args[0][0]
        self.assertEqual(args["owner_id"], "OWNER")
        self.assertEqual(args["status"], ConversationStatus.PENDING.value)
        self.assertEqual(args["metadata"]["source"], "test")

    def test_create_new_linked(self):
        """Test creating new linked conversation."""
        self.repo.create.return_value = self.mock_conv
        prev_conv = self.mock_conv
        prev_conv.ended_at = datetime.now(timezone.utc)
        
        self.finder.create_new(
            "OWNER",
            "+123",
            "+456",
            "whatsapp",
            previous_conversation=prev_conv
        )
        
        args = self.repo.create.call_args[0][0]
        self.assertEqual(args["metadata"]["previous_conversation_id"], prev_conv.conv_id)
        self.assertIn("linked_at", args["metadata"])

if __name__ == "__main__":
    unittest.main()
