"""
Unit tests for Conversation Service V2.
"""

import os
import sys
from unittest.mock import MagicMock, AsyncMock

from dotenv import load_dotenv

# Load test environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env.test"), override=True)

# Mock database connection BEFORE importing modules that use it
sys.modules["src.core.database.session"] = MagicMock()
sys.modules["src.core.database.session"].db = MagicMock()
sys.modules["src.core.database.session"].get_db = MagicMock()
sys.modules["src.core.database.session"].DatabaseConnection = MagicMock()

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, Mock

from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.components.conversation_closer import \
    ClosureResult
from src.modules.conversation.services.conversation_service import \
    ConversationService


@pytest.mark.asyncio
class TestConversationServiceV2:
    @pytest.fixture(autouse=True)
    async def setup(self):
        self.repo = AsyncMock()
        self.message_repo = AsyncMock()
        self.finder = AsyncMock()
        self.lifecycle = AsyncMock()
        self.closer = Mock() # Assuming closer is sync

        self.service = ConversationService(
            self.repo, self.message_repo, self.finder, self.lifecycle, self.closer
        )

        # Valid ULIDs for testing
        self.valid_ulid_1 = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        self.valid_ulid_2 = "01ARZ3NDEKTSV4RRFFQ69G5FAW"

        self.mock_conv = Conversation(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            channel="whatsapp",
            session_key="123::456",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    async def test_get_or_create_active_found(self):
        """Test finding an existing active conversation."""
        self.finder.find_active.return_value = self.mock_conv
        # Ensure conversation is not expired and not closed
        self.mock_conv.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        self.mock_conv.status = ConversationStatus.PENDING.value

        result = await self.service.get_or_create_conversation(
            self.valid_ulid_2, "123", "456"
        )

        assert result == self.mock_conv
        self.finder.create_new.assert_not_called()

    async def test_get_or_create_active_expired(self):
        """Test finding an active conversation that is actually expired."""
        self.finder.find_active.return_value = self.mock_conv
        # Make it expired
        self.mock_conv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.mock_conv.status = ConversationStatus.PENDING.value

        new_conv = Mock(spec=Conversation)
        self.finder.create_new.return_value = new_conv

        result = await self.service.get_or_create_conversation(
            self.valid_ulid_2, "123", "456"
        )

        # Should expire old one
        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.EXPIRED,
            reason="expired_before_new",
            initiated_by="system",
        )

        # Should create new one linked
        self.finder.create_new.assert_called_with(
            self.valid_ulid_2,
            "123",
            "456",
            "whatsapp",
            None,
            None,
            previous_conversation=self.mock_conv,
        )
        assert result == new_conv

    async def test_get_or_create_not_found(self):
        """Test creating new conversation when none found."""
        self.finder.find_active.return_value = None
        self.finder.find_last_conversation.return_value = None

        new_conv = Mock(spec=Conversation)
        self.finder.create_new.return_value = new_conv

        result = await self.service.get_or_create_conversation(
            self.valid_ulid_2, "123", "456"
        )

        self.finder.create_new.assert_called()
        assert result == new_conv

    async def test_add_message_closure_intent(self):
        """Test detecting closure intent."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Stop please",
            message_owner=MessageOwner.USER,
            content="Stop please",
            direction="inbound",
            message_type="text",
        )

        self.closer.detect_intent.return_value = ClosureResult(
            should_close=True,
            confidence=1.0,
            reasons=[],
            suggested_status=ConversationStatus.USER_CLOSED,
        )

        await self.service.add_message(self.mock_conv, msg_dto)

        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.USER_CLOSED,
            "user_intent_detected",
            "user",
            expires_at=None,
        )

    async def test_add_message_agent_acceptance(self):
        """Test agent message transitioning PENDING -> PROGRESS."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Hello",
            message_owner=MessageOwner.AGENT,
            content="Hello",
            direction="outbound",
            message_type="text",
        )

        self.closer.detect_intent.return_value = ClosureResult(
            should_close=False, confidence=0, reasons=[]
        )

        self.mock_conv.status = ConversationStatus.PENDING.value

        await self.service.add_message(self.mock_conv, msg_dto)

        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.PROGRESS,
            "agent_acceptance",
            "agent",
            expires_at=ANY,
        )

    async def test_add_message_reactivation(self):
        """Test user message transitioning IDLE -> PROGRESS."""
        msg_dto = MessageCreateDTO(
            conv_id=self.valid_ulid_1,
            owner_id=self.valid_ulid_2,
            from_number="123",
            to_number="456",
            body="Hi again",
            message_owner=MessageOwner.USER,
            content="Hi again",
            direction="inbound",
            message_type="text",
        )

        self.closer.detect_intent.return_value = ClosureResult(
            should_close=False, confidence=0, reasons=[]
        )

        self.mock_conv.status = ConversationStatus.IDLE_TIMEOUT.value

        await self.service.add_message(self.mock_conv, msg_dto)

        self.lifecycle.transition_to.assert_called_with(
            self.mock_conv,
            ConversationStatus.PROGRESS,
            "user_reactivation",
            "user",
            expires_at=None,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
