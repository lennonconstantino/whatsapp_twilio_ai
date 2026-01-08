"""
Conversation Manager Module

Módulo para gestão de conversas de WhatsApp e outros canais com integração de agentes de IA.
"""

__version__ = "0.1.0"
__author__ = "Your Team"

from .entity.conversation import Conversation, ConversationStatus
from .entity.message import Message, MessageOwner, MessageType, MessageDirection
from .service.conversation_service import ConversationService
from .service.message_service import MessageService

__all__ = [
    "Conversation",
    "ConversationStatus",
    "Message",
    "MessageOwner",
    "MessageType",
    "MessageDirection",
    "ConversationService",
    "MessageService",
]
