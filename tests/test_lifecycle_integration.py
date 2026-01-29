import os
from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock, Mock

from dotenv import load_dotenv

# Set fake env vars for testing before importing application modules
load_dotenv(os.path.join(os.path.dirname(__file__), ".env.test"), override=True)

from src.core.utils import get_logger  # noqa: E402
from src.modules.conversation.dtos.message_dto import \
    MessageCreateDTO  # noqa: E402
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus  # noqa: E402
from src.modules.conversation.enums.message_owner import \
    MessageOwner  # noqa: E402
from src.modules.conversation.models.conversation import \
    Conversation  # noqa: E402
from src.modules.conversation.services.conversation_service import \
    ConversationService  # noqa: E402

logger = get_logger(__name__)


def test_complete_conversation_lifecycle():
    # 1. Setup Mocks
    repo = MagicMock()
    msg_repo = MagicMock()
    closure = MagicMock()  # Mock closure detector logic

    # Real components for integration test
    from src.modules.conversation.components.conversation_finder import ConversationFinder
    from src.modules.conversation.components.conversation_lifecycle import ConversationLifecycle
    
    finder = ConversationFinder(repo)
    lifecycle = ConversationLifecycle(repo)

    # Configure ClosureDetector mock defaults
    closure.should_close_conversation.return_value = (False, None, None)
    closure.detect_cancellation_in_pending.return_value = False
    closure.detect_intent.return_value = Mock(should_close=False)

    service = ConversationService(
        conversation_repo=repo,
        message_repo=msg_repo,
        finder=finder,
        lifecycle=lifecycle,
        closer=closure
    )

    owner_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    conv_id = "01ARZ3NDEKTSV4RRFFQ69G5FAW"
    from_number = "+5511999999999"
    to_number = "+5511888888888"

    # Helper to create valid conversation objects
    def create_conv_mock(status=ConversationStatus.PENDING, context=None):
        return Conversation(
            conv_id=conv_id,
            owner_id=owner_id,
            from_number=from_number,
            to_number=to_number,
            channel="whatsapp",
            status=status.value if hasattr(status, "value") else status,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            context=context or {},
            version=1,
        )

    # Mock get_or_create_conversation behavior
    # Scenario: No active conversation found, creates new one
    repo.find_active_by_session_key.return_value = None

    # Mock create() to return a new conversation
    pending_conv = create_conv_mock(ConversationStatus.PENDING)
    repo.create.return_value = pending_conv

    # --- Step 1: Create Conversation ---
    conv = service.get_or_create_conversation(
        owner_id=owner_id,
        from_number=from_number,
        to_number=to_number,
        channel="whatsapp",
    )

    assert conv.status == ConversationStatus.PENDING.value
    repo.find_active_by_session_key.assert_called()
    repo.create.assert_called()

    # --- Step 2: User Message (PENDING -> PENDING) ---
    user_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id=owner_id,
        from_number=from_number,
        to_number=to_number,
        body="Preciso de ajuda",
        message_owner=MessageOwner.USER,
    )

    # Mock find_by_id for reload
    repo.find_by_id.return_value = pending_conv

    service.add_message(conv, user_msg)

    # Assert message was added
    msg_repo.create.assert_called()

    # Verify status didn't change (still PENDING)
    # add_message might call update_status if transition happens,
    # but here it shouldn't for PENDING->PENDING.
    # actually add_message logic for USER message in PENDING doesn't
    # change status unless configured.

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PENDING.value

    # --- Step 3: Agent Message (PENDING -> PROGRESS) ---
    agent_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id=owner_id,
        from_number=to_number,
        to_number=from_number,
        body="Olá! Como posso ajudar?",
        message_owner=MessageOwner.AGENT,
    )

    # Mock update_status to return updated conversation
    progress_conv = create_conv_mock(
        ConversationStatus.PROGRESS,
        context={"accepted_by": {"agent_type": "agent"}},
    )
    repo.update_status.return_value = progress_conv
    repo.find_by_id.return_value = progress_conv  # Return new state after reload

    service.add_message(conv, agent_msg)

    # Verify status transition call
    repo.update_status.assert_called_with(
        conv.conv_id,
        ConversationStatus.PROGRESS,
        initiated_by="agent",
        reason="agent_acceptance",
        expires_at=ANY,
        ended_at=None,
    )

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert "accepted_by" in conv.context
    assert conv.context["accepted_by"]["agent_type"] == MessageOwner.AGENT.value

    # --- Step 4: Process Idle Conversations (PROGRESS -> IDLE_TIMEOUT) ---

    # Mock find_idle_candidates to return our conversation
    repo.find_idle_candidates.return_value = [progress_conv]

    # Mock update_status for idle timeout
    idle_conv = create_conv_mock(ConversationStatus.IDLE_TIMEOUT)
    repo.update_status.return_value = idle_conv

    processed_count = service.process_idle_conversations(idle_minutes=-1)

    logger.info("Processed idle conversations", count=processed_count)
    assert processed_count == 1

    # Verify update_status was called for timeout
    repo.update_status.assert_called_with(
        conv.conv_id,
        ConversationStatus.IDLE_TIMEOUT,
        reason="inactivity_timeout",
        ended_at=ANY,
        initiated_by="system",
        expires_at=None,
    )

    # Update our local view
    repo.find_by_id.return_value = idle_conv
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.IDLE_TIMEOUT.value

    # --- Step 5: User Message Reactivation (IDLE_TIMEOUT -> PROGRESS) ---
    user_msg2 = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id=owner_id,
        from_number=from_number,
        to_number=to_number,
        body="Ainda está aí?",
        message_owner=MessageOwner.USER,
    )

    # Mock update_status for reactivation
    reactivated_conv = create_conv_mock(
        ConversationStatus.PROGRESS,
        context={"reactivated_from_idle": {"triggered_by": "user"}},
    )
    repo.update_status.return_value = reactivated_conv
    repo.find_by_id.return_value = reactivated_conv

    service.add_message(conv, user_msg2)

    # Verify reactivation call
    repo.update_status.assert_called_with(
        conv.conv_id,
        ConversationStatus.PROGRESS,
        initiated_by="user",
        reason="user_reactivation",
        ended_at=None,
        expires_at=None,
    )

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert "reactivated_from_idle" in conv.context

    # --- Step 6: Close Conversation (PROGRESS -> AGENT_CLOSED) ---

    # Mock update_status for closing
    closed_conv = create_conv_mock(ConversationStatus.AGENT_CLOSED)
    repo.update_status.return_value = closed_conv
    repo.find_by_id.return_value = closed_conv

    service.close_conversation(conv, ConversationStatus.AGENT_CLOSED)

    # Verify close call
    repo.update_status.assert_called_with(
        conv.conv_id,
        ConversationStatus.AGENT_CLOSED,
        ended_at=ANY,
        initiated_by="system",
        reason="closed_by_service",
        expires_at=None,
    )

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.AGENT_CLOSED.value
