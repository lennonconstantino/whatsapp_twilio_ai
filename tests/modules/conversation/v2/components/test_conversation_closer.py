"""
Unit tests for Conversation Closer Component (V2).
"""
import unittest
from unittest.mock import MagicMock

from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.v2.components.conversation_closer import ConversationCloser

class TestConversationCloser(unittest.TestCase):
    def setUp(self):
        self.closer = ConversationCloser(closure_keywords=["encerrar", "encerrar atendimento"])
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value
        )

    def test_detect_intent_keywords(self):
        """Test detection by keywords."""
        msg = Message(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number=self.mock_conv.from_number,
            to_number=self.mock_conv.to_number,
            body="Encerrar atendimento",
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT
        )
        
        result = self.closer.detect_intent(msg, self.mock_conv)
        
        self.assertTrue(result.should_close)
        self.assertEqual(result.suggested_status, ConversationStatus.USER_CLOSED)

    def test_detect_intent_negative(self):
        """Test no detection."""
        msg = Message(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number=self.mock_conv.from_number,
            to_number=self.mock_conv.to_number,
            body="Olá, preciso de ajuda",
            message_owner=MessageOwner.USER,
            message_type=MessageType.TEXT
        )
        
        result = self.closer.detect_intent(msg, self.mock_conv)
        
        self.assertFalse(result.should_close)

    def test_detect_intent_agent_message(self):
        """Test ignoring agent messages."""
        msg = Message(
            conv_id=self.mock_conv.conv_id,
            owner_id=self.mock_conv.owner_id,
            from_number=self.mock_conv.from_number,
            to_number=self.mock_conv.to_number,
            body="Encerrar",
            message_owner=MessageOwner.AGENT,
            message_type=MessageType.TEXT
        )
        
        result = self.closer.detect_intent(msg, self.mock_conv)
        
        self.assertFalse(result.should_close)

if __name__ == "__main__":
    unittest.main()
