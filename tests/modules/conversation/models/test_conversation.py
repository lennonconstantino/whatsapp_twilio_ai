
import pytest
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.enums.conversation_status import ConversationStatus

class TestConversationModel:
    def test_valid_creation(self):
        conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+1234567890",
            to_number="+0987654321"
        )
        assert conv.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert conv.status == ConversationStatus.PENDING

    def test_invalid_ulid(self):
        with pytest.raises(ValidationError):
            Conversation(
                conv_id="invalid-ulid",
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                from_number="+123",
                to_number="+456"
            )

        with pytest.raises(ValidationError):
            Conversation(
                conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                owner_id="invalid-ulid",
                from_number="+123",
                to_number="+456"
            )

    def test_user_id_validation(self):
        conv = Conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456",
            user_id="01ARZ3NDEKTSV4RRFFQ69G5FAV"
        )
        assert conv.user_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        with pytest.raises(ValidationError):
            Conversation(
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                from_number="+123",
                to_number="+456",
                user_id="invalid"
            )

    def test_status_helpers(self):
        conv = Conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456",
            status=ConversationStatus.PROGRESS
        )
        assert conv.is_active() is True
        assert conv.is_paused() is False
        assert conv.is_closed() is False
        assert conv.can_receive_messages() is True

        conv.status = ConversationStatus.AGENT_CLOSED
        assert conv.is_active() is False
        assert conv.is_closed() is True

    def test_is_expired(self):
        conv = Conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456",
            status=ConversationStatus.PROGRESS
        )
        # No expiry set
        assert conv.is_expired() is False

        # Future expiry
        conv.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        assert conv.is_expired() is False

        # Past expiry
        conv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert conv.is_expired() is True
        
        # Closed conversation shouldn't be expired (it's closed)
        conv.status = ConversationStatus.EXPIRED
        assert conv.is_expired() is False

    def test_is_idle(self):
        conv = Conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456",
            status=ConversationStatus.PROGRESS
        )
        # No timestamps
        assert conv.is_idle(30) is False

        # Recent activity
        conv.updated_at = datetime.now(timezone.utc)
        assert conv.is_idle(30) is False

        # Old activity
        conv.updated_at = datetime.now(timezone.utc) - timedelta(minutes=60)
        assert conv.is_idle(30) is True

        # Closed conversation shouldn't be idle
        conv.status = ConversationStatus.AGENT_CLOSED
        assert conv.is_idle(30) is False

    def test_close_conversation(self):
        conv = Conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456",
            status=ConversationStatus.PROGRESS
        )
        
        conv.close_conversation(ConversationStatus.AGENT_CLOSED, "Bye")
        
        assert conv.status == ConversationStatus.AGENT_CLOSED
        assert conv.ended_at is not None

    def test_repr(self):
        conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+123",
            to_number="+456"
        )
        assert "01ARZ3NDEKTSV4RRFFQ69G5FAV" in repr(conv)
