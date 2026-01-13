import sys
import os
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.models.domain import Conversation
from src.models.enums import ConversationStatus
from src.services.conversation_service import ConversationService
from src.utils.custom_ulid import generate_ulid

# Setup simple logger
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_priority_closure():
    logger.info("Starting Priority Closure Test")
    
    # Mock Repository
    mock_repo = MagicMock()
    
    # Mock Service
    # We mock message_repo and closure_detector as they are not needed for this test
    service = ConversationService(conversation_repo=mock_repo, message_repo=MagicMock(), closure_detector=MagicMock())
    
    # Helper to create conv
    def create_conv(status):
        return Conversation(
            conv_id=generate_ulid(),
            owner_id=generate_ulid(),
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=status.value,
            started_at=datetime.now(timezone.utc).isoformat()
        )

    # 1. Normal Closure (PENDING -> AGENT_CLOSED)
    # Should call normal close_conversation
    logger.info("Test 1: Normal Closure")
    conv = create_conv(ConversationStatus.PENDING)
    mock_repo.update_status.return_value = create_conv(ConversationStatus.AGENT_CLOSED)
    
    service.close_conversation_with_priority(conv, ConversationStatus.AGENT_CLOSED)
    
    mock_repo.update_status.assert_called_with(
        conv.conv_id, 
        ConversationStatus.AGENT_CLOSED, 
        ended_at=ANY, 
        initiated_by=None, 
        reason=None
    )
    
    # 2. Priority Override (EXPIRED -> FAILED)
    # Should Override because FAILED(1) > EXPIRED(5)
    logger.info("Test 2: Priority Override (EXPIRED -> FAILED)")
    conv_expired = create_conv(ConversationStatus.EXPIRED)
    mock_repo.reset_mock()
    
    service.close_conversation_with_priority(conv_expired, ConversationStatus.FAILED, reason="Critical Error")
    
    # Verify force=True was used
    mock_repo.update_status.assert_called_with(
        conv_expired.conv_id, 
        ConversationStatus.FAILED, 
        ended_at=ANY, 
        initiated_by=None, 
        reason="Critical Error",
        force=True
    )
    
    # 3. Priority Ignore (USER_CLOSED -> EXPIRED)
    # Should Ignore because EXPIRED(5) < USER_CLOSED(2)
    logger.info("Test 3: Priority Ignore (USER_CLOSED -> EXPIRED)")
    conv_user_closed = create_conv(ConversationStatus.USER_CLOSED)
    mock_repo.reset_mock()
    
    result = service.close_conversation_with_priority(conv_user_closed, ConversationStatus.EXPIRED)
    
    # Should NOT call update_status
    mock_repo.update_status.assert_not_called()
    assert result.status == ConversationStatus.USER_CLOSED.value
    
    # 4. Priority Ignore (FAILED -> FAILED)
    # Equal priority should be ignored
    logger.info("Test 4: Equal Priority Ignore")
    conv_failed = create_conv(ConversationStatus.FAILED)
    mock_repo.reset_mock()
    
    service.close_conversation_with_priority(conv_failed, ConversationStatus.FAILED)
    mock_repo.update_status.assert_not_called()

    logger.info("All tests passed!")

if __name__ == "__main__":
    test_priority_closure()
