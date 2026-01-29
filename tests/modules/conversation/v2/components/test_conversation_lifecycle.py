"""
Unit tests for Conversation Lifecycle Component (V2).
"""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, ANY

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.v2.components.conversation_lifecycle import ConversationLifecycle

class TestConversationLifecycle(unittest.TestCase):
    def setUp(self):
        self.repo = MagicMock()
        self.lifecycle = ConversationLifecycle(self.repo)
        
        self.mock_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
            version=1
        )

    def test_transition_valid(self):
        """Test valid transition."""
        self.repo.update.return_value = self.mock_conv
        
        self.lifecycle.transition_to(
            self.mock_conv,
            ConversationStatus.PROGRESS,
            reason="test",
            initiated_by="agent"
        )
        
        self.repo.update.assert_called_with(
            self.mock_conv.conv_id,
            {
                "status": ConversationStatus.PROGRESS.value,
                "updated_at": ANY
            },
            id_column="conv_id",
            current_version=1
        )

    def test_transition_invalid(self):
        """Test invalid transition raises ValueError."""
        # PENDING -> AGENT_CLOSED is invalid directly (must go to PROGRESS first usually, or maybe allowed?)
        # Let's check VALID_TRANSITIONS in code.
        # PENDING -> [PROGRESS, EXPIRED, SUPPORT_CLOSED, USER_CLOSED, FAILED]
        # AGENT_CLOSED is NOT in PENDING transitions.
        
        with self.assertRaises(ValueError):
            self.lifecycle.transition_to(
                self.mock_conv,
                ConversationStatus.AGENT_CLOSED,
                reason="invalid",
                initiated_by="agent"
            )

    def test_transition_concurrency_error(self):
        """Test concurrency error propagation."""
        self.repo.update.return_value = None # Simulate optimistic lock failure
        
        with self.assertRaises(ConcurrencyError):
            self.lifecycle.transition_to(
                self.mock_conv,
                ConversationStatus.PROGRESS,
                reason="test",
                initiated_by="agent"
            )

    def test_transition_priority_override(self):
        """Test priority override (Lower -> Higher Priority)."""
        # Current: USER_CLOSED (Prio 2)
        self.mock_conv.status = ConversationStatus.USER_CLOSED.value
        self.repo.update.return_value = self.mock_conv
        
        # Try: FAILED (Prio 1)
        self.lifecycle.transition_to_with_priority(
            self.mock_conv,
            ConversationStatus.FAILED,
            reason="error",
            initiated_by="system"
        )
        
        self.repo.update.assert_called()
        args = self.repo.update.call_args[0]
        self.assertEqual(args[1]["status"], ConversationStatus.FAILED.value)

    def test_transition_priority_ignore(self):
        """Test priority ignore (Higher -> Lower Priority)."""
        # Current: USER_CLOSED (Prio 2)
        self.mock_conv.status = ConversationStatus.USER_CLOSED.value
        
        # Try: AGENT_CLOSED (Prio 4)
        self.lifecycle.transition_to_with_priority(
            self.mock_conv,
            ConversationStatus.AGENT_CLOSED,
            reason="done",
            initiated_by="agent"
        )
        
        self.repo.update.assert_not_called()

    def test_extend_expiration(self):
        """Test extend expiration."""
        self.repo.update.return_value = self.mock_conv
        
        self.lifecycle.extend_expiration(self.mock_conv, 60)
        
        self.repo.update.assert_called()
        args = self.repo.update.call_args[0]
        self.assertIn("expires_at", args[1])

    def test_transfer_owner(self):
        """Test transfer owner."""
        self.repo.update.return_value = self.mock_conv
        
        self.lifecycle.transfer_owner(
            self.mock_conv,
            "NEW_USER_ID",
            "shift_change"
        )
        
        self.repo.update.assert_called()
        args = self.repo.update.call_args[0]
        self.assertEqual(args[1]["user_id"], "NEW_USER_ID")
        self.assertIn("transfer_history", args[1]["context"])

    def test_escalate(self):
        """Test escalate."""
        self.repo.update.return_value = self.mock_conv
        
        self.lifecycle.escalate(
            self.mock_conv,
            "SUPERVISOR_ID",
            "help"
        )
        
        self.repo.update.assert_called()
        args = self.repo.update.call_args[0]
        self.assertEqual(args[1]["status"], ConversationStatus.PROGRESS.value)
        self.assertIn("escalated", args[1]["context"])

if __name__ == "__main__":
    unittest.main()
