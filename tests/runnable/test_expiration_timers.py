import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, MagicMock

from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env.test"), override=True)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.config import settings
from src.modules.conversation.components.closure_detector import \
    ClosureDetector
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.services.conversation_service import \
    ConversationService


class TestExpirationTimers(unittest.TestCase):
    def setUp(self):
        # Mock repositories
        self.repo = MagicMock()
        self.msg_repo = MagicMock()
        self.closure_detector = ClosureDetector()  # Logic only, no DB

        # Initialize service with mocks
        self.service = ConversationService(
            self.repo, self.msg_repo, self.closure_detector
        )

        # Setup common mock objects
        self.owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.conv_id = "01ARZ3NDEKTSV4RRFFQ69G5FAW"

        # Helper to simulate creation return
        def create_side_effect(data):
            data_copy = data.copy()
            # Convert ISO strings back to datetime objects for the model
            if "expires_at" in data_copy and isinstance(data_copy["expires_at"], str):
                data_copy["expires_at"] = datetime.fromisoformat(
                    data_copy["expires_at"]
                )
            if "started_at" in data_copy and isinstance(data_copy["started_at"], str):
                data_copy["started_at"] = datetime.fromisoformat(
                    data_copy["started_at"]
                )

            # Ensure ID
            if "conv_id" not in data_copy:
                data_copy["conv_id"] = self.conv_id

            return Conversation(**data_copy)

        self.repo.create.side_effect = create_side_effect

    def test_pending_expiration_timer(self):
        """Test that new conversations (PENDING) get ~48h expiration."""
        # Config values
        pending_minutes = settings.conversation.pending_expiration_minutes

        # Setup mock: No active conversation found
        self.repo.find_active_by_session_key.return_value = None
        self.repo.find_all_by_session_key.return_value = []  # No history

        # Create conversation
        conv = self.service.get_or_create_conversation(
            owner_id=self.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
        )

        # Assert status
        self.assertEqual(conv.status, ConversationStatus.PENDING.value)

        # Assert expiration time
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=pending_minutes)

        # Allow 1 minute tolerance
        # Note: conv.expires_at comes from our side_effect which uses data passed by service
        diff = abs((conv.expires_at - expected_expiry).total_seconds())
        self.assertLess(
            diff,
            60,
            f"Expiration should be close to {pending_minutes} " f"minutes from now",
        )

        print(f"PENDING Expiration Validated: {conv.expires_at} (~48h)")

    def test_progress_expiration_update(self):
        """Test that transition to PROGRESS updates expiration to ~24h."""
        progress_minutes = settings.conversation.expiration_minutes

        # Setup existing PENDING conversation
        pending_conv = Conversation(
            conv_id=self.conv_id,
            owner_id=self.owner_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
            session_key="test::key",
        )

        # Simulate Agent response to transition to PROGRESS
        msg_dto = MessageCreateDTO(
            conv_id=pending_conv.conv_id,
            owner_id=self.owner_id,
            body="Hello, I will help you.",
            message_owner=MessageOwner.AGENT,
            from_number=pending_conv.to_number,
            to_number=pending_conv.from_number,
        )

        # Mock update_status to return updated conversation
        def update_status_side_effect(
            conv_id, status, initiated_by, reason, expires_at=None, **kwargs
        ):
            pending_conv.status = status.value if hasattr(status, "value") else status
            if expires_at:
                pending_conv.expires_at = expires_at
            return pending_conv

        self.repo.update_status.side_effect = update_status_side_effect
        # Mock context update too
        self.repo.update_context.return_value = pending_conv

        # Add message (triggers transition logic)
        self.service.add_message(pending_conv, msg_dto)

        # Verify update_status was called with correct status and expiration
        self.repo.update_status.assert_called()

        # Inspect call args to verify expiration logic
        call_args = self.repo.update_status.call_args
        args, kwargs = call_args

        # Check status (passed as positional arg in service)
        # call: update_status(conv_id, status, initiated_by=..., ...)
        self.assertEqual(args[1], ConversationStatus.PROGRESS)

        # Check expiration (passed as kwarg in service)
        updated_expiry = kwargs.get("expires_at")
        self.assertIsNotNone(
            updated_expiry, "expires_at should be passed to update_status"
        )

        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=progress_minutes)

        diff = abs((updated_expiry - expected_expiry).total_seconds())
        self.assertLess(
            diff,
            60,
            f"Updated expiration should be close to {progress_minutes} "
            f"minutes from now",
        )

        print(f"PROGRESS Expiration Validated: {updated_expiry} (~24h)")


if __name__ == "__main__":
    unittest.main()
