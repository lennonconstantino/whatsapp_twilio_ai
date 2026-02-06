import os
import sys
from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock, AsyncMock

import pytest
from dotenv import load_dotenv

# Set environment variables for testing before importing application modules
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env.test"), override=True)

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Setup simple logger
import logging  # noqa: E402

from src.core.utils.custom_ulid import generate_ulid  # noqa: E402
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus  # noqa: E402
from src.modules.conversation.models.conversation import \
    Conversation  # noqa: E402
from src.modules.conversation.services.conversation_service import \
    ConversationService  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_priority_closure():
    logger.info("Starting Priority Closure Test")

    # Mock Repository
    mock_repo = MagicMock()
    mock_repo.update_status = AsyncMock()
    
    # Real Lifecycle to test priority logic
    from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
    lifecycle = ConversationLifecycle(mock_repo)

    # Mock Service
    service = ConversationService(
        conversation_repo=mock_repo,
        message_repo=MagicMock(),
        finder=MagicMock(),
        lifecycle=lifecycle,
        closer=MagicMock(),
    )

    # Helper to create conv
    def create_conv(status):
        return Conversation(
            conv_id=generate_ulid(),
            owner_id=generate_ulid(),
            from_number="123",
            to_number="456",
            channel="whatsapp",
            status=status.value,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    # 1. Normal Closure (PENDING -> AGENT_CLOSED)
    # Should call normal close_conversation
    logger.info("Test 1: Normal Closure")
    conv = create_conv(ConversationStatus.PENDING)
    mock_repo.update_status.return_value = create_conv(ConversationStatus.AGENT_CLOSED)

    await service.close_conversation_with_priority(
        conv, ConversationStatus.AGENT_CLOSED, initiated_by="agent", reason="done"
    )

    mock_repo.update_status.assert_called_with(
        conv.conv_id,
        ConversationStatus.AGENT_CLOSED,
        initiated_by="agent",
        reason="done",
        ended_at=ANY,
        expires_at=None,
    )

    # 2. Priority Override (EXPIRED -> FAILED)
    # Should Override because FAILED(1) > EXPIRED(5)
    logger.info("Test 2: Priority Override (EXPIRED -> FAILED)")
    conv_expired = create_conv(ConversationStatus.EXPIRED)
    mock_repo.reset_mock()

    await service.close_conversation_with_priority(
        conv_expired, ConversationStatus.FAILED, initiated_by="system", reason="Critical Error"
    )

    # Verify force=True was used
    mock_repo.update_status.assert_called_with(
        conv_expired.conv_id,
        ConversationStatus.FAILED,
        ended_at=ANY,
        initiated_by="system",
        reason="Critical Error",
        force=True,
    )

    # 3. Priority Ignore (USER_CLOSED -> EXPIRED)
    # Should Ignore because EXPIRED(5) < USER_CLOSED(2)
    logger.info("Test 3: Priority Ignore (USER_CLOSED -> EXPIRED)")
    conv_user_closed = create_conv(ConversationStatus.USER_CLOSED)
    mock_repo.reset_mock()

    result = await service.close_conversation_with_priority(
        conv_user_closed, ConversationStatus.EXPIRED, initiated_by="system", reason="expired"
    )

    # Should NOT call update_status
    mock_repo.update_status.assert_not_called()
    assert result.status == ConversationStatus.USER_CLOSED.value

    # 4. Priority Ignore (FAILED -> FAILED)
    # Equal priority should be ignored
    logger.info("Test 4: Equal Priority Ignore")
    conv_failed = create_conv(ConversationStatus.FAILED)
    mock_repo.reset_mock()

    await service.close_conversation_with_priority(conv_failed, ConversationStatus.FAILED)
    mock_repo.update_status.assert_not_called()

    logger.info("All tests passed!")
