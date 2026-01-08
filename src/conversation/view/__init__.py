"""
Módulo de views (DTOs)
"""
from .conversation_dto import (
    ConversationCreateDTO,
    ConversationUpdateDTO,
    ConversationResponseDTO,
    ConversationDetailDTO,
    ConversationListDTO,
    ConversationStatsDTO,
)
from .message_dto import (
    MessageCreateDTO,
    MessageResponseDTO,
    MessageListDTO,
    MessageSummaryDTO,
    SendMessageDTO,
    ReceiveMessageDTO,
)

__all__ = [
    "ConversationCreateDTO",
    "ConversationUpdateDTO",
    "ConversationResponseDTO",
    "ConversationDetailDTO",
    "ConversationListDTO",
    "ConversationStatsDTO",
    "MessageCreateDTO",
    "MessageResponseDTO",
    "MessageListDTO",
    "MessageSummaryDTO",
    "SendMessageDTO",
    "ReceiveMessageDTO",
]
