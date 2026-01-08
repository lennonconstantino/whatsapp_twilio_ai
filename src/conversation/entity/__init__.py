"""
Módulo de entidades do domínio
"""
from .conversation import Conversation, ConversationStatus
from .message import Message, MessageOwner, MessageType, MessageDirection

__all__ = [
    "Conversation",
    "ConversationStatus",
    "Message",
    "MessageOwner",
    "MessageType",
    "MessageDirection",
]
