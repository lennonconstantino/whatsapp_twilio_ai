
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, ANY, patch

from src.core.utils.exceptions import ConcurrencyError
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.models.conversation import Conversation
from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle

class TestConversationLifecycle:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def lifecycle(self, mock_repo):
        return ConversationLifecycle(mock_repo)

    @pytest.fixture
    def mock_conv(self):
        return Conversation(
            conv_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAW",
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=ConversationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
            version=1,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1) # Expired by default for expiration tests
        )

    def test_transition_valid(self, lifecycle, mock_repo, mock_conv):
        """Test valid transition."""
        mock_repo.update_status.return_value = mock_conv
        
        lifecycle.transition_to(
            mock_conv,
            ConversationStatus.PROGRESS,
            reason="test",
            initiated_by="agent"
        )
        
        mock_repo.update_status.assert_called_with(
            mock_conv.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="agent",
            reason="test",
            ended_at=None,
            expires_at=None
        )

    def test_transition_invalid(self, lifecycle, mock_conv):
        """Test invalid transition raises ValueError."""
        # PENDING -> IDLE_TIMEOUT is invalid
        with pytest.raises(ValueError):
            lifecycle.transition_to(
                mock_conv,
                ConversationStatus.IDLE_TIMEOUT,
                reason="invalid",
                initiated_by="system"
            )

    def test_transition_handoff_to_progress(self, lifecycle, mock_repo, mock_conv):
        """Test valid transition from HUMAN_HANDOFF to PROGRESS."""
        mock_conv.status = ConversationStatus.HUMAN_HANDOFF.value
        mock_repo.update_status.return_value = mock_conv
        
        lifecycle.transition_to(
            mock_conv,
            ConversationStatus.PROGRESS,
            reason="release_to_bot",
            initiated_by="agent"
        )
        
        mock_repo.update_status.assert_called_with(
            mock_conv.conv_id,
            ConversationStatus.PROGRESS,
            initiated_by="agent",
            reason="release_to_bot",
            ended_at=None,
            expires_at=None
        )

    def test_transition_expired_validity(self, lifecycle, mock_repo, mock_conv):
        """Test expiration transitions."""
        # PENDING -> EXPIRED
        mock_conv.status = ConversationStatus.PENDING.value
        mock_repo.update_status.return_value = mock_conv
        
        lifecycle.transition_to(
            mock_conv,
            ConversationStatus.EXPIRED,
            reason="ttl",
            initiated_by="system"
        )
        mock_repo.update_status.assert_called()
        
        # PROGRESS -> EXPIRED
        mock_conv.status = ConversationStatus.PROGRESS.value
        lifecycle.transition_to(
            mock_conv,
            ConversationStatus.EXPIRED,
            reason="ttl",
            initiated_by="system"
        )
        mock_repo.update_status.assert_called()

    def test_transition_concurrency_error(self, lifecycle, mock_repo, mock_conv):
        """Test concurrency error propagation."""
        mock_repo.update_status.return_value = None # Simulate optimistic lock failure
        
        with pytest.raises(ConcurrencyError):
            lifecycle.transition_to(
                mock_conv,
                ConversationStatus.PROGRESS,
                reason="test",
                initiated_by="agent"
            )

    def test_transition_priority_override(self, lifecycle, mock_repo, mock_conv):
        """Test priority override (Lower -> Higher Priority)."""
        # Current: USER_CLOSED (Prio 2)
        mock_conv.status = ConversationStatus.USER_CLOSED.value
        mock_repo.update_status.return_value = mock_conv
        
        # Try: FAILED (Prio 1)
        lifecycle.transition_to_with_priority(
            mock_conv,
            ConversationStatus.FAILED,
            reason="error",
            initiated_by="system"
        )
        
        mock_repo.update_status.assert_called()
        args, kwargs = mock_repo.update_status.call_args
        assert args[1] == ConversationStatus.FAILED
        assert kwargs.get("force") is True

    def test_transition_priority_ignore(self, lifecycle, mock_repo, mock_conv):
        """Test priority ignore (Higher -> Lower Priority)."""
        # Current: USER_CLOSED (Prio 2)
        mock_conv.status = ConversationStatus.USER_CLOSED.value
        
        # Try: AGENT_CLOSED (Prio 4)
        lifecycle.transition_to_with_priority(
            mock_conv,
            ConversationStatus.AGENT_CLOSED,
            reason="done",
            initiated_by="agent"
        )
        
        mock_repo.update_status.assert_not_called()

    def test_extend_expiration(self, lifecycle, mock_repo, mock_conv):
        """Test extend expiration."""
        mock_repo.update.return_value = mock_conv
        
        lifecycle.extend_expiration(mock_conv, 60)
        
        mock_repo.update.assert_called()
        args = mock_repo.update.call_args[0]
        assert "expires_at" in args[1]

    def test_extend_expiration_concurrency_error(self, lifecycle, mock_repo, mock_conv):
        """Test extend expiration concurrency error."""
        mock_repo.update.return_value = None
        
        with pytest.raises(ConcurrencyError):
            lifecycle.extend_expiration(mock_conv, 60)

    def test_transfer_owner(self, lifecycle, mock_repo, mock_conv):
        """Test transfer owner."""
        mock_repo.update.return_value = mock_conv
        
        lifecycle.transfer_owner(
            mock_conv,
            "NEW_USER_ID",
            "shift_change"
        )
        
        mock_repo.update.assert_called()
        args = mock_repo.update.call_args[0]
        assert args[1]["user_id"] == "NEW_USER_ID"
        assert "transfer_history" in args[1]["context"]

    def test_transfer_owner_concurrency_error(self, lifecycle, mock_repo, mock_conv):
        """Test transfer owner concurrency error."""
        mock_repo.update.return_value = None
        
        with pytest.raises(ConcurrencyError):
            lifecycle.transfer_owner(mock_conv, "NEW_USER_ID", "reason")

    def test_escalate(self, lifecycle, mock_repo, mock_conv):
        """Test escalate."""
        mock_repo.update.return_value = mock_conv
        
        lifecycle.escalate(
            mock_conv,
            "SUPERVISOR_ID",
            "help"
        )
        
        mock_repo.update.assert_called()
        args = mock_repo.update.call_args[0]
        assert args[1]["status"] == ConversationStatus.PROGRESS.value
        assert "escalated" in args[1]["context"]

    def test_escalate_concurrency_error(self, lifecycle, mock_repo, mock_conv):
        """Test escalate concurrency error."""
        mock_repo.update.return_value = None
        
        with pytest.raises(ConcurrencyError):
            lifecycle.escalate(mock_conv, "sid", "reason")

    def test_process_expirations(self, lifecycle, mock_repo, mock_conv):
        """Test process expirations."""
        mock_repo.find_expired_candidates.return_value = [mock_conv]
        mock_repo.update_status.return_value = mock_conv # success
        
        processed = lifecycle.process_expirations(limit=10)
        
        assert processed == 1
        mock_repo.update_status.assert_called_with(
            mock_conv.conv_id,
            ConversationStatus.EXPIRED,
            reason="ttl_expired",
            initiated_by="system",
            ended_at=ANY,
            expires_at=None
        )

    def test_process_expirations_not_expired(self, lifecycle, mock_repo, mock_conv):
        """Test process expirations skips non-expired."""
        mock_conv.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_repo.find_expired_candidates.return_value = [mock_conv]
        
        processed = lifecycle.process_expirations(limit=10)
        
        assert processed == 0
        mock_repo.update_status.assert_not_called()

    def test_process_expirations_concurrency_error(self, lifecycle, mock_repo, mock_conv):
        """Test process expirations handles concurrency error."""
        mock_repo.find_expired_candidates.return_value = [mock_conv]
        mock_repo.update_status.return_value = None # trigger error in transition_to -> check ConcurrencyError handling in process loop
        
        # transition_to raises ConcurrencyError if update_status returns None
        # process_expirations catches ConcurrencyError and logs warning
        
        processed = lifecycle.process_expirations(limit=10)
        
        assert processed == 0
        # Should catch and continue

    def test_process_idle_timeouts(self, lifecycle, mock_repo, mock_conv):
        """Test process idle timeouts."""
        mock_conv.status = ConversationStatus.PROGRESS.value
        mock_repo.find_idle_candidates.return_value = [mock_conv]
        mock_repo.update_status.return_value = mock_conv
        
        processed = lifecycle.process_idle_timeouts(idle_minutes=30, limit=10)
        
        assert processed == 1
        mock_repo.update_status.assert_called_with(
            mock_conv.conv_id,
            ConversationStatus.IDLE_TIMEOUT,
            reason="inactivity_timeout",
            initiated_by="system",
            ended_at=None,
            expires_at=None
        )

    def test_process_idle_timeouts_wrong_status(self, lifecycle, mock_repo, mock_conv):
        """Test process idle timeouts skips non-progress."""
        mock_conv.status = ConversationStatus.PENDING.value
        mock_repo.find_idle_candidates.return_value = [mock_conv]
        
        processed = lifecycle.process_idle_timeouts(idle_minutes=30, limit=10)
        
        assert processed == 0
        mock_repo.update_status.assert_not_called()

    def test_process_idle_timeouts_exception(self, lifecycle, mock_repo, mock_conv):
        """Test process idle timeouts handles generic exception."""
        mock_conv.status = ConversationStatus.PROGRESS.value
        mock_repo.find_idle_candidates.return_value = [mock_conv]
        mock_repo.update_status.side_effect = Exception("Error")
        
        processed = lifecycle.process_idle_timeouts(idle_minutes=30, limit=10)
        
        assert processed == 0
        # Should catch and continue

    def test_log_history_exception(self, lifecycle, mock_repo, mock_conv):
        """Test exception logging in log_transition_history."""
        mock_repo.update_status.return_value = mock_conv
        mock_repo.log_transition_history.side_effect = Exception("Log Error")
        
        with patch("src.modules.conversation.components.conversation_lifecycle.logger") as mock_logger:
            lifecycle.transition_to(
                mock_conv,
                ConversationStatus.PROGRESS,
                reason="test",
                initiated_by="agent"
            )
            
            mock_logger.error.assert_called_with(
                "Failed to log transition history",
                error="Log Error",
                conv_id=mock_conv.conv_id
            )
