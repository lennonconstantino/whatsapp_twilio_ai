"""
Example usage script demonstrating the Owner Project API.

This script shows how to:
1. Create owners and users
2. Create conversations
3. Send messages
4. Handle closure detection
5. Process timeouts
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timedelta
from config import settings
from utils import get_db, configure_logging, get_logger
from repositories import (
    OwnerRepository,
    UserRepository,
    ConversationRepository,
    MessageRepository
)
from services import ConversationService, conversation_service
from models import (
    MessageCreate,
    MessageDirection,
    MessageOwner,
    MessageType,
    ConversationStatus
)

configure_logging()
logger = get_logger(__name__)


def example_create_conversation():
    """Example: Create a conversation."""
    logger.info("=== Example: Create Conversation ===")
    
    service = ConversationService()
    
    # Create or get existing conversation
    conversation = service.get_or_create_conversation(
        owner_id=1,
        from_number="+5511988887777",
        to_number="+5511999998888",
        channel="whatsapp"
    )
    
    logger.info(
        "Conversation created/retrieved",
        conv_id=conversation.conv_id,
        status=conversation.status.value
    )
    
    return conversation


def example_add_messages(conversation):
    """Example: Add messages to a conversation."""
    logger.info("=== Example: Add Messages ===")
    
    service = ConversationService()
    
    # User message
    user_msg = MessageCreate(
        conv_id=conversation.conv_id,
        from_number="+5511988887777",
        to_number="+5511999998888",
        body="Olá! Gostaria de saber sobre seus serviços.",
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=MessageType.TEXT
    )
    
    message1 = service.add_message(conversation, user_msg)
    logger.info("User message added", msg_id=message1.msg_id if message1 else None)
    
    # Agent response
    agent_msg = MessageCreate(
        conv_id=conversation.conv_id,
        from_number="+5511999998888",
        to_number="+5511988887777",
        body="Olá! Terei prazer em ajudá-lo. Oferecemos diversos serviços...",
        direction=MessageDirection.OUTBOUND,
        message_owner=MessageOwner.AGENT,
        message_type=MessageType.TEXT
    )
    
    message2 = service.add_message(conversation, agent_msg)
    logger.info("Agent message added", msg_id=message2.msg_id if message2 else None)
    
    return message1, message2


def example_closure_detection(conversation):
    """Example: Closure detection."""
    logger.info("=== Example: Closure Detection ===")
    
    service = ConversationService()
    
    # Message with closure intent
    closure_msg = MessageCreate(
        conv_id=conversation.conv_id,
        from_number="+5511988887777",
        to_number="+5511999998888",
        body="Obrigado! Foi muito útil. Tchau!",
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=MessageType.TEXT
    )
    
    message = service.add_message(conversation, closure_msg)
    logger.info("Closure message added", msg_id=message.msg_id if message else None)
    
    # Check if conversation was closed or marked for closure
    updated_conv = service.get_conversation_by_id(conversation.conv_id)
    if updated_conv:
        logger.info(
            "Conversation status after closure detection",
            status=updated_conv.status.value,
            context=updated_conv.context
        )


def example_list_messages(conversation):
    """Example: List conversation messages."""
    logger.info("=== Example: List Messages ===")
    
    service = ConversationService()
    messages = service.get_conversation_messages(conversation.conv_id)
    
    logger.info(f"Found {len(messages)} messages")
    
    for msg in messages:
        logger.info(
            "Message",
            msg_id=msg.msg_id,
            owner=msg.message_owner.value,
            body=msg.body[:50] + "..." if len(msg.body) > 50 else msg.body
        )


def example_close_conversation(conversation):
    """Example: Manually close a conversation."""
    logger.info("=== Example: Close Conversation ===")
    
    service = ConversationService()
    
    closed = service.close_conversation(
        conversation,
        ConversationStatus.AGENT_CLOSED,
        reason="Conversation completed successfully"
    )
    
    if closed:
        logger.info(
            "Conversation closed",
            conv_id=closed.conv_id,
            status=closed.status.value,
            ended_at=closed.ended_at
        )


def example_process_timeouts():
    """Example: Process expired and idle conversations."""
    logger.info("=== Example: Process Timeouts ===")
    
    service = ConversationService()
    
    # Process expired conversations
    expired_count = service.process_expired_conversations(limit=10)
    logger.info(f"Processed {expired_count} expired conversations")
    
    # Process idle conversations
    idle_count = service.process_idle_conversations(
        idle_minutes=30,
        limit=10
    )
    logger.info(f"Processed {idle_count} idle conversations")


def example_extend_conversation(conversation):
    """Example: Extend conversation expiration."""
    logger.info("=== Example: Extend Conversation ===")
    
    service = ConversationService()
    
    extended = service.extend_expiration(
        conversation,
        additional_minutes=60
    )
    
    if extended:
        logger.info(
            "Conversation extended",
            conv_id=extended.conv_id,
            new_expires_at=extended.expires_at
        )


def example_list_active_conversations():
    """Example: List all active conversations for an owner."""
    logger.info("=== Example: List Active Conversations ===")
    
    service = ConversationService()
    conversations = service.get_active_conversations(owner_id=1, limit=50)
    
    logger.info(f"Found {len(conversations)} active conversations")
    
    for conv in conversations:
        logger.info(
            "Active conversation",
            conv_id=conv.conv_id,
            from_number=conv.from_number,
            status=conv.status.value,
            started_at=conv.started_at
        )


def main():
    """Run all examples."""
    logger.info("Starting Owner Project examples...")
    
    try:
        # Example 1: Create conversation
        conversation = example_create_conversation()
        
        # Example 2: Add messages
        example_add_messages(conversation)
        
        # Example 3: List messages
        example_list_messages(conversation)
        
        # Example 4: Extend conversation
        example_extend_conversation(conversation)
        
        # Example 5: Closure detection
        example_closure_detection(conversation)
        
        # Example 6: List active conversations
        example_list_active_conversations()
        
        # Example 7: Process timeouts
        example_process_timeouts()
        
        # Example 8: Close conversation (if still open)
        updated_conv = conversation_service.get_conversation_by_id(conversation.conv_id)
        if updated_conv and updated_conv.is_active():
            example_close_conversation(updated_conv)
        
        logger.info("All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
