from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.core.utils.exceptions import ConcurrencyError, DuplicateError
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner
from src.modules.conversation.enums.message_type import MessageType
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.models.message import Message
from src.modules.conversation.services.conversation_service import \
    ConversationService


class TestConversationService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_message_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_closure_detector(self):
        mock = MagicMock()
        mock.detect_closure_intent.return_value = {
            "should_close": False,
            "confidence": 0.0,
            "reasons": [],
            "suggested_status": None,
        }
        mock.detect_cancellation_in_pending.return_value = False
        return mock

    @pytest.fixture
    def service(self, mock_repo, mock_message_repo, mock_closure_detector):
        return ConversationService(
            conversation_repo=mock_repo,
            message_repo=mock_message_repo,
            closure_detector=mock_closure_detector,
        )

    @pytest.fixture
    def mock_conversation(self):
        return Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PROGRESS.value,
            started_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            session_key="+5511888888888::+5511999999999",
            context={},
            version=1,
        )

    def test_get_or_create_existing_active(self, service, mock_repo, mock_conversation):
        """Test retrieving an existing active conversation."""
        # Setup
        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = mock_conversation

        # Execute
        result = service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )

        # Verify
        assert result.conv_id == mock_conversation.conv_id
        mock_repo.create.assert_not_called()

    def test_get_or_create_expired_creates_new(
        self, service, mock_repo, mock_conversation
    ):
        """Test that an expired conversation triggers creation of a new one."""
        # Setup expired conversation
        expired_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mock_conversation.expires_at = datetime.fromisoformat(expired_date)
        mock_conversation.status = ConversationStatus.EXPIRED.value

        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = mock_conversation

        # Mock create returning new conversation
        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",  # Reusing ID for simplicity in mock, usually different
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            version=1,
        )
        mock_repo.create.return_value = new_conv

        # Execute
        result = service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )

        # Verify
        assert result.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_repo.create.assert_called_once()
        # Verify metadata linking
        call_args = mock_repo.create.call_args[0][0]
        assert (
            call_args["metadata"]["previous_conversation_id"]
            == mock_conversation.conv_id
        )

    def test_get_or_create_none_creates_new(self, service, mock_repo):
        """Test creating new conversation when none exists."""
        # Setup
        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = None
        mock_repo.find_all_by_session_key.return_value = []  # No history

        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            version=1,
        )
        mock_repo.create.return_value = new_conv

        # Execute
        result = service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )

        # Verify
        assert result.conv_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        mock_repo.create.assert_called_once()

    def test_add_message_reactivates_idle(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test that adding a message reactivates an IDLE_TIMEOUT conversation."""
        # Setup
        mock_conversation.status = ConversationStatus.IDLE_TIMEOUT.value
        mock_repo.update_status.return_value = mock_conversation
        mock_repo.update_context.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            content="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id=mock_conversation.owner_id,
            conv_id=mock_conversation.conv_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            content="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="user",
            reason="reactivation_from_idle",
        )

    def test_add_message_agent_accepts_pending(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test that agent message transitions PENDING to PROGRESS."""
        # Setup
        mock_conversation.status = ConversationStatus.PENDING.value
        mock_repo.update_status.return_value = mock_conversation
        mock_repo.update_context.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511888888888",  # Agent replying
            to_number="+5511999999999",
            body="Hello from agent",
            content="Hello from agent",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.AGENT,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id=mock_conversation.owner_id,
            conv_id=mock_conversation.conv_id,
            from_number="+5511888888888",
            to_number="+5511999999999",
            body="Hello from agent",
            content="Hello from agent",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.AGENT,
            channel="whatsapp",
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="agent",
            reason="agent_acceptance",
            expires_at=ANY,
        )

    def test_add_message_user_pending_keeps_pending(
        self,
        service,
        mock_repo,
        mock_message_repo,
        mock_conversation,
        mock_closure_detector,
    ):
        """Test that user message in PENDING keeps it in PENDING."""
        # Setup
        mock_conversation.status = ConversationStatus.PENDING.value
        mock_closure_detector.detect_cancellation_in_pending.return_value = False

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello from user",
            content="Hello from user",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id=mock_conversation.owner_id,
            conv_id=mock_conversation.conv_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello from user",
            content="Hello from user",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        mock_repo.update_status.assert_not_called()

    def test_add_message_cancellation_in_pending(
        self,
        service,
        mock_repo,
        mock_message_repo,
        mock_conversation,
        mock_closure_detector,
    ):
        """Test user cancellation while in PENDING."""
        # Setup
        mock_conversation.status = ConversationStatus.PENDING.value
        mock_closure_detector.detect_cancellation_in_pending.return_value = True

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="CANCEL",
            content="CANCEL",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id=mock_conversation.owner_id,
            conv_id=mock_conversation.conv_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="CANCEL",
            content="CANCEL",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.USER_CLOSED,
            initiated_by="user",
            reason="user_cancellation_in_pending",
            ended_at=ANY,
        )

    def test_add_message_concurrency_retry(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test retry logic on ConcurrencyError."""
        # Setup
        mock_conversation.status = ConversationStatus.IDLE_TIMEOUT.value

        # First call fails with ConcurrencyError, second succeeds
        mock_repo.update_status.side_effect = [
            ConcurrencyError("Conflict"),
            mock_conversation,  # Success on retry
        ]
        mock_repo.update_context.return_value = mock_conversation

        # Mock find_by_id for reload
        mock_repo.find_by_id.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            content="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id=mock_conversation.owner_id,
            conv_id=mock_conversation.conv_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            content="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        assert mock_repo.update_status.call_count == 2
        mock_repo.find_by_id.assert_called_once()

    def test_close_conversation_success(self, service, mock_repo, mock_conversation):
        """Test successful conversation closure."""
        # Setup
        mock_repo.update_status.return_value = mock_conversation

        # Execute
        result = service.close_conversation(
            mock_conversation,
            ConversationStatus.AGENT_CLOSED,
            initiated_by="agent",
            reason="done",
        )

        # Verify
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.AGENT_CLOSED,
            ended_at=ANY,
            initiated_by="agent",
            reason="done",
        )
        assert result == mock_conversation

    def test_close_conversation_concurrency_retry(
        self, service, mock_repo, mock_conversation
    ):
        """Test retry logic when closing conversation."""
        # Setup
        mock_repo.update_status.side_effect = [
            ConcurrencyError("Conflict"),
            mock_conversation,
        ]
        mock_repo.find_by_id.return_value = mock_conversation

        # Execute
        service.close_conversation(mock_conversation, ConversationStatus.AGENT_CLOSED)

        # Verify
        assert mock_repo.update_status.call_count == 2
        mock_repo.find_by_id.assert_called_once()

    def test_get_methods(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test simple get methods."""
        # Setup
        mock_repo.find_by_id.return_value = mock_conversation
        mock_repo.find_active_by_owner.return_value = [mock_conversation]
        mock_message_repo.find_by_conversation.return_value = []

        # Execute & Verify
        assert (
            service.get_conversation_by_id("01ARZ3NDEKTSV4RRFFQ69G5FAV")
            == mock_conversation
        )
        assert service.get_active_conversations("01ARZ3NDEKTSV4RRFFQ69G5FAV") == [
            mock_conversation
        ]
        assert service.get_conversation_messages("01ARZ3NDEKTSV4RRFFQ69G5FAV") == []

    def test_process_expired_conversations(self, service, mock_repo, mock_conversation):
        """Test processing of expired conversations."""
        # Setup
        expired_conv = mock_conversation
        expired_conv.status = ConversationStatus.PENDING.value
        mock_repo.find_expired_conversations.return_value = [expired_conv]
        mock_repo.update_status.return_value = expired_conv

        # Execute
        count = service.process_expired_conversations(limit=10)

        # Verify
        assert count == 1
        mock_repo.update_status.assert_called_with(
            expired_conv.conv_id,
            ConversationStatus.EXPIRED,
            ended_at=ANY,
            initiated_by="system",
            reason="expired",
        )

    def test_process_expired_concurrency_recovery(
        self, service, mock_repo, mock_conversation
    ):
        """Test recovery from concurrency error during expiration."""
        # Setup
        expired_conv = mock_conversation
        # Set expired date
        expired_conv.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_conv.status = ConversationStatus.PENDING.value

        mock_repo.find_expired_conversations.return_value = [expired_conv]

        # First update fails with ConcurrencyError
        # Second update (after reload) succeeds
        mock_repo.update_status.side_effect = [
            ConcurrencyError("Conflict"),
            expired_conv,
        ]

        # Reload finds the conversation still expired
        mock_repo.find_by_id.return_value = expired_conv

        # Execute
        count = service.process_expired_conversations(limit=10)

        # Verify
        assert count == 1
        assert mock_repo.update_status.call_count == 2
        mock_repo.find_by_id.assert_called_once()

    def test_should_check_closure(self, service):
        """Test _should_check_closure logic."""
        # Text message from user -> True
        msg_text = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="text",
            content="text",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
        )
        assert service._should_check_closure(msg_text) is True

        # Audio message -> True (current implementation only checks owner)
        msg_audio = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="audio",
            content="audio",
            message_type=MessageType.AUDIO,
            message_owner=MessageOwner.USER,
        )
        assert service._should_check_closure(msg_audio) is True

        # Agent message -> False
        msg_agent = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="text",
            content="text",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.AGENT,
        )
        assert service._should_check_closure(msg_agent) is False

    def test_close_conversation_priority(self, service, mock_repo, mock_conversation):
        """Test close_conversation_with_priority logic."""
        # 1. Try to close with lower priority (AGENT_CLOSED vs USER_CLOSED)
        # Setup: Current status is USER_CLOSED (prio 2)
        mock_conversation.status = ConversationStatus.USER_CLOSED.value
        mock_repo.update_status.return_value = mock_conversation

        # Execute: Try to set AGENT_CLOSED (prio 4)
        result = service.close_conversation_with_priority(
            mock_conversation, ConversationStatus.AGENT_CLOSED
        )

        # Verify: Should return conversation without update
        assert result == mock_conversation
        mock_repo.update_status.assert_not_called()

        # 2. Try to close with higher priority (FAILED vs AGENT_CLOSED)
        # Setup: Current status is AGENT_CLOSED (prio 4)
        mock_conversation.status = ConversationStatus.AGENT_CLOSED.value

        # Execute: Try to set FAILED (prio 1)
        service.close_conversation_with_priority(
            mock_conversation, ConversationStatus.FAILED, reason="error"
        )

        # Verify: Should force update
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.FAILED,
            ended_at=ANY,
            initiated_by=None,
            reason="error",
            force=True,
        )

    def test_add_message_duplicate_error(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test add_message handling of DuplicateError."""
        # Setup
        mock_repo.find_by_id.return_value = mock_conversation
        mock_message_repo.create.side_effect = DuplicateError("Duplicate")

        message_create = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+1234567890",
            to_number="+0987654321",
            body="text",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
        )

        # Execute & Verify
        with pytest.raises(DuplicateError):
            service.add_message(mock_conversation, message_create)

        # Should verify it logged warning but didn't handle critical error
        # (logging verification is implicit unless we mock logger)

    def test_process_idle_conversations(self, service, mock_repo, mock_conversation):
        """Test processing of idle conversations."""
        # Setup
        idle_conv = mock_conversation
        idle_conv.status = ConversationStatus.PENDING.value
        mock_repo.find_idle_conversations.return_value = [idle_conv]
        mock_repo.update_status.return_value = idle_conv

        # Execute
        count = service.process_idle_conversations(idle_minutes=30, limit=10)

        # Verify
        assert count == 1
        mock_repo.update_status.assert_called_with(
            idle_conv.conv_id,
            ConversationStatus.IDLE_TIMEOUT,
            ended_at=ANY,
            initiated_by="system",
            reason="idle_timeout",
        )

    def test_process_idle_concurrency_recovery(
        self, service, mock_repo, mock_conversation
    ):
        """Test recovery from concurrency error during idle processing."""
        # Setup
        idle_conv = mock_conversation
        idle_conv.status = ConversationStatus.PENDING.value
        # Mock is_idle to return True
        with patch.object(Conversation, "is_idle", return_value=True):
            mock_repo.find_idle_conversations.return_value = [idle_conv]

            # First update fails, second succeeds
            mock_repo.update_status.side_effect = [
                ConcurrencyError("Conflict"),
                idle_conv,
            ]

            # Reload finds it still idle
            mock_repo.find_by_id.return_value = idle_conv

            # Execute
            count = service.process_idle_conversations(limit=10)

            # Verify
            assert count == 1
            assert mock_repo.update_status.call_count == 2
            mock_repo.find_by_id.assert_called_once()

    def test_transfer_conversation(self, service, mock_repo, mock_conversation):
        """Test transferring conversation to another agent."""
        # Setup
        mock_repo.update.return_value = mock_conversation

        # Execute
        new_user_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV_NEW"
        result = service.transfer_conversation(
            mock_conversation, new_user_id, reason="shift_change"
        )

        # Verify
        assert result == mock_conversation
        mock_repo.update.assert_called_once()
        call_args = mock_repo.update.call_args
        assert call_args[0][0] == mock_conversation.conv_id
        assert call_args[0][1]["user_id"] == new_user_id
        assert "transfer_history" in call_args[0][1]["context"]
        assert (
            call_args[0][1]["context"]["transfer_history"][0]["reason"]
            == "shift_change"
        )

    def test_escalate_conversation(self, service, mock_repo, mock_conversation):
        """Test escalating conversation to supervisor."""
        # Setup
        mock_repo.update.return_value = mock_conversation

        # Execute
        supervisor_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV_SUP"
        result = service.escalate_conversation(
            mock_conversation, supervisor_id, reason="complexity"
        )

        # Verify
        assert result == mock_conversation
        mock_repo.update.assert_called_once()
        call_args = mock_repo.update.call_args
        assert call_args[0][0] == mock_conversation.conv_id
        assert call_args[0][1]["status"] == ConversationStatus.PROGRESS.value
        assert "escalated" in call_args[0][1]["context"]
        assert call_args[0][1]["context"]["escalated"]["supervisor_id"] == supervisor_id

    def test_extend_expiration(self, service, mock_repo, mock_conversation):
        """Test extending conversation expiration."""
        # Setup
        mock_repo.extend_expiration.return_value = mock_conversation

        # Execute
        result = service.extend_expiration(mock_conversation, additional_minutes=60)

        # Verify
        assert result == mock_conversation
        mock_repo.extend_expiration.assert_called_with(mock_conversation.conv_id, 60)

    def test_check_closure_intent_auto_close(
        self,
        service,
        mock_repo,
        mock_conversation,
        mock_closure_detector,
        mock_message_repo,
    ):
        """Test auto-closing conversation when confidence is high."""
        # Setup
        mock_closure_detector.detect_closure_intent.return_value = {
            "should_close": True,
            "confidence": 0.9,  # > 0.8 threshold
            "reasons": ["High confidence"],
            "suggested_status": ConversationStatus.USER_CLOSED.value,
        }

        mock_message_repo.find_recent_by_conversation.return_value = []
        mock_repo.update_context.return_value = mock_conversation
        mock_repo.update_status.return_value = mock_conversation

        message = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="bye",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
        )

        # Execute
        result = service._check_closure_intent(mock_conversation, message)

        # Verify
        assert result is True
        mock_repo.update_context.assert_called_once()
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.USER_CLOSED,
            ended_at=ANY,
            initiated_by="system",
            reason="auto_closure_detection",
        )

    def test_add_message_concurrency_context_update(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test concurrency handling when updating context in add_message."""
        # Setup
        # Use IDLE_TIMEOUT to trigger reactivation path which has context update
        mock_conversation.status = ConversationStatus.IDLE_TIMEOUT.value

        # update_status succeeds
        mock_repo.update_status.return_value = mock_conversation

        # update_context fails first time, succeeds second time (retry via recursion/loop)
        # BUT add_message loop covers the whole block.
        # So:
        # 1. update_status OK
        # 2. update_context FAILS -> raise ConcurrencyError
        # 3. loop catches, reloads
        # 4. update_status OK
        # 5. update_context OK

        mock_repo.update_context.side_effect = [
            ConcurrencyError("Conflict"),
            mock_conversation,
        ]

        mock_repo.find_by_id.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        mock_message_repo.create.return_value = Message(
            msg_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
        )

        # Execute
        service.add_message(mock_conversation, message_dto)

        # Verify
        assert mock_repo.update_context.call_count == 2
        mock_repo.find_by_id.assert_called_once()

    def test_get_or_create_background_tasks_disabled(
        self, service, mock_repo, mock_conversation
    ):
        """Test get_or_create when background tasks are disabled."""
        # Setup
        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = mock_conversation

        # Mock settings
        with patch(
            "src.modules.conversation.services.conversation_service.settings"
        ) as mock_settings:
            mock_settings.toggle.enable_background_tasks = False

            # Execute
            service.get_or_create_conversation(
                owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                from_number="+5511999999999",
                to_number="+5511888888888",
            )

            # Verify
            mock_repo.cleanup_expired_conversations.assert_not_called()

    def test_get_or_create_expired_not_closed(
        self, service, mock_repo, mock_conversation
    ):
        """Test handling of conversation that is expired but not yet closed."""
        # Setup
        mock_conversation.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_conversation.status = ConversationStatus.PENDING.value  # Not closed

        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = mock_conversation

        # Mock create returning new conversation
        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FB2",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            version=1,
        )
        mock_repo.create.return_value = new_conv

        # Mock update_status for closing the expired one
        mock_repo.update_status.return_value = mock_conversation

        # Execute
        result = service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )

        # Verify
        assert result.conv_id == new_conv.conv_id
        # Should have closed the old one
        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.EXPIRED,
            ended_at=ANY,
            initiated_by="system",
            reason="expired_before_new",
        )
        # Should have created new one
        mock_repo.create.assert_called_once()

    def test_get_or_create_link_previous(self, service, mock_repo, mock_conversation):
        """Test linking to previous conversation when no active one exists."""
        # Setup
        mock_repo.calculate_session_key.return_value = "key"
        mock_repo.find_active_by_session_key.return_value = None

        # Mock finding previous conversation
        prev_conv = mock_conversation
        prev_conv.status = ConversationStatus.FAILED.value
        prev_conv.ended_at = datetime.now(timezone.utc)
        mock_repo.find_all_by_session_key.return_value = [prev_conv]

        # Mock create
        new_conv = Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FB2",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            version=1,
        )
        mock_repo.create.return_value = new_conv

        # Execute
        result = service.get_or_create_conversation(
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            from_number="+5511999999999",
            to_number="+5511888888888",
        )

        # Verify
        assert result.conv_id == new_conv.conv_id
        mock_repo.create.assert_called_once()
        call_args = mock_repo.create.call_args[0][0]
        assert call_args["metadata"]["previous_conversation_id"] == prev_conv.conv_id
        assert (
            call_args["metadata"]["previous_status"] == ConversationStatus.FAILED.value
        )
        assert call_args["metadata"]["recovery_mode"] is True

    def test_add_message_max_retries_exceeded(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test add_message raises ConcurrencyError after max retries."""
        # Setup
        mock_conversation.status = ConversationStatus.IDLE_TIMEOUT.value

        # Always fail with ConcurrencyError
        mock_repo.update_status.side_effect = ConcurrencyError("Conflict")
        mock_repo.find_by_id.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute & Verify
        with pytest.raises(ConcurrencyError):
            service.add_message(mock_conversation, message_dto)

        # Should be 6 calls: 3 for add_message + 3 for close_conversation (triggered by error handling)
        assert mock_repo.update_status.call_count == 6

    def test_add_message_critical_error(
        self, service, mock_repo, mock_message_repo, mock_conversation
    ):
        """Test handling of critical error in add_message."""
        # Setup
        mock_message_repo.create.side_effect = Exception("Critical DB Error")
        mock_repo.update_context.return_value = mock_conversation
        mock_repo.update_status.return_value = mock_conversation

        message_dto = MessageCreateDTO(
            conv_id=mock_conversation.conv_id,
            owner_id=mock_conversation.owner_id,
            from_number="+5511999999999",
            to_number="+5511888888888",
            body="Hello",
            message_type=MessageType.TEXT,
            message_owner=MessageOwner.USER,
            channel="whatsapp",
        )

        # Execute & Verify
        with pytest.raises(Exception):
            service.add_message(mock_conversation, message_dto)

        # Verify critical error handling (closes conversation as FAILED)
        mock_repo.update_context.assert_called_once()
        # Check context updated with failure details
        ctx_call = mock_repo.update_context.call_args[0][1]
        assert "failure_details" in ctx_call
        assert ctx_call["failure_details"]["error"] == "Critical DB Error"

        mock_repo.update_status.assert_called_with(
            mock_conversation.conv_id,
            ConversationStatus.FAILED,
            ended_at=ANY,
            initiated_by="system",
            reason="critical_error",
        )

    def test_force_close_max_retries(self, service, mock_repo, mock_conversation):
        """Test force_close raises ConcurrencyError after max retries."""
        # Setup
        mock_repo.update_status.side_effect = ConcurrencyError("Conflict")
        mock_repo.find_by_id.return_value = mock_conversation

        # Execute & Verify
        with pytest.raises(ConcurrencyError):
            service._force_close(
                mock_conversation, ConversationStatus.FAILED, auto_retry=True
            )

        assert mock_repo.update_status.call_count == 3
