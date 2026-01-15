from datetime import datetime, timezone


from src.core.utils import get_logger
from src.modules.conversation.services.conversation_service import ConversationService
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import ConversationStatus
from src.modules.conversation.enums.message_owner import MessageOwner


logger = get_logger(__name__)


def test_complete_conversation_lifecycle():
    service = ConversationService()

    import random

    suffix = random.randint(1000, 9999)
    from_number = f"+55119{suffix}"
    to_number = f"+55118{suffix}"

    try:
        service.conversation_repo.client.table("owners").insert(
            {
                "owner_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "name": "Test Owner",
                "email": "test@example.com",
                "active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception:
        logger.warning("Owner seeding failed (might exist)")

    conv = service.get_or_create_conversation(
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        from_number=from_number,
        to_number=to_number,
        channel="whatsapp",
    )
    assert conv.status == ConversationStatus.PENDING.value

    user_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        from_number=from_number,
        to_number=to_number,
        body="Preciso de ajuda",
        message_owner=MessageOwner.USER,
    )
    service.add_message(conv, user_msg)

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PENDING.value

    agent_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        from_number=to_number,
        to_number=from_number,
        body="Olá! Como posso ajudar?",
        message_owner=MessageOwner.AGENT,
    )
    service.add_message(conv, agent_msg)

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert conv.context is not None
    assert "accepted_by" in conv.context
    assert (
        conv.context["accepted_by"]["agent_type"] == MessageOwner.AGENT.value
    )

    processed_count = service.process_idle_conversations(idle_minutes=-1)
    logger.info("Processed idle conversations", count=processed_count)

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.IDLE_TIMEOUT.value

    user_msg2 = MessageCreateDTO(
        conv_id=conv.conv_id,
        owner_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        from_number=from_number,
        to_number=to_number,
        body="Ainda está aí?",
        message_owner=MessageOwner.USER,
    )
    service.add_message(conv, user_msg2)

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert "reactivated_from_idle" in conv.context

    service.close_conversation(conv, ConversationStatus.AGENT_CLOSED)

    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.AGENT_CLOSED.value
