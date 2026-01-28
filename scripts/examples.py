"""
Example usage script demonstrating the Owner Project API.

This script shows how to:
1. Create owners and users
2. Create conversations
3. Send messages
4. Handle closure detection
5. Process timeouts
"""

import random
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings
from src.core.utils import get_db, get_logger
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums import (ConversationStatus,
                                            MessageDirection, MessageOwner,
                                            MessageType)
from src.modules.conversation.services.conversation_service import \
    ConversationService
from src.modules.identity.repositories.owner_repository import OwnerRepository


logger = get_logger(__name__)

# Mock valid ULID for owner_id
# MOCK_OWNER_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def example_create_owner():
    """Example: Create or get an owner."""
    logger.info("=== Example: Create/Get Owner ===")

    db = get_db()
    repo = OwnerRepository(db)
    email = "example@test.com"

    owner = repo.find_by_email(email)
    if owner:
        logger.info("Found existing owner", owner_id=owner.owner_id)
    else:
        owner = repo.create_owner(name="Example Owner", email=email)
        logger.info("Created new owner", owner_id=owner.owner_id)

    return owner


def example_create_conversation(owner_id):
    """Example: Create a conversation."""
    logger.info("=== Example: Create Conversation ===")

    service = ConversationService()

    # Generate random numbers to avoid collisions in examples
    suffix_from = "".join([str(random.randint(0, 9)) for _ in range(8)])
    suffix_to = "".join([str(random.randint(0, 9)) for _ in range(8)])
    from_number = f"+55119{suffix_from}"
    to_number = f"+55119{suffix_to}"

    # Create or get existing conversation
    conversation = service.get_or_create_conversation(
        owner_id=owner_id,
        from_number=from_number,
        to_number=to_number,
        channel="whatsapp",
    )

    logger.info(
        "Conversation created/retrieved",
        conv_id=conversation.conv_id,
        status=conversation.status,
    )

    return conversation


def example_add_messages(conversation):
    """Example: Add messages to a conversation."""
    logger.info("=== Example: Add Messages ===")

    service = ConversationService()

    # User message
    user_msg = MessageCreateDTO(
        conv_id=conversation.conv_id,
        owner_id=conversation.owner_id,
        from_number=conversation.from_number,
        to_number=conversation.to_number,
        body="Olá! Gostaria de saber sobre seus serviços.",
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=MessageType.TEXT,
    )

    message1 = service.message_repo.create(user_msg.model_dump())
    logger.info("User message added", msg_id=message1.msg_id if message1 else None)

    # Agent response
    agent_msg = MessageCreateDTO(
        conv_id=conversation.conv_id,
        owner_id=conversation.owner_id,
        from_number=conversation.to_number,
        to_number=conversation.from_number,
        body="Olá! Terei prazer em ajudá-lo. Oferecemos diversos serviços...",
        direction=MessageDirection.OUTBOUND,
        message_owner=MessageOwner.AGENT,
        message_type=MessageType.TEXT,
    )

    message2 = service.message_repo.create(agent_msg.model_dump())
    logger.info("Agent message added", msg_id=message2.msg_id if message2 else None)

    return message1, message2


def example_closure_detection(conversation):
    """Example: Closure detection."""
    logger.info("=== Example: Closure Detection ===")

    service = ConversationService()

    # Message with closure intent
    closure_msg = MessageCreateDTO(
        conv_id=conversation.conv_id,
        owner_id=conversation.owner_id,
        from_number=conversation.from_number,
        to_number=conversation.to_number,
        body="Obrigado! Foi muito útil. Tchau!",
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=MessageType.TEXT,
    )

    message = service.message_repo.create(closure_msg.model_dump())
    logger.info("Closure message added", msg_id=message.msg_id if message else None)

    # Check if conversation was closed or marked for closure
    updated_conv = service.get_conversation_by_id(conversation.conv_id)
    if updated_conv:
        logger.info(
            "Conversation status after closure detection",
            status=updated_conv.status,
            context=updated_conv.context,
        )


def example_list_messages(conversation):
    """Example: List conversation messages."""
    logger.info("=== Example: List Messages ===\n")

    service = ConversationService()

    # Get recent messages
    messages = service.message_repo.find_by_conversation(conversation.conv_id)

    logger.info(f"Found {len(messages)} messages:")

    for msg in messages:
        logger.info(
            "Message",
            msg_id=msg.msg_id,
            owner=msg.message_owner,
            body=msg.body[:50] + "..." if len(msg.body) > 50 else msg.body,
        )


def example_close_conversation(conversation):
    """Example: Manually close a conversation."""
    logger.info("=== Example: Close Conversation ===\n")

    service = ConversationService()

    # Update to PROGRESS first to allow closing by agent
    service.conversation_repo.update_status(
        conversation.conv_id,
        ConversationStatus.PROGRESS,
        initiated_by="system",
        reason="Example progress",
    )

    # Refresh conversation
    conversation = service.conversation_repo.find_by_id(
        conversation.conv_id, id_column="conv_id"
    )

    closed = service.close_conversation(
        conversation=conversation,
        status=ConversationStatus.AGENT_CLOSED,
        initiated_by="agent",
        reason="Conversation completed successfully",
    )

    if closed:
        logger.info(
            "Conversation closed",
            conv_id=closed.conv_id,
            status=closed.status,
            ended_at=closed.ended_at,
        )


def example_process_timeouts():
    """Example: Process expired and idle conversations."""
    logger.info("=== Example: Process Timeouts ===")

    service = ConversationService()

    # Process expired conversations
    expired_count = service.process_expired_conversations(limit=10)
    logger.info(f"Processed {expired_count} expired conversations")

    # Process idle conversations
    idle_count = service.process_idle_conversations(idle_minutes=30, limit=10)
    logger.info(f"Processed {idle_count} idle conversations")


def example_extend_conversation(conversation):
    """Example: Extend conversation expiration."""
    logger.info("=== Example: Extend Conversation ===")

    service = ConversationService()

    extended = service.extend_expiration(
        conversation=conversation, additional_minutes=60
    )

    if extended:
        logger.info(
            "Conversation extended",
            conv_id=extended.conv_id,
            new_expires_at=extended.expires_at,
        )


def example_list_active_conversations(owner_id):
    """Example: List all active conversations for an owner."""
    logger.info("=== Example: List Active Conversations ===")

    service = ConversationService()
    conversations = service.get_active_conversations(owner_id=owner_id, limit=50)

    logger.info(f"Found {len(conversations)} active conversations")

    for conv in conversations:
        logger.info(
            "Active conversation",
            conv_id=conv.conv_id,
            from_number=conv.from_number,
            status=conv.status,
            started_at=conv.started_at,
        )


def main():
    """Run all examples."""
    logger.info("Starting Owner Project examples...")

    try:
        # Example 0: Create/Get Owner
        owner = example_create_owner()
        owner_id = owner.owner_id

        # Example 1: Create conversation
        conversation = example_create_conversation(owner_id)

        # Example 2: Add messages
        example_add_messages(conversation)

        # Example 3: List messages
        example_list_messages(conversation)

        # Example 4: Extend conversation
        example_extend_conversation(conversation)

        # Example 5: Closure detection
        example_closure_detection(conversation)

        # Example 6: List active conversations
        example_list_active_conversations(owner_id)

        # Example 7: Process timeouts
        example_process_timeouts()

        # Example 8: Close conversation (if still open)
        # Assuming get_conversation_by_id exists in service or repo
        # Using service.get_or_create to ensure we have a fresh object or direct repo access if preferred
        # Here we use the service method if available, or repo
        service = ConversationService()
        updated_conv = service.conversation_repo.find_by_id(
            conversation.conv_id, id_column="conv_id"
        )

        if updated_conv and updated_conv.is_active():
            example_close_conversation(updated_conv)

        logger.info("All examples completed successfully!")

    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
